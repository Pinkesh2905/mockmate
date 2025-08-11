from django.contrib import admin
from django.apps import apps # Import apps module
from .models import Quiz, Question, Answer, QuizAttempt # Removed Course import from here
# Import Course from courses.models if needed for related fields, but not for direct registration
from courses.models import Course # To allow linking quizzes to courses in the admin form
from users.models import UserProfile # To access user roles in get_queryset, save_model etc.


# Inline for Answers within a Question
class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 1 # Number of empty forms to display
    fields = ['text', 'is_correct']
    verbose_name = "Answer"
    verbose_name_plural = "Answers"

# Inline for Questions within a Quiz
class QuestionInline(admin.StackedInline): # Stacked for more space for question text
    model = Question
    extra = 1
    fields = ['text']
    verbose_name = "Question"
    verbose_name_plural = "Questions"
    inlines = [AnswerInline] # Nest Answers within Questions

@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'total_questions', 'passing_score', 'duration_minutes', 'created_by', 'status', 'created_at')
    prepopulated_fields = {'slug': ('title',)}
    search_fields = ('title', 'description', 'created_by__username', 'course__title')
    list_filter = ('status', 'created_at', 'created_by', 'course')
    inlines = [QuestionInline]
    # Fields that can be edited in the admin form
    fields = (
        'title', 'slug', 'description', 'course', 'passing_score', 'duration_minutes',
        'created_by', 'status', 'created_at', 'updated_at'
    )
    readonly_fields = ('created_at', 'updated_at')

    # Override save_model to set created_by if not set (e.g., if created via admin by superuser)
    def save_model(self, request, obj, form, change):
        # Set created_by when a new quiz is added by a staff user
        if not obj.pk and request.user.is_staff and hasattr(request.user, 'profile') and request.user.profile.role == 'TUTOR':
            obj.created_by = request.user
            obj.status = 'PENDING_APPROVAL' # Default status for new tutor quizzes
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Admin can see all quizzes
        if request.user.is_superuser:
            return qs
        # Tutors can see their own quizzes (drafts, pending) and published quizzes
        if request.user.is_staff and hasattr(request.user, 'profile') and request.user.profile.role == 'TUTOR':
            return qs.filter(models.Q(created_by=request.user) | models.Q(status='PUBLISHED'))
        # Students should only see published quizzes
        return qs.filter(status='PUBLISHED')

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if request.user.is_staff and hasattr(request.user, 'profile') and request.user.profile.role == 'TUTOR':
            form.base_fields['status'].widget.attrs['disabled'] = True
            form.base_fields['created_by'].widget.attrs['disabled'] = True
            if not obj: # For new quizzes, set initial created_by
                form.base_fields['created_by'].initial = request.user.id
        return form

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        if request.user.is_staff and hasattr(request.user, 'profile') and request.user.profile.role == 'TUTOR':
            return readonly_fields + ('status', 'created_by',)
        return readonly_fields


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('quiz', 'text')
    search_fields = ('quiz__title', 'text')
    list_filter = ('quiz',)
    inlines = [AnswerInline]

@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('question', 'text', 'is_correct')
    search_fields = ('question__text', 'text')
    list_filter = ('is_correct', 'question__quiz')

@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'quiz', 'percentage_score', 'passed', 'start_time', 'end_time')
    search_fields = ('user__username', 'quiz__title')
    list_filter = ('passed', 'quiz', 'start_time')
    readonly_fields = ('user', 'quiz', 'score', 'percentage_score', 'passed', 'start_time', 'end_time', 'selected_answers')

# Removed the conditional Course registration
# if 'quizzes.Course' in [m._meta.label for m in apps.get_models()]:
#     @admin.register(Course)
#     class CourseAdmin(admin.ModelAdmin):
#         list_display = ('title', 'slug')
#         prepopulated_fields = {'slug': ('title',)}
