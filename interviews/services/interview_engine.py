"""
Interview Engine - InterviewIQ
Manages interview question progression, state transitions, duplicate prevention,
adaptive difficulty, follow-up branching, and interview completion.
"""

import logging
from typing import Dict, Any, Tuple
from django.utils import timezone
from interviews.models import InterviewSession, InterviewQuestion, InterviewAnswer, InterviewEvaluation
from interviews.services.ai_service import get_ai_service
from interviews.services.evaluation_service import EvaluationService

logger = logging.getLogger(__name__)


class InterviewEngine:

    @classmethod
    def start_session(cls, session: InterviewSession) -> InterviewQuestion:
        """
        Initializes an interview session, generates the opening question,
        and transitions the state to WAITING_FOR_ANSWER.
        """
        if session.state not in (InterviewSession.STATE_CREATED, InterviewSession.STATE_READY):
            # If already started, return the current question
            cur = session.current_question()
            if cur:
                return cur
            raise ValueError(f"Cannot start session in state '{session.state}'.")

        ai_svc = get_ai_service()
        q_data = ai_svc.generate_first_question(session)

        question = InterviewQuestion.objects.create(
            session=session,
            question_index=1,
            is_follow_up=False,
            text=q_data.get('text', 'Could you introduce yourself and your technical background?'),
            category=q_data.get('category', 'Technical Fundamentals'),
            target_concept=q_data.get('target_concept', ''),
            difficulty=q_data.get('difficulty', session.difficulty),
            interviewer_note=q_data.get('interviewer_note', '')
        )

        session.state = InterviewSession.STATE_WAITING_FOR_ANSWER
        session.ai_mode_used = getattr(q_data, 'ai_mode_used', getattr(ai_svc, '__class__', type).__name__)
        session.save(update_fields=['state', 'ai_mode_used', 'updated_at'])

        return question

    @classmethod
    def submit_answer(
        cls,
        session: InterviewSession,
        question_id: int,
        answer_text: str,
        input_method: str = 'text',
        duration_seconds: int = 0
    ) -> Tuple[InterviewEvaluation, Dict[str, Any]]:
        """
        Processes candidate answer with state validation and duplicate prevention.
        Evaluates answer, determines follow-up or next question, and updates session state.
        """
        # Validate state
        if session.state not in (InterviewSession.STATE_WAITING_FOR_ANSWER, InterviewSession.STATE_FOLLOW_UP):
            raise ValueError(f"Cannot submit answer when interview state is '{session.state}'.")

        # Fetch and validate question
        try:
            question = session.questions.get(id=question_id)
        except InterviewQuestion.DoesNotExist:
            raise ValueError("Question not found in the specified interview session.")

        # Duplicate submission protection
        if hasattr(question, 'answer'):
            raise ValueError("An answer has already been submitted for this question.")

        # Ensure this is the active question
        current_q = session.current_question()
        if current_q.id != question.id:
            raise ValueError("Submitted answer does not correspond to the currently active question.")

        # Transition to EVALUATING
        session.state = InterviewSession.STATE_EVALUATING
        session.save(update_fields=['state', 'updated_at'])

        # Save the answer
        answer = InterviewAnswer.objects.create(
            question=question,
            text=answer_text,
            input_method=input_method,
            duration_seconds=duration_seconds
        )

        # Analyze speech / communication metrics
        comm_metrics = EvaluationService.analyze_communication(answer_text, duration_seconds)

        # Build conversation history context
        history = []
        for q in session.questions.all():
            if hasattr(q, 'answer'):
                history.append({
                    'question_index': q.question_index,
                    'is_follow_up': q.is_follow_up,
                    'question_text': q.text,
                    'answer_text': q.answer.text
                })

        # Evaluate with AI service
        ai_svc = get_ai_service()
        eval_data = ai_svc.evaluate_answer(session, question, answer_text, history)

        evaluation = InterviewEvaluation.objects.create(
            answer=answer,
            score=eval_data.get('score', 50.0),
            classification=eval_data.get('classification', InterviewEvaluation.CLASS_PARTIALLY_CORRECT),
            correct_concepts=eval_data.get('correct_concepts', []),
            missing_concepts=eval_data.get('missing_concepts', []),
            incorrect_statements=eval_data.get('incorrect_statements', []),
            explanation=eval_data.get('explanation', ''),
            suggestions=eval_data.get('suggestions', ''),
            better_answer_example=eval_data.get('better_answer_example', ''),
            interviewer_response=eval_data.get('interviewer_response', 'Thank you for your answer.'),
            suggested_follow_up=eval_data.get('suggested_follow_up', ''),
            confidence_score=eval_data.get('confidence_score', 0.95),
            communication_feedback=comm_metrics
        )

        # Next Step Progression
        next_step_data = cls._progress_interview(session, question, evaluation, ai_svc, history)

        return evaluation, next_step_data

    @classmethod
    def _progress_interview(
        cls,
        session: InterviewSession,
        current_question: InterviewQuestion,
        evaluation: InterviewEvaluation,
        ai_svc,
        history: list
    ) -> Dict[str, Any]:
        """
        Determines whether to trigger a contextual follow-up question,
        advance to next main question, or complete the interview.
        """
        # Follow-up criteria:
        # 1. AI indicated follow_up_needed
        # 2. current_question is NOT already a follow-up (max 1 follow-up depth)
        # 3. Follow-up text is non-empty
        follow_up_eligible = (
            not current_question.is_follow_up and
            evaluation.suggested_follow_up and
            evaluation.classification in (
                InterviewEvaluation.CLASS_PARTIALLY_CORRECT,
                InterviewEvaluation.CLASS_VAGUE,
                InterviewEvaluation.CLASS_NEEDS_CLARIFICATION,
                InterviewEvaluation.CLASS_UNABLE_TO_EVALUATE
            )
        )

        if follow_up_eligible:
            follow_up_q = InterviewQuestion.objects.create(
                session=session,
                question_index=current_question.question_index,
                is_follow_up=True,
                parent_question=current_question,
                text=evaluation.suggested_follow_up,
                category=f"{current_question.category} (Follow-up)",
                target_concept=current_question.target_concept,
                difficulty=current_question.difficulty,
                interviewer_note=f"Follow-up prompted by {evaluation.classification} answer."
            )
            session.state = InterviewSession.STATE_WAITING_FOR_ANSWER
            session.save(update_fields=['state', 'updated_at'])

            return {
                'action': 'follow_up',
                'question_id': follow_up_q.id,
                'question_text': follow_up_q.text,
                'question_index': follow_up_q.question_index,
                'is_follow_up': True,
                'interviewer_response': evaluation.interviewer_response
            }

        # Check completed main questions count
        main_questions_completed = session.questions.filter(
            is_follow_up=False,
            answer__evaluation__isnull=False
        ).count()

        has_intro = session.questions.filter(category='Candidate Introduction').exists()
        target_count = session.total_questions_target + (1 if has_intro else 0)

        if main_questions_completed >= target_count:
            # Interview Target reached -> Generate Final Report
            report = cls.complete_session(session)
            return {
                'action': 'completed',
                'overall_score': session.overall_score,
                'report': report,
                'interviewer_response': evaluation.interviewer_response + " That concludes all questions for this session. Excellent effort!"
            }

        # Otherwise, ask Next Question
        previous_evals = []
        for q in session.questions.all():
            if hasattr(q, 'answer') and hasattr(q.answer, 'evaluation'):
                previous_evals.append({
                    'score': q.answer.evaluation.score,
                    'classification': q.answer.evaluation.classification
                })

        next_q_data = ai_svc.generate_next_question(session, history, previous_evals)
        next_q = InterviewQuestion.objects.create(
            session=session,
            question_index=main_questions_completed + 1,
            is_follow_up=False,
            text=next_q_data.get('text', 'What is your experience with software architecture?'),
            category=next_q_data.get('category', 'Technical Depth'),
            target_concept=next_q_data.get('target_concept', ''),
            difficulty=next_q_data.get('difficulty', session.current_difficulty),
            interviewer_note=next_q_data.get('interviewer_note', '')
        )

        session.state = InterviewSession.STATE_WAITING_FOR_ANSWER
        session.save(update_fields=['state', 'updated_at'])

        return {
            'action': 'next_question',
            'question_id': next_q.id,
            'question_text': next_q.text,
            'question_index': next_q.question_index,
            'category': next_q.category,
            'difficulty': next_q.difficulty,
            'is_follow_up': False,
            'interviewer_response': evaluation.interviewer_response
        }

    @classmethod
    def complete_session(cls, session: InterviewSession) -> Dict[str, Any]:
        """
        Finalizes an interview session, aggregates metrics, generates the final report,
        and marks the session COMPLETED.
        """
        evaluations_list = []
        full_transcript = []

        for q in session.questions.all():
            item = {'question_id': q.id, 'question_text': q.text, 'index': q.question_index, 'is_follow_up': q.is_follow_up}
            if hasattr(q, 'answer'):
                item['answer_text'] = q.answer.text
                item['duration'] = q.answer.duration_seconds
                if hasattr(q.answer, 'evaluation'):
                    ev = q.answer.evaluation
                    item['score'] = ev.score
                    item['classification'] = ev.classification
                    evaluations_list.append({
                        'score': ev.score,
                        'classification': ev.classification,
                        'correct_concepts': ev.correct_concepts,
                        'missing_concepts': ev.missing_concepts,
                        'incorrect_statements': ev.incorrect_statements,
                        'suggestions': ev.suggestions
                    })
            full_transcript.append(item)

        ai_svc = get_ai_service()
        report = ai_svc.generate_final_report(session, full_transcript, evaluations_list)

        metrics = EvaluationService.calculate_session_metrics(evaluations_list)
        overall_score = metrics.get('overall_score')

        session.overall_score = overall_score
        session.summary_report = report
        session.state = InterviewSession.STATE_COMPLETED
        session.completed_at = timezone.now()
        session.save(update_fields=['overall_score', 'summary_report', 'state', 'completed_at', 'updated_at'])

        return report
