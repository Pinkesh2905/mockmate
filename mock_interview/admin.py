from django.contrib import admin
from .models import MockInterviewSession, InterviewTurn

# Inline for InterviewTurns within a MockInterviewSession
class InterviewTurnInline(admin.TabularInline):
    model = InterviewTurn
    extra = 0 # Don't show empty forms by default
    readonly_fields = ('turn_number', 'ai_question', 'user_answer', 'ai_internal_analysis', 'ai_follow_up_feedback', 'timestamp')
    can_delete = False # Don't allow deleting turns from admin
    verbose_name = "Interview Turn"
    verbose_name_plural = "Interview Turns"


@admin.register(MockInterviewSession)
class MockInterviewSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'job_role', 'status', 'start_time', 'end_time', 'score', 'overall_feedback')
    list_filter = ('status', 'job_role', 'start_time')
    search_fields = ('user__username', 'job_role', 'key_skills')
    readonly_fields = ('user', 'start_time', 'end_time', 'created_at', 'updated_at')
    inlines = [InterviewTurnInline]

    fieldsets = (
        (None, {
            'fields': ('user', 'job_role', 'key_skills', 'status')
        }),
        ('Timing & Results', {
            'fields': ('start_time', 'end_time', 'score', 'overall_feedback')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(InterviewTurn)
class InterviewTurnAdmin(admin.ModelAdmin):
    list_display = ('session', 'turn_number', 'ai_question', 'user_answer', 'timestamp')
    list_filter = ('session__job_role', 'timestamp')
    search_fields = ('session__user__username', 'ai_question', 'user_answer')
    readonly_fields = ('session', 'turn_number', 'ai_question', 'user_answer', 'ai_internal_analysis', 'ai_follow_up_feedback', 'timestamp')
