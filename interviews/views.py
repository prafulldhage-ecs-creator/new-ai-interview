import json
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Avg

from .models import InterviewSession, InterviewQuestion, InterviewAnswer, InterviewEvaluation
from .forms import InterviewSetupForm, AnswerSubmissionForm, UserRegistrationForm
from .services.interview_engine import InterviewEngine
from .services.evaluation_service import EvaluationService

logger = logging.getLogger(__name__)


def get_user_session_filter(request):
    """Returns query filters to restrict interview sessions to current authenticated user or anonymous browser session."""
    if request.user.is_authenticated:
        return {'user': request.user}
    if not request.session.session_key:
        request.session.save()
    return {'session_key': request.session.session_key, 'user__isnull': True}


def check_session_ownership(request, session: InterviewSession) -> bool:
    """Verifies that the session belongs to the requesting user or browser session."""
    if request.user.is_authenticated:
        return session.user_id == request.user.id
    if not request.session.session_key:
        request.session.save()
    return session.session_key == request.session.session_key and session.user is None


class HomeView(View):
    def get(self, request):
        return render(request, 'home.html')


class DashboardView(View):
    def get(self, request):
        filters = get_user_session_filter(request)
        sessions = InterviewSession.objects.filter(**filters).order_by('-created_at')

        completed_sessions = sessions.filter(state=InterviewSession.STATE_COMPLETED)
        completed_count = completed_sessions.count()

        scored_sessions = completed_sessions.filter(overall_score__isnull=False)
        avg_score_data = scored_sessions.aggregate(Avg('overall_score'))
        raw_avg = avg_score_data.get('overall_score__avg')
        avg_score = round(raw_avg, 1) if raw_avg is not None else None

        # Skill improvement indicator if >= 2 scored sessions
        improvement_delta = None
        if scored_sessions.count() >= 2:
            latest = scored_sessions[0].overall_score or 0.0
            previous = scored_sessions[1].overall_score or 0.0
            improvement_delta = round(latest - previous, 1)

        # Recommended practice areas derived from actual past evaluations
        recommended_areas = set()
        for s in completed_sessions[:5]:
            rep = s.summary_report or {}
            for t in rep.get('recommended_topics', []):
                recommended_areas.add(t)
            for g in rep.get('knowledge_gaps', []):
                recommended_areas.add(g)

        context = {
            'recent_sessions': sessions[:6],
            'completed_count': completed_count,
            'avg_score': avg_score,
            'improvement_delta': improvement_delta,
            'recommended_areas': list(recommended_areas)[:4],
            'has_history': sessions.exists()
        }
        return render(request, 'dashboard.html', context)


class InterviewSetupView(View):
    def get(self, request):
        form = InterviewSetupForm()
        return render(request, 'interview_setup.html', {'form': form})

    def post(self, request):
        form = InterviewSetupForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            if request.user.is_authenticated:
                session.user = request.user
            else:
                if not request.session.session_key:
                    request.session.save()
                session.session_key = request.session.session_key

            session.current_difficulty = session.difficulty if session.difficulty != 'Adaptive' else 'Medium'
            session.state = InterviewSession.STATE_CREATED
            session.save()

            # Initialize first question
            try:
                InterviewEngine.start_session(session)
            except Exception as e:
                logger.error("Failed to initialize session question: %s", e)
                messages.error(request, f"Unable to initialize interview: {str(e)}")
                return redirect('interview_setup')

            return redirect('interview_room', session_id=session.id)

        return render(request, 'interview_setup.html', {'form': form})


class InterviewRoomView(View):
    def get(self, request, session_id):
        session = get_object_or_404(InterviewSession, id=session_id)
        if not check_session_ownership(request, session):
            return HttpResponseForbidden("You do not have permission to access this interview session.")

        # If already completed, redirect to report
        if session.state == InterviewSession.STATE_COMPLETED:
            return redirect('interview_report', session_id=session.id)

        # Ensure active question is available
        question = session.current_question()
        if not question or session.state in (InterviewSession.STATE_CREATED, InterviewSession.STATE_READY):
            question = InterviewEngine.start_session(session)

        # Collect past Q&A in this session
        past_interactions = []
        for q in session.questions.all().order_by('question_index', 'id'):
            if hasattr(q, 'answer') and hasattr(q.answer, 'evaluation'):
                past_interactions.append({
                    'question': q,
                    'answer': q.answer,
                    'evaluation': q.answer.evaluation
                })

        context = {
            'session': session,
            'current_question': question,
            'past_interactions': past_interactions,
            'current_index': question.question_index,
            'total_target': session.total_questions_target,
            'progress_percent': int(((question.question_index - 1) / session.total_questions_target) * 100)
        }
        return render(request, 'interview_room.html', context)


class SubmitAnswerAPIView(View):
    """
    POST API for answering questions.
    Accepts application/json or standard POST form data.
    """
    def post(self, request, session_id):
        session = get_object_or_404(InterviewSession, id=session_id)
        if not check_session_ownership(request, session):
            return JsonResponse({'success': False, 'error': 'Forbidden access.'}, status=403)

        # Extract data from JSON or form post
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
            except Exception:
                return JsonResponse({'success': False, 'error': 'Invalid JSON body.'}, status=400)
        else:
            data = request.POST

        form = AnswerSubmissionForm(data)
        if not form.is_valid():
            errors = form.errors.as_text()
            return JsonResponse({'success': False, 'error': errors}, status=400)

        question_id = form.cleaned_data['question_id']
        answer_text = form.cleaned_data['text']
        input_method = form.cleaned_data.get('input_method', 'text')
        duration_seconds = form.cleaned_data.get('duration_seconds', 0)

        try:
            evaluation, next_step = InterviewEngine.submit_answer(
                session=session,
                question_id=question_id,
                answer_text=answer_text,
                input_method=input_method,
                duration_seconds=duration_seconds
            )
        except ValueError as ve:
            return JsonResponse({'success': False, 'error': str(ve)}, status=400)
        except Exception as ex:
            logger.exception("Unexpected error in submit_answer: %s", ex)
            return JsonResponse({'success': False, 'error': f"Processing error: {str(ex)}"}, status=500)

        # Return structured evaluation and next step details
        response_payload = {
            'success': True,
            'evaluation': {
                'score': evaluation.score,
                'classification': evaluation.classification,
                'correct_concepts': evaluation.correct_concepts,
                'missing_concepts': evaluation.missing_concepts,
                'incorrect_statements': evaluation.incorrect_statements,
                'explanation': evaluation.explanation,
                'suggestions': evaluation.suggestions,
                'better_answer_example': evaluation.better_answer_example,
                'interviewer_response': evaluation.interviewer_response,
                'communication_feedback': evaluation.communication_feedback
            },
            'next_step': next_step,
            'is_completed': session.state == InterviewSession.STATE_COMPLETED
        }
        return JsonResponse(response_payload)


class EndInterviewView(View):
    def post(self, request, session_id):
        session = get_object_or_404(InterviewSession, id=session_id)
        if not check_session_ownership(request, session):
            return HttpResponseForbidden("Forbidden.")

        # If any question was answered, generate completed report
        answered_count = session.completed_questions_count()
        if answered_count > 0:
            InterviewEngine.complete_session(session)
            messages.info(request, "Interview concluded early. Generated report based on your answered questions.")
            return redirect('interview_report', session_id=session.id)
        else:
            session.transition_to(InterviewSession.STATE_CANCELLED)
            messages.info(request, "Interview session was cancelled with no answers recorded.")
            return redirect('dashboard')


class InterviewReportView(View):
    def get(self, request, session_id):
        session = get_object_or_404(InterviewSession, id=session_id)
        if not check_session_ownership(request, session):
            return HttpResponseForbidden("Forbidden.")

        # Ensure session is finalized if report is accessed
        if session.state != InterviewSession.STATE_COMPLETED:
            InterviewEngine.complete_session(session)

        # Fetch questions and evaluations
        questions_data = []
        for q in session.questions.all().order_by('question_index', 'id'):
            item = {'question': q, 'answer': None, 'evaluation': None}
            if hasattr(q, 'answer'):
                item['answer'] = q.answer
                if hasattr(q.answer, 'evaluation'):
                    item['evaluation'] = q.answer.evaluation
            questions_data.append(item)

        context = {
            'session': session,
            'report': session.summary_report or {},
            'questions_data': questions_data,
            'rubric_explanation': EvaluationService.RUBRIC_EXPLANATION,
            'total_asked': session.questions.count(),
            'total_answered': session.completed_questions_count()
        }
        return render(request, 'interview_report.html', context)


class InterviewHistoryView(View):
    def get(self, request):
        filters = get_user_session_filter(request)
        sessions = InterviewSession.objects.filter(**filters).order_by('-created_at')
        return render(request, 'history.html', {'sessions': sessions})


class DeleteInterviewView(View):
    def post(self, request, session_id):
        session = get_object_or_404(InterviewSession, id=session_id)
        if not check_session_ownership(request, session):
            return HttpResponseForbidden("Forbidden.")

        session.delete()
        messages.success(request, "Interview session and its records were permanently removed.")
        return redirect('history')


class SettingsView(View):
    def get(self, request):
        return render(request, 'settings.html')


class RegisterView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard')
        form = UserRegistrationForm()
        return render(request, 'registration/register.html', {'form': form})

    def post(self, request):
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            # Associate any anonymous sessions from current session_key with new user
            if request.session.session_key:
                InterviewSession.objects.filter(
                    session_key=request.session.session_key,
                    user__isnull=True
                ).update(user=user)
            messages.success(request, f"Welcome to InterviewIQ, {user.username}!")
            return redirect('dashboard')
        return render(request, 'registration/register.html', {'form': form})


class LoginView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard')
        form = AuthenticationForm()
        return render(request, 'registration/login.html', {'form': form})

    def post(self, request):
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            # Migrate any anonymous sessions from this browser
            if request.session.session_key:
                InterviewSession.objects.filter(
                    session_key=request.session.session_key,
                    user__isnull=True
                ).update(user=user)
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect('dashboard')
        return render(request, 'registration/login.html', {'form': form})


class LogoutView(View):
    def post(self, request):
        logout(request)
        messages.info(request, "You have been logged out.")
        return redirect('home')

    def get(self, request):
        logout(request)
        messages.info(request, "You have been logged out.")
        return redirect('home')
