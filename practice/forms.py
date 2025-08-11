from django import forms
# Removed UserCreationForm and User imports as signup forms are moved
# from .models import Topic, UserProfile # Removed as Topic is in core, UserProfile in users
from .models import PracticeProblem, TestCase # <--- NEW: Import PracticeProblem, TestCase

# Assuming UserProfile and SignupForm are now in the 'users' app
# from users.models import UserProfile
# from users.forms import SignupForm # If you move SignupForm to users/forms.py

# You might still need Topic if ProblemForm uses it, but based on your previous models.py,
# PracticeProblem does not have a direct Topic ForeignKey.
# If ProblemForm needs Topic, you'd import it from the correct app (e.g., 'core.models' if Topic is still there,
# or 'articles.models' or 'courses.models' if Topic moved there).
# For now, I'm assuming ProblemForm only needs PracticeProblem.

class ProblemForm(forms.ModelForm):
    class Meta:
        model = PracticeProblem # <--- This model needs to be imported
        fields = [
            'title', 'slug', 'difficulty', 'companies', 'url',
            'statement', 'template_python', 'template_cpp', 'template_java'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border rounded-lg focus:ring-blue-500 focus:border-blue-500'}),
            'slug': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border rounded-lg focus:ring-blue-500 focus:border-blue-500', 'placeholder': 'Auto-generated from title, or enter manually'}),
            'difficulty': forms.Select(attrs={'class': 'w-full px-3 py-2 border rounded-lg focus:ring-blue-500 focus:border-blue-500'}),
            'companies': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border rounded-lg focus:ring-blue-500 focus:border-blue-500', 'placeholder': 'Comma-separated companies (e.g., Google, Amazon)'}),
            'url': forms.URLInput(attrs={'class': 'w-full px-3 py-2 border rounded-lg focus:ring-blue-500 focus:border-blue-500', 'placeholder': 'Optional: Link to external problem source'}),
            'statement': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border rounded-lg focus:ring-blue-500 focus:border-blue-500', 'rows': 10}),
            'template_python': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border rounded-lg focus:ring-blue-500 focus:border-blue-500', 'rows': 8, 'font-family': 'monospace'}),
            'template_cpp': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border rounded-lg focus:ring-blue-500 focus:border-blue-500', 'rows': 8, 'font-family': 'monospace'}),
            'template_java': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border rounded-lg focus:ring-blue-500 focus:border-blue-500', 'rows': 8, 'font-family': 'monospace'}),
        }
        labels = {
            'template_python': 'Python Starter Code',
            'template_cpp': 'C++ Starter Code',
            'template_java': 'Java Starter Code',
        }


from django.forms import inlineformset_factory
from .models import TestCase

TestCaseFormSet = inlineformset_factory(
    PracticeProblem,
    TestCase,
    fields=['input', 'expected_output', 'is_sample'],
    extra=1,
    can_delete=True,
    widgets={
        'input': forms.Textarea(attrs={'rows': 3, 'class': 'w-full px-3 py-2 border rounded-lg'}),
        'expected_output': forms.Textarea(attrs={'rows': 3, 'class': 'w-full px-3 py-2 border rounded-lg'}),
        'is_sample': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5 text-blue-600'}),
    }
)

# Removed StudentSignUpForm and TutorSignUpForm
# class StudentSignUpForm(UserCreationForm):
#     class Meta(UserCreationForm.Meta):
#         model = User
#         fields = UserCreationForm.Meta.fields + ('email',)

# class TutorSignUpForm(UserCreationForm):
#     class Meta(UserCreationForm.Meta):
#         model = User
#         fields = UserCreationForm.Meta.fields + ('email',)

# Removed ContentCreateForm and ContentSubmissionForm
# class ContentCreateForm(forms.ModelForm):
#     class Meta:
#         model = Topic
#         fields = ['name', 'slug', 'description']

# class ContentSubmissionForm(forms.Form):
#     source_type = forms.ChoiceField(choices=[('url', 'URL'), ('upload', 'Upload')])
#     url = forms.URLField(required=False)
#     file = forms.FileField(required=False)
#     title = forms.CharField(max_length=200)
#     category = forms.CharField(max_length=100, required=False)
#     tags = forms.CharField(required=False, help_text="Comma-separated tags")
#     topic_slug = forms.CharField(required=False)
