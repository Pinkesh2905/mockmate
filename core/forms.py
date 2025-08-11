# from django import forms
# from django.contrib.auth.forms import UserCreationForm
# from django.contrib.auth.models import User
# from .models import Topic

# class SignupForm(UserCreationForm):
#     email = forms.EmailField(required=True, widget=forms.EmailInput())

#     class Meta:
#         model = User
#         fields = ['username', 'email', 'password1', 'password2']


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
