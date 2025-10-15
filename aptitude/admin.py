from django.contrib import admin
from .models import (
    AptitudeCategory,
    AptitudeTopic,
    AptitudeProblem,
    AptitudeSubmission,
    PracticeSet
)


@admin.register(AptitudeCategory)
class AptitudeCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name",)


@admin.register(AptitudeTopic)
class AptitudeTopicAdmin(admin.ModelAdmin):
    list_display = ("name", "category")
    list_filter = ("category",)
    search_fields = ("name",)


class AptitudeProblemAdmin(admin.ModelAdmin):
    list_display = ("id", "topic", "difficulty", "question_text_short", "correct_option", "created_at")
    list_filter = ("topic__category", "difficulty")
    search_fields = ("question_text",)
    ordering = ("-created_at",)

    def question_text_short(self, obj):
        return (obj.question_text[:75] + "...") if len(obj.question_text) > 75 else obj.question_text
    question_text_short.short_description = "Question"


@admin.register(AptitudeSubmission)
class AptitudeSubmissionAdmin(admin.ModelAdmin):
    list_display = ("user", "problem", "selected_option", "is_correct", "submitted_at")
    list_filter = ("is_correct", "submitted_at", "problem__topic__category")
    search_fields = ("user__username", "problem__question_text")


class PracticeSetAdmin(admin.ModelAdmin):
    list_display = ("title", "created_by", "created_at", "total_questions")
    filter_horizontal = ("problems",)
    search_fields = ("title", "description")
    list_filter = ("created_at",)

    def total_questions(self, obj):
        return obj.problems.count()


# Register with custom admin classes
admin.site.register(AptitudeProblem, AptitudeProblemAdmin)
admin.site.register(PracticeSet, PracticeSetAdmin)
