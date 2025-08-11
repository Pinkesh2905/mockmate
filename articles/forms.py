from django import forms
from .models import Article, Comment, Rating

class ArticleForm(forms.ModelForm):
    """
    Form for tutors to create/edit Article instances.
    Status and created_by fields will be handled in the view.
    """
    class Meta:
        model = Article
        fields = [
            'title', 'content', # Slug, created_by, status will be set by view
        ]
        widgets = {
            'content': forms.Textarea(attrs={'rows': 20, 'class': 'font-mono'}),
        }
        labels = {
            'content': 'Article Content (supports basic Markdown)',
        }

class CommentForm(forms.ModelForm):
    """
    Form for students to add comments to an article.
    """
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Write your comment here...', 'class': 'w-full p-2 border rounded-md focus:ring-blue-500 focus:border-blue-500'}),
        }
        labels = {
            'content': '', # No label for a cleaner look
        }

class RatingForm(forms.ModelForm):
    """
    Form for students to rate an article.
    """
    score = forms.IntegerField(
        widget=forms.HiddenInput(), # Hidden input, score will be set via JS (e.g., star rating)
        min_value=1,
        max_value=5
    )

    class Meta:
        model = Rating
        fields = ['score']
