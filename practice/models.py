from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator
import json
import uuid

# Define content statuses
CONTENT_STATUSES = (
    ('DRAFT', 'Draft'),
    ('PENDING_APPROVAL', 'Pending Approval'),
    ('PUBLISHED', 'Published'),
    ('ARCHIVED', 'Archived'),
    ('PRIVATE', 'Private'),
)

DIFFICULTY_CHOICES = (
    ('EASY', 'Easy'),
    ('MEDIUM', 'Medium'),
    ('HARD', 'Hard'),
)

PROGRAMMING_LANGUAGES = (
    ('python3', 'Python'),
    ('cpp17', 'C++'),
    ('java', 'Java'),
    ('javascript', 'JavaScript'),
    ('csharp', 'C#'),
    ('go', 'Go'),
    ('rust', 'Rust'),
    ('php', 'PHP'),
    ('ruby', 'Ruby'),
    ('kotlin', 'Kotlin'),
    ('swift', 'Swift'),
)

SUBMISSION_STATUS_CHOICES = [
    ('PENDING', 'Pending'),
    ('RUNNING', 'Running'),
    ('ACCEPTED', 'Accepted'),
    ('WRONG_ANSWER', 'Wrong Answer'),
    ('TIME_LIMIT_EXCEEDED', 'Time Limit Exceeded'),
    ('MEMORY_LIMIT_EXCEEDED', 'Memory Limit Exceeded'),
    ('RUNTIME_ERROR', 'Runtime Error'),
    ('COMPILATION_ERROR', 'Compilation Error'),
    ('PRESENTATION_ERROR', 'Presentation Error'),
    ('INTERNAL_ERROR', 'Internal Error'),
]

class Category(models.Model):
    """Categories for organizing problems"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    color_code = models.CharField(max_length=7, default='#3B82F6')
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

class Tag(models.Model):
    """Tags for problems"""
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

class PracticeProblem(models.Model):
    """Main practice problem model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True, max_length=255)
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='EASY')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='problems')
    tags = models.ManyToManyField(Tag, blank=True, related_name='problems')
    companies = models.CharField(max_length=500, blank=True)
    
    # Problem content
    statement = models.TextField()
    constraints = models.TextField(blank=True)
    hints = models.JSONField(default=list, blank=True)
    
    # Solution and approach
    approach = models.TextField(blank=True)
    time_complexity = models.CharField(max_length=100, blank=True)
    space_complexity = models.CharField(max_length=100, blank=True)
    
    # External references
    leetcode_url = models.URLField(blank=True)
    hackerrank_url = models.URLField(blank=True)
    external_url = models.URLField(blank=True)
    
    # Problem metadata
    acceptance_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    total_submissions = models.IntegerField(default=0)
    accepted_submissions = models.IntegerField(default=0)
    
    # Administrative fields
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=CONTENT_STATUSES, default='PUBLISHED')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_problems')
    
    # Problem settings
    time_limit = models.IntegerField(default=5, validators=[MinValueValidator(1), MaxValueValidator(10)])
    memory_limit = models.IntegerField(default=256, validators=[MinValueValidator(32), MaxValueValidator(512)])
    
    # Premium and private problems
    is_premium = models.BooleanField(default=False)
    is_private = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while PracticeProblem.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        
        # Update acceptance rate
        if self.total_submissions > 0:
            self.acceptance_rate = round((self.accepted_submissions / self.total_submissions) * 100, 2)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    def get_difficulty_color(self):
        colors = {
            'EASY': 'text-green-600',
            'MEDIUM': 'text-yellow-600', 
            'HARD': 'text-red-600'
        }
        return colors.get(self.difficulty, 'text-gray-600')

    def get_difficulty_bg_color(self):
        colors = {
            'EASY': 'bg-green-100 text-green-800',
            'MEDIUM': 'bg-yellow-100 text-yellow-800',
            'HARD': 'bg-red-100 text-red-800'
        }
        return colors.get(self.difficulty, 'bg-gray-100 text-gray-800')

    class Meta:
        ordering = ['-created_at']

class TestCase(models.Model):
    """Test cases for problems"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    problem = models.ForeignKey(PracticeProblem, on_delete=models.CASCADE, related_name='test_cases')
    input_data = models.TextField()
    expected_output = models.TextField()
    
    # Test case types
    is_sample = models.BooleanField(default=False)
    is_hidden = models.BooleanField(default=True)
    
    # Test case metadata
    description = models.CharField(max_length=255, blank=True)
    explanation = models.TextField(blank=True)
    difficulty_weight = models.IntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(10)])
    
    # Execution limits
    time_limit = models.IntegerField(null=True, blank=True)
    memory_limit = models.IntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    order = models.PositiveIntegerField(default=0)

    def clean_input_output(self):
        """Clean and normalize input/output data"""
        self.input_data = self.input_data.strip()
        self.expected_output = self.expected_output.strip()

    def save(self, *args, **kwargs):
        self.clean_input_output()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Test Case for {self.problem.title} ({'Sample' if self.is_sample else 'Hidden'})"

    class Meta:
        ordering = ['order', 'created_at']

class PracticeSubmission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='practice_submissions')
    problem = models.ForeignKey(PracticeProblem, on_delete=models.CASCADE, related_name='submissions')
    
    language = models.CharField(max_length=20, choices=PROGRAMMING_LANGUAGES)
    code = models.TextField()
    
    status = models.CharField(max_length=25, choices=SUBMISSION_STATUS_CHOICES, default='PENDING')
    
    # Execution details
    execution_time = models.FloatField(null=True, blank=True, help_text="Execution time in seconds")
    memory_used = models.IntegerField(null=True, blank=True, help_text="Memory used in KB")
    
    # --- NEW: Fields to store detailed evaluation results ---
    results = models.JSONField(null=True, blank=True, help_text="Stores detailed results for each test case")
    passed_cases = models.IntegerField(default=0, help_text="Number of test cases passed")
    total_cases = models.IntegerField(default=0, help_text="Total number of test cases evaluated")
    # --- END NEW ---

    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f"Submission by {self.user.username} for {self.problem.title} [{self.status}]"

class UserProblemStats(models.Model):
    """Track user statistics for each problem"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='problem_stats')
    problem = models.ForeignKey(PracticeProblem, on_delete=models.CASCADE, related_name='user_stats')
    
    # Progress tracking
    is_attempted = models.BooleanField(default=False)
    is_solved = models.BooleanField(default=False)
    first_solved_at = models.DateTimeField(null=True, blank=True)
    best_submission = models.ForeignKey(PracticeSubmission, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Statistics
    total_attempts = models.IntegerField(default=0)
    best_runtime = models.FloatField(default=0.0)
    best_memory = models.FloatField(default=0.0)
    best_score = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'problem']
        indexes = [
            models.Index(fields=['user', 'is_solved']),
            models.Index(fields=['user', 'is_attempted']),
        ]

class UserStats(models.Model):
    """Overall user statistics for the practice platform"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='practice_stats')
    
    # Problem solving stats
    problems_solved = models.IntegerField(default=0)
    problems_attempted = models.IntegerField(default=0)
    total_submissions = models.IntegerField(default=0)
    accepted_submissions = models.IntegerField(default=0)
    
    # Difficulty breakdown
    easy_solved = models.IntegerField(default=0)
    medium_solved = models.IntegerField(default=0)
    hard_solved = models.IntegerField(default=0)
    
    # Gamification
    total_points = models.IntegerField(default=0)
    rank = models.IntegerField(default=0)
    
    # Language preferences
    preferred_language = models.CharField(max_length=20, choices=PROGRAMMING_LANGUAGES, default='python3')
    languages_used = models.JSONField(default=dict)
    
    # Streaks and achievements
    current_streak = models.IntegerField(default=0)
    max_streak = models.IntegerField(default=0)
    last_solved_date = models.DateField(null=True, blank=True)
    
    # Performance metrics
    average_runtime = models.FloatField(default=0.0)
    total_contest_rating = models.IntegerField(default=1500)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def update_streak(self):
        """Update daily solving streak"""
        today = timezone.now().date()
        
        if self.last_solved_date:
            if self.last_solved_date == today:
                return  # Already solved today
            elif self.last_solved_date == today - timezone.timedelta(days=1):
                self.current_streak += 1
            else:
                self.current_streak = 1
        else:
            self.current_streak = 1
        
        self.last_solved_date = today
        self.max_streak = max(self.max_streak, self.current_streak)
        self.save()

    def __str__(self):
        return f"{self.user.username} - Practice Stats"

class Discussion(models.Model):
    """Discussion forum for each problem"""
    problem = models.ForeignKey(PracticeProblem, on_delete=models.CASCADE, related_name='discussions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='problem_discussions')
    
    title = models.CharField(max_length=255)
    content = models.TextField()
    
    # Discussion metadata
    is_solution = models.BooleanField(default=False)
    is_pinned = models.BooleanField(default=False)
    upvotes = models.IntegerField(default=0)
    downvotes = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.problem.title} - {self.title}"

    class Meta:
        ordering = ['-is_pinned', '-created_at']

class DiscussionVote(models.Model):
    """Voting system for discussions"""
    VOTE_CHOICES = [
        (1, 'Upvote'),
        (-1, 'Downvote'),
    ]
    
    discussion = models.ForeignKey(Discussion, on_delete=models.CASCADE, related_name='votes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='discussion_votes')
    vote = models.IntegerField(choices=VOTE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['discussion', 'user']

class Badge(models.Model):
    """Gamification badge for user achievements"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    image_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class UserBadge(models.Model):
    """Represents a badge awarded to a user"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='badges')
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE, related_name='awarded_to')
    awarded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'badge']
        ordering = ['-awarded_at']

class ProblemVideoSolution(models.Model):
    """Links a video solution to a practice problem"""
    problem = models.ForeignKey(PracticeProblem, on_delete=models.CASCADE, related_name='video_solutions')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=255)
    url = models.URLField()
    is_premium = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Video Solution for {self.problem.title}"

class CodeTemplate(models.Model):
    """Code templates for different programming languages"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    problem = models.ForeignKey(PracticeProblem, on_delete=models.CASCADE, related_name='code_templates')
    language = models.CharField(max_length=20, choices=PROGRAMMING_LANGUAGES, default='python3')
    starter_code = models.TextField(help_text="Initial code template for users")
    solution_code = models.TextField(blank=True, help_text="Reference solution (optional)")
    is_default = models.BooleanField(default=False, help_text="Default template for this language")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Ensure only one default template per language per problem
        if self.is_default:
            CodeTemplate.objects.filter(
                problem=self.problem,
                language=self.language,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.problem.title} - {self.get_language_display()}"

    class Meta:
        unique_together = ['problem', 'language']
        ordering = ['language']