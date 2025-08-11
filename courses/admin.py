from django.contrib import admin
from django.apps import apps # Import apps module for apps.get_models()
from .models import Course, Enrollment, Lesson, WatchedLesson, Certificate, Topic # <--- CORRECTED: Import Topic from here
from users.models import UserProfile # Import UserProfile to access role


# Inline for Lessons within a Course
class LessonInline(admin.TabularInline): # TabularInline is compact
    model = Lesson
    extra = 1 # Number of empty forms to display
    fields = ['title', 'order', 'video_url', 'content', 'duration_minutes', 'is_video_required', 'is_free_preview', 'topic', 'created_by']
    verbose_name = "Lesson"
    verbose_name_plural = "Lessons"
    # Make created_by read-only for tutors, but editable for admins
    # This will be handled by overriding get_form later if needed for complex logic
    readonly_fields = ('created_by',) # Set as readonly by default in admin

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        # Set initial created_by for new lessons if current user is a tutor
        # IMPORTANT: Access user.profile now
        if request.user.is_staff and hasattr(request.user, 'profile') and request.user.profile.role == 'TUTOR':
            formset.form.base_fields['created_by'].initial = request.user.id
        return formset


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'category', 'level', 'instructor', 'price', 'status', 'created_by', 'created_at', 'total_lessons')
    prepopulated_fields = {'slug': ('title',)}
    search_fields = ('title', 'instructor', 'category', 'description')
    list_filter = ('category', 'level', 'status', 'created_by', 'created_at')
    inlines = [LessonInline]
    # Fields to display in the add/edit form
    fields = (
        'title', 'slug', 'description', 'video_link', 'thumbnail', 'duration',
        'level', 'category', 'instructor', 'price', 'topics',
        'status', 'created_by', # New fields
        'created_at', 'updated_at', 'total_lessons', 'rating', 'students' # Readonly fields
    )
    readonly_fields = ('created_at', 'updated_at', 'total_lessons', 'rating', 'students')

    # Override save_model to set created_by and initial status
    def save_model(self, request, obj, form, change):
        # IMPORTANT: Access user.profile now
        if not obj.pk and request.user.is_staff and hasattr(request.user, 'profile') and request.user.profile.role == 'TUTOR':
            obj.created_by = request.user
            obj.status = 'PENDING_APPROVAL' # Default status for new tutor courses
        super().save_model(request, obj, form, change)

    # Restrict tutor's ability to change status and created_by in admin
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # IMPORTANT: Access user.profile now
        if request.user.is_staff and hasattr(request.user, 'profile') and request.user.profile.role == 'TUTOR':
            form.base_fields['status'].widget.attrs['disabled'] = True
            form.base_fields['created_by'].widget.attrs['disabled'] = True
            if not obj: # For new courses, set initial created_by
                form.base_fields['created_by'].initial = request.user.id
        return form

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        # IMPORTANT: Access user.profile now
        if request.user.is_staff and hasattr(request.user, 'profile') and request.user.profile.role == 'TUTOR':
            return readonly_fields + ('status', 'created_by',)
        return readonly_fields


# REMOVED: @admin.register(Lesson) and LessonAdmin class
# Lesson model is managed via CourseAdmin's inline.

admin.site.register(Enrollment)
admin.site.register(WatchedLesson)
admin.site.register(Certificate)

# Register Topic model here, as it's now defined in courses/models.py
@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
