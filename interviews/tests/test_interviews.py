from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.contrib.auth.models import User
from interviews.models import InterviewSession, InterviewQuestion, InterviewAnswer, InterviewEvaluation
from interviews.services.interview_engine import InterviewEngine
from interviews.services.evaluation_service import EvaluationService
from interviews.services.ai_service import DemoAIService, OpenAIAIService, get_ai_service


class InterviewEngineAndStateMachineTestCase(TestCase):
    def setUp(self):
        self.session = InterviewSession.objects.create(
            title='Engine Test Session',
            technical_domain='Data Structures and Algorithms',
            difficulty='Adaptive',
            total_questions_target=5
        )

    def test_state_machine_valid_and_invalid_transitions(self):
        self.assertEqual(self.session.state, InterviewSession.STATE_CREATED)

        # Valid transition: CREATED -> READY
        self.session.transition_to(InterviewSession.STATE_READY)
        self.assertEqual(self.session.state, InterviewSession.STATE_READY)

        # Valid transition: READY -> WAITING_FOR_ANSWER
        self.session.transition_to(InterviewSession.STATE_WAITING_FOR_ANSWER)
        self.assertEqual(self.session.state, InterviewSession.STATE_WAITING_FOR_ANSWER)

        # Invalid transition: WAITING_FOR_ANSWER directly to CREATED
        with self.assertRaises(ValueError):
            self.session.transition_to(InterviewSession.STATE_CREATED)

    def test_start_session_creates_first_question(self):
        question = InterviewEngine.start_session(self.session)
        self.assertIsNotNone(question)
        self.assertEqual(question.question_index, 1)
        self.assertFalse(question.is_follow_up)
        self.session.refresh_from_db()
        self.assertEqual(self.session.state, InterviewSession.STATE_WAITING_FOR_ANSWER)

    def test_duplicate_answer_submission_prevention(self):
        question = InterviewEngine.start_session(self.session)

        # First submission succeeds
        eval1, next_step = InterviewEngine.submit_answer(
            session=self.session,
            question_id=question.id,
            answer_text="Array has contiguous memory allocation with O(1) random access.",
            input_method='text',
            duration_seconds=15
        )
        self.assertIsNotNone(eval1)

        # Second submission on SAME question MUST raise ValueError
        with self.assertRaises(ValueError) as ctx:
            InterviewEngine.submit_answer(
                session=self.session,
                question_id=question.id,
                answer_text="Duplicate attempt to re-submit.",
                input_method='text'
            )
        self.assertIn("already been submitted", str(ctx.exception))

    def test_invalid_session_question_rejected(self):
        other_session = InterviewSession.objects.create(
            title='Other Session',
            technical_domain='Python'
        )
        other_q = InterviewEngine.start_session(other_session)

        # Attempting to submit other_q in self.session must fail
        InterviewEngine.start_session(self.session)
        with self.assertRaises(ValueError) as ctx:
            InterviewEngine.submit_answer(
                session=self.session,
                question_id=other_q.id,
                answer_text="Trying cross-session injection"
            )
        self.assertIn("not found in the specified interview session", str(ctx.exception))

    def test_communication_filler_word_analysis(self):
        sample_transcript = "Um basically an array is like contiguous memory and uh you know has fast access."
        analysis = EvaluationService.analyze_communication(sample_transcript, duration_seconds=10)

        self.assertGreater(analysis['word_count'], 5)
        self.assertGreater(analysis['filler_count'], 2)
        self.assertGreater(analysis['filler_ratio_pct'], 10.0)
        self.assertIn('basically', [f['word'] for f in analysis['detected_fillers']])

    def test_demo_ai_service_deterministic_behavior(self):
        demo = DemoAIService()
        q = demo.generate_first_question(self.session)
        self.assertIn('text', q)
        self.assertIn('target_concept', q)

        # Test evaluating "I don't know"
        question_obj = InterviewQuestion(text="What is a red-black tree?", target_concept="self-balancing binary search tree")
        res_idk = demo.evaluate_answer(self.session, question_obj, "I don't know, honestly not sure.", [])
        self.assertEqual(res_idk['classification'], 'Unable to evaluate')
        self.assertTrue(res_idk['follow_up_needed'])

        # Test evaluating strong answer
        res_strong = demo.evaluate_answer(
            self.session,
            question_obj,
            "A red-black tree is a self-balancing binary search tree where each node has color bit red or black to maintain balance in O(log n) time.",
            []
        )
        self.assertIn(res_strong['classification'], ('Correct', 'Mostly correct'))
        self.assertGreaterEqual(res_strong['score'], 80.0)

    @patch('openai.OpenAI')
    def test_openai_service_mock_and_fallback(self, mock_openai_cls):
        # Mock client to return mock JSON
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content='{"score": 88, "classification": "Mostly correct", "correct_concepts": ["nodes"], "missing_concepts": [], "incorrect_statements": [], "explanation": "Good answer", "suggestions": "Add edge cases", "better_answer_example": "Exemplary", "interviewer_response": "Well done", "follow_up_needed": false, "suggested_follow_up": "", "confidence_score": 0.9}'))
        ]
        mock_client.chat.completions.create.return_value = mock_response

        service = OpenAIAIService(api_key='test-key-mock')
        question_obj = InterviewQuestion(text="Explain nodes", target_concept="pointers")
        eval_res = service.evaluate_answer(self.session, question_obj, "Node contains data and next pointer.", [])

        self.assertEqual(eval_res['score'], 88)
        self.assertEqual(eval_res['classification'], 'Mostly correct')

    @patch('openai.OpenAI')
    def test_openai_failure_falls_back_to_demo_mode_gracefully(self, mock_openai_cls):
        # Mock client that raises network exception
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("Simulated connection timeout")

        service = OpenAIAIService(api_key='test-key-mock')
        question_obj = InterviewQuestion(text="Explain linked lists", target_concept="contiguous memory pointer nodes")
        
        # Must not raise exception, but return safe fallback
        eval_res = service.evaluate_answer(self.session, question_obj, "Linked list is node based.", [])
        self.assertIsNotNone(eval_res)
        self.assertIn('score', eval_res)
        self.assertIn('Fallback', eval_res['explanation'])
