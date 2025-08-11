from django.contrib import admin
# Removed User and BaseUserAdmin imports, and UserAdmin customization
# from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
# from django.contrib.auth.models import User
from .models import PracticeProblem, PracticeSubmission, TestCase # Removed UserProfile import

# Removed UserProfileInline and custom UserAdmin, as they belong in users/admin.py
# class UserProfileInline(admin.StackedInline): ...
# class UserAdmin(BaseUserAdmin): ...
# admin.site.unregister(User)
# admin.site.register(User, UserAdmin)


# Inline for Test Cases
class TestCaseInline(admin.TabularInline):
    model = TestCase
    extra = 1
    fields = ['input', 'expected_output', 'is_sample', 'description']
    verbose_name = "Test Case"
    verbose_name_plural = "Test Cases"


@admin.register(PracticeProblem)
class PracticeProblemAdmin(admin.ModelAdmin):
    list_display = ('title', 'difficulty', 'status', 'created_by', 'created_at', 'slug')
    prepopulated_fields = {'slug': ('title',)}
    search_fields = ('title', 'statement', 'companies')
    list_filter = ('difficulty', 'status', 'created_at', 'created_by__username')
    inlines = [TestCaseInline]
    # Fields that can be edited in the admin form
    fields = (
        'title', 'slug', 'difficulty', 'companies', 'url', 'statement',
        'sample_input', 'sample_output', 'status', 'created_by',
        'template_python', 'template_cpp', 'template_java'
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Admin can see all problems
        if request.user.is_superuser:
            return qs
        # Tutors can see their own problems (drafts, pending) and published problems
        # IMPORTANT: Access user.profile now
        if request.user.is_staff and hasattr(request.user, 'profile') and request.user.profile.role == 'TUTOR':
            return qs.filter(models.Q(created_by=request.user) | models.Q(status='PUBLISHED'))
        # Students should only see published problems
        return qs.filter(status='PUBLISHED')

    def save_model(self, request, obj, form, change):
        # Set created_by when a new problem is added by a staff user
        # IMPORTANT: Access user.profile now
        if not obj.pk and request.user.is_staff and hasattr(request.user, 'profile') and request.user.profile.role == 'TUTOR':
            obj.created_by = request.user
            # Set initial status to PENDING_APPROVAL for tutors
            obj.status = 'PENDING_APPROVAL'
        super().save_model(request, obj, form, change)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # If the user is a tutor, make 'status' and 'created_by' fields read-only
        # and set initial 'created_by' to current user
        # IMPORTANT: Access user.profile now
        if request.user.is_staff and hasattr(request.user, 'profile') and request.user.profile.role == 'TUTOR':
            form.base_fields['status'].widget.attrs['disabled'] = True
            form.base_fields['created_by'].widget.attrs['disabled'] = True
            # Set initial value for created_by if adding a new problem
            if not obj:
                form.base_fields['created_by'].initial = request.user.id
        # Admins can edit all fields
        return form

    # Make sure disabled fields are not saved if submitted
    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        # IMPORTANT: Access user.profile now
        if request.user.is_staff and hasattr(request.user, 'profile') and request.user.profile.role == 'TUTOR':
            # Tutors cannot change status or created_by after initial save
            return readonly_fields + ('status', 'created_by',)
        return readonly_fields


@admin.register(PracticeSubmission)
class PracticeSubmissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'problem', 'language', 'status', 'submission_time')
    list_filter = ('language', 'status', 'submission_time', 'problem')
    search_fields = ('user__username', 'problem__title', 'code', 'raw_output')
    readonly_fields = ('submission_time', 'raw_output', 'test_results', 'cpu_time', 'memory', 'user', 'problem', 'code', 'language')
    # Submissions are read-only in admin as they are results of user actions
