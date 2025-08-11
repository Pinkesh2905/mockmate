from django import forms
from django.forms.models import inlineformset_factory
from .models import Course, Lesson, Topic # <--- CORRECTED: Import Topic from here

class CourseForm(forms.ModelForm):
    """
    Form for tutors to create/edit Course instances.
    Status and created_by fields will be handled in the view.
    """
    # Use ModelChoiceField for topics to allow selecting existing topics
    topics = forms.ModelMultipleChoiceField(
        queryset=Topic.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text="Select topics covered in this course."
    )

    class Meta:
        model = Course
        fields = [
            'title', 'description', 'video_link', 'thumbnail',
            'duration', 'level', 'category', 'instructor', 'price', 'topics'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 8}),
            'video_link': forms.URLInput(attrs={'placeholder': 'e.g., https://www.youtube.com/embed/VIDEO_ID'}),
            'thumbnail': forms.URLInput(attrs={'placeholder': 'URL to course thumbnail image'}),
        }
        labels = {
            'video_link': 'Introductory Video Link',
            'thumbnail': 'Thumbnail Image URL',
        }

class LessonForm(forms.ModelForm):
    """
    Form for adding/editing individual Lessons.
    """
    class Meta:
        model = Lesson
        fields = ['title', 'order', 'video_url', 'content', 'duration_minutes', 'is_video_required', 'is_free_preview', 'topic']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 10}),
            'video_url': forms.URLInput(attrs={'placeholder': 'e.g., https://www.youtube.com/embed/VIDEO_ID'}),
        }
        labels = {
            'video_url': 'Lesson Video Link',
            'duration_minutes': 'Duration (minutes)',
        }

# Formset for managing multiple Lessons within a CourseForm
LessonFormSet = inlineformset_factory(
    Course,
    Lesson,
    form=LessonForm,
    extra=1, # Number of empty forms to display
    can_delete=True,
    min_num=0, # Allow courses with no lessons initially
    validate_min=False, # Don't require minimum lessons for initial save
)
