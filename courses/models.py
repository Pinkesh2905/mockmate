from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.text import slugify

# Import CONTENT_STATUSES from practice.models (its new home)
from practice.models import CONTENT_STATUSES

# --- Topic Model (now defined here in courses app) ---
class Topic(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    class Meta:
        verbose_name = "Topic"
        verbose_name_plural = "Topics"
        ordering = ['name']
# --- End Topic Model ---


class Course(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)  # Auto-generate if blank
    video_link = models.URLField(blank=True, null=True, help_text="Main introductory video link for the course") # Made optional
    thumbnail = models.URLField(blank=True, help_text="URL for course thumbnail image")
    duration = models.CharField(max_length=50, blank=True, help_text="e.g., '10 hours', '3 weeks'")
    level = models.CharField(max_length=50, blank=True)
    category = models.CharField(max_length=100, blank=True)
    instructor = models.CharField(max_length=255, blank=True) # Can be derived from created_by's profile
    total_lessons = models.PositiveIntegerField(default=0)
    rating = models.FloatField(default=0.0) # This will be calculated from user ratings if implemented
    students = models.PositiveIntegerField(default=0)
    price = models.CharField(max_length=50, default="Free")
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # New fields for role-based content management
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='authored_courses',
        help_text="The user (tutor/staff) who created this course."
    )
    status = models.CharField(
        max_length=20,
        choices=CONTENT_STATUSES,
        default='PUBLISHED',
        help_text="Current status of the course (e.g., Draft, Pending Approval, Published)."
    )

    # Connect courses to topics from this app
    topics = models.ManyToManyField(
        Topic, # Use the Topic model defined in this app
        related_name='courses',
        blank=True,
        help_text="Topics covered in this course"
    )

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        # Generate slug if not provided
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    def get_completion_percentage(self, user):
        """Calculate completion percentage for a specific user"""
        if not self.total_lessons or self.total_lessons == 0: # Handle division by zero
            return 0
        watched_count = WatchedLesson.objects.filter(
            user=user,
            lesson__course=self
        ).count()
        return int((watched_count / self.total_lessons) * 100)


class Enrollment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='course_enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    progress = models.IntegerField(default=0)  # Percentage (0-100)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    last_accessed = models.DateTimeField(auto_now=True)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'course')
        ordering = ['-enrolled_at']

    def __str__(self):
        return f"{self.user.username} enrolled in {self.course.title}"

    def update_progress(self):
        """Update progress based on watched lessons"""
        self.progress = self.course.get_completion_percentage(self.user)
        if self.progress == 100 and not self.completed:
            self.completed = True
            self.completed_at = timezone.now()
        self.save()


class Lesson(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='lessons'
    )
    # Optional: Connect to topics as well
    topic = models.ForeignKey(
        Topic, # Use the Topic model defined in this app
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='course_lessons',
        help_text="Optional: Topic this lesson belongs to"
    )
    title = models.CharField(max_length=200)
    content = models.TextField(blank=True)
    video_url = models.URLField(blank=True, null=True, help_text="Embeddable video URL (e.g., YouTube embed link)")
    order = models.PositiveIntegerField(default=0)
    duration_minutes = models.PositiveIntegerField(default=0)
    is_video_required = models.BooleanField(default=True, help_text="If true, lesson is marked complete only after video is watched.")
    is_free_preview = models.BooleanField(default=False)  # For course previews
    created_at = models.DateTimeField(auto_now_add=True)
    
    # New field: Link lesson to the user who created it (a Tutor/Staff)
    # This is useful if different tutors contribute lessons to a course
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='authored_lessons',
        help_text="The user (tutor/staff) who created this lesson."
    )

    class Meta:
        ordering = ['course', 'order']
        unique_together = ('course', 'order')  # Ensure unique order within course

    def __str__(self):
        return f"{self.course.title} - {self.title}"

    def is_watched_by(self, user):
        """Check if lesson is watched by specific user"""
        return WatchedLesson.objects.filter(user=user, lesson=self).exists()


class WatchedLesson(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='watched_course_lessons')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='watches')
    watched_on = models.DateTimeField(auto_now_add=True)
    watch_duration = models.PositiveIntegerField(default=0, help_text="Seconds watched")

    class Meta:
        unique_together = ('user', 'lesson')
        ordering = ['-watched_on']

    def __str__(self):
        # Corrected typo: Removed extra '(' here
        return f"{self.user.username} watched {self.lesson.title}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update enrollment progress when lesson is watched
        try:
            enrollment = Enrollment.objects.get(user=self.user, course=self.lesson.course)
            enrollment.update_progress()
        except Enrollment.DoesNotExist:
            pass


class Certificate(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='course_certificates')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='certificates')
    issued_on = models.DateTimeField(auto_now_add=True)
    certificate_file = models.FileField(upload_to='certificates/', blank=True, null=True)
    certificate_url = models.URLField(blank=True, null=True)  # For external certificate URLs
    is_generated = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'course')
        ordering = ['-issued_on']

    def __str__(self):
        return f"{self.user.username} - {self.course.title} Certificate"

