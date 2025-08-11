# mock_interview/forms.py
from django import forms
from .models import MockInterviewSession


class InterviewSetupForm(forms.ModelForm):
    """
    Form for students to set up a mock interview session.
    Optional resume upload will be parsed by AI to prefill fields.
    """
    resume_file = forms.FileField(
        required=False,
        label="Upload Resume (PDF/DOCX/TXT)",
        help_text="Optional: Upload your resume to automatically detect your job role and skills."
    )

    class Meta:
        model = MockInterviewSession
        fields = ['job_role', 'key_skills']  # resume_file is handled separately
        widgets = {
            'job_role': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Full Stack Developer, Data Scientist'
            }),
            'key_skills': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Comma-separated skills (e.g., Python, Django, React)',
                'rows': 3
            }),
        }
        labels = {
            'job_role': 'Target Job Role',
            'key_skills': 'Key Skills',
        }

    def clean_resume_file(self):
        file = self.cleaned_data.get('resume_file')
        if file:
            allowed_types = ['application/pdf',
                             'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                             'application/msword',
                             'text/plain']
            if file.content_type not in allowed_types:
                raise forms.ValidationError("Unsupported file type. Please upload PDF, DOCX, DOC, or TXT.")
            if file.size > 5 * 1024 * 1024:  # 5MB limit
                raise forms.ValidationError("File too large. Maximum size is 5 MB.")
        return file
