from django import forms
from .models import (
    AptitudeCategory,
    AptitudeTopic,
    AptitudeProblem,
    PracticeSet
)


class AptitudeCategoryForm(forms.ModelForm):
    class Meta:
        model = AptitudeCategory
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Category name"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Short description"}),
        }


class AptitudeTopicForm(forms.ModelForm):
    class Meta:
        model = AptitudeTopic
        fields = ["category", "name", "description"]
        widgets = {
            "category": forms.Select(attrs={"class": "form-control"}),
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Topic name"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class AptitudeProblemForm(forms.ModelForm):
    class Meta:
        model = AptitudeProblem
        fields = [
            "topic",
            "question_text",
            "option_a",
            "option_b",
            "option_c",
            "option_d",
            "correct_option",
            "explanation",
            "difficulty",
        ]
        widgets = {
            "topic": forms.Select(attrs={"class": "form-control"}),
            "question_text": forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "Enter the question"}),
            "option_a": forms.TextInput(attrs={"class": "form-control", "placeholder": "Option A"}),
            "option_b": forms.TextInput(attrs={"class": "form-control", "placeholder": "Option B"}),
            "option_c": forms.TextInput(attrs={"class": "form-control", "placeholder": "Option C"}),
            "option_d": forms.TextInput(attrs={"class": "form-control", "placeholder": "Option D"}),
            "correct_option": forms.Select(attrs={"class": "form-control"}),
            "explanation": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Explain the solution (optional)"}),
            "difficulty": forms.Select(attrs={"class": "form-control"}),
        }


class PracticeSetForm(forms.ModelForm):
    class Meta:
        model = PracticeSet
        fields = ["title", "description", "problems"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Practice Set Title"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "problems": forms.SelectMultiple(attrs={"class": "form-control"}),
        }
