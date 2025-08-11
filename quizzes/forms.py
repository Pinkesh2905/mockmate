from django import forms
from django.forms.models import inlineformset_factory
from .models import Quiz, Question, Answer, QuizAttempt

class QuizForm(forms.ModelForm):
    """
    Form for tutors to create/edit Quiz instances.
    Status and created_by fields will be handled in the view.
    """
    class Meta:
        model = Quiz
        fields = [
            'title', 'slug', 'description', 'course', 'passing_score', 'duration_minutes'
        ]
        widgets = {
            'slug': forms.TextInput(attrs={'placeholder': 'Auto-generated from title, or enter manually'}),
            'description': forms.Textarea(attrs={'rows': 5}),
        }
        labels = {
            'duration_minutes': 'Duration (minutes)',
        }

class QuestionForm(forms.ModelForm):
    """
    Form for adding/editing individual Questions.
    """
    class Meta:
        model = Question
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={'rows': 3}),
        }

class AnswerForm(forms.ModelForm):
    """
    Form for adding/editing individual Answers.
    """
    class Meta:
        model = Answer
        fields = ['text', 'is_correct']
        widgets = {
            'text': forms.TextInput(attrs={'class': 'w-full p-2 border rounded-md'}),
            'is_correct': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5 text-blue-600'})
        }

# Formsets for managing nested forms (Quiz -> Questions -> Answers)
QuestionFormSet = inlineformset_factory(
    Quiz,
    Question,
    form=QuestionForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
)

AnswerFormSet = inlineformset_factory(
    Question,
    Answer,
    form=AnswerForm,
    extra=1,
    can_delete=True,
    min_num=2, # At least two answers per question
    validate_min=True,
)

# Form for students to submit answers for a quiz attempt
class QuizAttemptForm(forms.Form):
    """
    A dynamic form to capture a student's selected answers for a quiz.
    Questions and answers are added dynamically in the view.
    """
    def __init__(self, *args, **kwargs):
        self.quiz = kwargs.pop('quiz')
        super().__init__(*args, **kwargs)
        
        for i, question in enumerate(self.quiz.questions.all()):
            choices = [(str(answer.id), answer.text) for answer in question.answers.all()]
            # Assuming single choice for now (RadioSelect)
            self.fields[f'question_{question.id}'] = forms.ChoiceField(
                label=f'Question {i+1}: {question.text}',
                choices=choices,
                widget=forms.RadioSelect,
                required=True
            )
            # Add a hidden field for the question ID to easily map answers
            self.fields[f'question_{question.id}'].question_id = question.id
