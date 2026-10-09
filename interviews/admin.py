from django.contrib import admin
from .models import InterviewSession, InterviewQuestion, InterviewAnswer, InterviewEvaluation


class InterviewQuestionInline(admin.TabularInline):
    model = InterviewQuestion
    extra = 0
    readonly_fields = ('question_index', 'is_follow_up', 'text', 'category', 'difficulty', 'created_at')


@admin.register(InterviewSession)
class InterviewSessionAdmin(admin.ModelAdmin):
    list_display = ('title', 'interview_type', 'technical_domain', 'difficulty', 'state', 'overall_score', 'ai_mode_used', 'created_at')
    list_filter = ('state', 'interview_type', 'technical_domain', 'difficulty', 'ai_mode_used', 'created_at')
    search_fields = ('title', 'target_role', 'user__username', 'session_key')
    inlines = [InterviewQuestionInline]


@admin.register(InterviewQuestion)
class InterviewQuestionAdmin(admin.ModelAdmin):
    list_display = ('session', 'question_index', 'is_follow_up', 'category', 'difficulty', 'created_at')
    list_filter = ('is_follow_up', 'difficulty', 'category')
    search_fields = ('text', 'target_concept', 'session__title')


@admin.register(InterviewAnswer)
class InterviewAnswerAdmin(admin.ModelAdmin):
    list_display = ('question', 'input_method', 'duration_seconds', 'created_at')
    list_filter = ('input_method', 'created_at')
    search_fields = ('text', 'question__text')


@admin.register(InterviewEvaluation)
class InterviewEvaluationAdmin(admin.ModelAdmin):
    list_display = ('answer', 'score', 'classification', 'confidence_score', 'created_at')
    list_filter = ('classification', 'created_at')
    search_fields = ('explanation', 'suggestions')
