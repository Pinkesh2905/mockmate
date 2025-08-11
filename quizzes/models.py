from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.template.defaultfilters import slugify
from django.core.validators import MinValueValidator, MaxValueValidator

# IMPORTANT: Import Course model from the 'courses' app
from courses.models import Course

# Import CONTENT_STATUSES from practice.models (its single source of truth)
from practice.models import CONTENT_STATUSES


class Quiz(models.Model):
    """
    Represents a quiz. Can be standalone or linked to a course.
    """
    title = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField(blank=True, help_text="A brief description of the quiz.")
    
    # Optional link to a Course
    course = models.ForeignKey(
        Course,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='quizzes',
        help_text="Optional: The course this quiz is associated with."
    )
    
    passing_score = models.IntegerField(
        default=70,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Minimum percentage score required to pass the quiz."
    )
    duration_minutes = models.IntegerField(
        default=30,
        validators=[MinValueValidator(1)],
        help_text="Maximum duration allowed for the quiz in minutes."
    )
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_quizzes',
        help_text="The user (tutor/staff) who created this quiz."
    )
    status = models.CharField(
        max_length=20,
        choices=CONTENT_STATUSES, # Use imported CONTENT_STATUSES
        default='PUBLISHED',
        help_text="Current status of the quiz (e.g., Draft, Pending Approval, Published)."
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Quizzes"
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    @property
    def total_questions(self):
        return self.questions.count()


class Question(models.Model):
    """
    Represents a single question within a quiz.
    """
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField(help_text="The question text.")
    # Optional: type of question (e.g., 'MCQ', 'TrueFalse', 'ShortAnswer')
    # For simplicity, we'll assume MCQ for now.
    
    class Meta:
        ordering = ['id'] # Maintain order of questions within a quiz

    def __str__(self):
        return f"Q: {self.text[:50]}..."


class Answer(models.Model):
    """
    Represents an answer choice for a question.
    """
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    text = models.CharField(max_length=255, help_text="The answer choice text.")
    is_correct = models.BooleanField(default=False, help_text="True if this is the correct answer.")
    
    class Meta:
        ordering = ['id'] # Maintain order of answers for a question

    def __str__(self):
        return f"A: {self.text[:50]}... (Correct: {self.is_correct})"


class QuizAttempt(models.Model):
    """
    Records a student's attempt at a quiz.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_attempts')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    score = models.IntegerField(default=0, help_text="Score obtained by the user (raw points).")
    percentage_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text="Percentage score obtained by the user."
    )
    passed = models.BooleanField(default=False, help_text="Whether the user passed the quiz.")
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    # Store student's chosen answers as JSON for review
    selected_answers = models.JSONField(
        blank=True,
        null=True,
        help_text="JSON of selected answers: {question_id: [answer_id, ...]}"
    )

    class Meta:
        ordering = ['-start_time']

    def __str__(self):
        return f"{self.user.username}'s attempt on {self.quiz.title} ({self.percentage_score}%)"

    def calculate_score(self):
        """Calculates the score and percentage based on selected answers."""
        total_questions = self.quiz.questions.count()
        correct_answers_count = 0
        
        if self.selected_answers and total_questions > 0:
            for q_id_str, selected_ans_ids in self.selected_answers.items():
                try:
                    question = Question.objects.get(id=int(q_id_str))
                    # Assuming single choice for now, if multiple, adjust logic
                    if selected_ans_ids and isinstance(selected_ans_ids, list):
                        selected_answer_id = selected_ans_ids[0] # Take the first selected answer
                        correct_answer = question.answers.filter(is_correct=True).first()
                        if correct_answer and correct_answer.id == selected_answer_id:
                            correct_answers_count += 1
                except Question.DoesNotExist:
                    continue # Skip if question not found

            self.score = correct_answers_count
            self.percentage_score = (correct_answers_count / total_questions) * 100
            self.passed = self.percentage_score >= self.quiz.passing_score
        else:
            self.score = 0
            self.percentage_score = 0.00
            self.passed = False
        
        self.save()

