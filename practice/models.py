from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Define content statuses (relevant to PracticeProblem)
CONTENT_STATUSES = (
    ('DRAFT', 'Draft'),
    ('PENDING_APPROVAL', 'Pending Approval'),
    ('PUBLISHED', 'Published'),
    ('ARCHIVED', 'Archived'),
)


class PracticeProblem(models.Model):
    """
    Stores each practice coding problem.
    """
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    difficulty = models.CharField(max_length=50, blank=True)
    companies = models.CharField(
        max_length=255, blank=True,
        help_text="Optional: companies where this problem was asked"
    )
    url = models.URLField(blank=True, help_text="Optional external link if any")
    statement = models.TextField(help_text="Full problem description")
    sample_input = models.TextField(blank=True, help_text="Sample input for problem")
    sample_output = models.TextField(blank=True, help_text="Sample output for problem")
    created_at = models.DateTimeField(default=timezone.now)
    # New field: status for content approval workflow
    status = models.CharField(
        max_length=20,
        choices=CONTENT_STATUSES,
        default='PUBLISHED',
        help_text="Current status of the problem (e.g., Draft, Pending Approval, Published)."
    )
    # New field: Link problem to the user who created it (a Tutor/Staff)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL, # If user is deleted, problem remains but creator is null
        null=True,
        blank=True,
        related_name='created_problems',
        help_text="The user (tutor/staff) who created this problem."
    )

    # Starter templates for various languages
    template_python = models.TextField(blank=True, null=True)
    template_cpp = models.TextField(blank=True, null=True)
    template_java = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']


class TestCase(models.Model):
    """
    Stores test cases for each PracticeProblem.
    """
    problem = models.ForeignKey(
        PracticeProblem,
        on_delete=models.CASCADE,
        related_name='test_cases'
    )
    input = models.TextField(help_text="Input for the test case")
    expected_output = models.TextField(help_text="Expected output for the test case")
    is_sample = models.BooleanField(
        default=False,
        help_text="True if this is a sample test case visible to the user"
    )
    # Optional: Add a description for sample test cases
    description = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Test Case for {self.problem.title} (Sample: {self.is_sample})"

    class Meta:
        ordering = ['id'] # Order by ID to maintain consistent test case order


class PracticeSubmission(models.Model):
    """
    Each user submission for a PracticeProblem, storing code, language, and result.
    """
    # Choices for submission status
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('ACCEPTED', 'Accepted'),
        ('WRONG_ANSWER', 'Wrong Answer'),
        ('TIME_LIMIT_EXCEEDED', 'Time Limit Exceeded'),
        ('RUNTIME_ERROR', 'Runtime Error'),
        ('COMPILATION_ERROR', 'Compilation Error'),
        ('UNKNOWN_ERROR', 'Unknown Error'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='practice_submissions'
    )
    problem = models.ForeignKey(
        PracticeProblem,
        on_delete=models.CASCADE,
        related_name='submissions'
    )
    code = models.TextField(help_text="User's submitted code")
    language = models.CharField(
        max_length=20,
        default='python3',
        help_text="Language of submission: python3, cpp, java, etc."
    )
    # Result from JDoodle (raw output)
    raw_output = models.TextField(
        blank=True,
        help_text="Raw execution output from JDoodle"
    )
    # Overall status of the submission
    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default='PENDING',
        help_text="Status of the submission (e.g., Accepted, Wrong Answer)"
    )
    # Store detailed test case results as JSON
    test_results = models.JSONField(
        blank=True,
        null=True,
        help_text="Detailed results for each test case (JSON format)"
    )
    cpu_time = models.CharField(max_length=50, blank=True, null=True)
    memory = models.CharField(max_length=50, blank=True, null=True)

    submission_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} | {self.problem.title} | {self.language} | {self.status}"

    class Meta:
        ordering = ['-submission_time']
