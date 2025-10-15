from django.contrib import admin
from django.db import models
from django.forms import Textarea
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    Category, Tag, PracticeProblem, TestCase, 
    PracticeSubmission, UserProblemStats, Discussion, DiscussionVote,
    Badge, UserBadge, ProblemVideoSolution, CodeTemplate
)

# --- Admin Actions ---
@admin.action(description='Mark selected problems as Published')
def make_published(modeladmin, request, queryset):
    queryset.update(status='PUBLISHED')

@admin.action(description='Mark selected problems as Draft')
def make_draft(modeladmin, request, queryset):
    queryset.update(status='DRAFT')

@admin.action(description='Archive selected problems')
def archive_problems(modeladmin, request, queryset):
    queryset.update(status='ARCHIVED')

# --- Model Admin Registrations ---

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'color_preview', 'problem_count')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    
    def color_preview(self, obj):
        return format_html(
            '<span style="background-color: {}; padding: 4px 8px; border-radius: 4px; color: white;">{}</span>',
            obj.color_code, obj.color_code
        )
    color_preview.short_description = 'Color'
    
    def problem_count(self, obj):
        count = obj.problems.filter(status='PUBLISHED').count()
        url = (
            reverse('admin:practice_practiceproblem_changelist')
            + f'?category__id__exact={obj.id}'
        )
        return format_html('<a href="{}">{}</a>', url, count)
    problem_count.short_description = 'Problems'

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'problem_count')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    
    def problem_count(self, obj):
        count = obj.problems.filter(status='PUBLISHED').count()
        url = (
            reverse('admin:practice_practiceproblem_changelist')
            + f'?tags__id__exact={obj.id}'
        )
        return format_html('<a href="{}">{}</a>', url, count)
    problem_count.short_description = 'Problems'

# --- Inlines for Problem Admin ---

class TestCaseInline(admin.TabularInline):
    model = TestCase
    extra = 1
    fields = ['input_data', 'expected_output', 'is_sample', 'is_hidden', 'order']
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 3, 'cols': 40})},
    }
    ordering = ['order']

class ProblemVideoSolutionInline(admin.TabularInline):
    model = ProblemVideoSolution
    extra = 1
    fields = ['title', 'url', 'user']

class CodeTemplateInline(admin.TabularInline):
    model = CodeTemplate
    extra = 1
    fields = ('language', 'starter_code', 'is_default')

@admin.register(PracticeProblem)
class PracticeProblemAdmin(admin.ModelAdmin):
    actions = [make_published, make_draft, archive_problems]
    list_display = (
        'title', 'difficulty_badge', 'category', 'status_badge', 'acceptance_rate', 
        'total_submissions', 'test_case_count', 'created_by', 'created_at'
    )
    list_filter = ('difficulty', 'status', 'category', 'created_at', 'tags', 'created_by')
    search_fields = ('title', 'statement')
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ('tags',)
    readonly_fields = ('acceptance_rate', 'total_submissions', 'accepted_submissions', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'difficulty', 'category', 'tags')
        }),
        ('Problem Content', {
            'fields': ('statement', 'constraints', 'hints', 'approach')
        }),
        ('Problem Settings', {
            'fields': ('time_limit', 'memory_limit')
        }),
        ('Administrative', {
            'fields': ('status', 'created_by')
        }),
        ('Statistics', {
            'fields': ('acceptance_rate', 'total_submissions', 'accepted_submissions'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    inlines = [TestCaseInline, ProblemVideoSolutionInline, CodeTemplateInline]
    
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 6, 'cols': 80})},
    }

    def difficulty_badge(self, obj):
        colors = {'EASY': '#10B981', 'MEDIUM': '#F59E0B', 'HARD': '#EF4444'}
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px;">{}</span>',
            colors.get(obj.difficulty, '#6B7280'), obj.get_difficulty_display()
        )
    difficulty_badge.short_description = 'Difficulty'
    
    def status_badge(self, obj):
        colors = {'PUBLISHED': '#10B981', 'PENDING_APPROVAL': '#F59E0B', 'DRAFT': '#6B7280', 'ARCHIVED': '#EF4444', 'PRIVATE': '#8B5CF6'}
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px;">{}</span>',
            colors.get(obj.status, '#6B7280'), obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def test_case_count(self, obj):
        return obj.test_cases.count()
    test_case_count.short_description = 'Test Cases'

@admin.register(PracticeSubmission)
class PracticeSubmissionAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'problem_title', 'language_badge', 'status_badge', 
        'passed_cases', 'total_cases', 'submitted_at'
    )
    list_filter = ('status', 'language', 'submitted_at', 'problem__difficulty')
    search_fields = ('user__username', 'problem__title')
    date_hierarchy = 'submitted_at'
    
    readonly_fields = [f.name for f in PracticeSubmission._meta.fields]
    
    fieldsets = (
        ('Submission Info', {
            'fields': ('id', 'user', 'problem', 'language', 'submitted_at')
        }),
        ('Code', {
            'fields': ('code',), 'classes': ('collapse',)
        }),
        ('Evaluation Results', {
            'fields': ('status', 'passed_cases', 'total_cases', 'execution_time', 'memory_used', 'results')
        }),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
    
    def problem_title(self, obj):
        return obj.problem.title
    problem_title.short_description = 'Problem'
    
    def language_badge(self, obj):
        return format_html(
            '<span style="background-color: #3B82F6; color: white; padding: 2px 6px; border-radius: 8px; font-size: 10px;">{}</span>',
            obj.get_language_display()
        )
    language_badge.short_description = 'Language'
    
    def status_badge(self, obj):
        colors = {
            'ACCEPTED': '#10B981', 'WRONG_ANSWER': '#EF4444', 'TIME_LIMIT_EXCEEDED': '#F97316',
            'RUNTIME_ERROR': '#EF4444', 'COMPILATION_ERROR': '#DC2626', 'PENDING': '#F59E0B', 'RUNNING': '#3B82F6'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px;">{}</span>',
            colors.get(obj.status, '#6B7280'), obj.get_status_display()
        )
    status_badge.short_description = 'Status'

@admin.register(UserProblemStats)
class UserProblemStatsAdmin(admin.ModelAdmin):
    list_display = ('user', 'problem_title', 'status_badges', 'total_attempts', 'first_solved_at')
    list_filter = ('is_solved', 'problem__difficulty')
    search_fields = ('user__username', 'problem__title')
    readonly_fields = ('user', 'problem', 'is_solved', 'first_solved_at', 'total_attempts', 'created_at', 'updated_at')
    
    def problem_title(self, obj):
        return obj.problem.title
    problem_title.short_description = 'Problem'
    
    def status_badges(self, obj):
        badges = []
        if obj.is_solved:
            badges.append('<span style="background-color: #10B981; color: white; padding: 2px 6px; border-radius: 8px; font-size: 10px;">Solved</span>')
        elif obj.total_attempts > 0:
            badges.append('<span style="background-color: #F59E0B; color: white; padding: 2px 6px; border-radius: 8px; font-size: 10px;">Attempted</span>')
        return format_html(' '.join(badges)) if badges else '-'
    status_badges.short_description = 'Status'

# --- Register remaining models with default or simple admin views ---
admin.site.register(TestCase)
admin.site.register(Discussion)
admin.site.register(DiscussionVote)
admin.site.register(Badge)
admin.site.register(UserBadge)
admin.site.register(ProblemVideoSolution)

# --- Customize admin site header and titles ---
admin.site.site_header = "MockMate Practice Administration"
admin.site.site_title = "MockMate Practice Admin"
admin.site.index_title = "Welcome to MockMate Practice Administration"