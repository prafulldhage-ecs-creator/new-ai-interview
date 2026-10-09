from django.urls import path
from .views import (
    HomeView,
    DashboardView,
    InterviewSetupView,
    InterviewRoomView,
    SubmitAnswerAPIView,
    EndInterviewView,
    InterviewReportView,
    InterviewHistoryView,
    DeleteInterviewView,
    SettingsView,
    RegisterView,
    LoginView,
    LogoutView,
)

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('setup/', InterviewSetupView.as_view(), name='interview_setup'),
    path('room/<uuid:session_id>/', InterviewRoomView.as_view(), name='interview_room'),
    path('api/interview/<uuid:session_id>/submit-answer/', SubmitAnswerAPIView.as_view(), name='api_submit_answer'),
    path('interview/<uuid:session_id>/end/', EndInterviewView.as_view(), name='interview_end'),
    path('interview/<uuid:session_id>/report/', InterviewReportView.as_view(), name='interview_report'),
    path('interview/<uuid:session_id>/delete/', DeleteInterviewView.as_view(), name='interview_delete'),
    path('history/', InterviewHistoryView.as_view(), name='history'),
    path('settings/', SettingsView.as_view(), name='settings'),
    path('accounts/login/', LoginView.as_view(), name='login'),
    path('accounts/register/', RegisterView.as_view(), name='register'),
    path('accounts/logout/', LogoutView.as_view(), name='logout'),
]
