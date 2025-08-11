from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.template.defaultfilters import slugify # For auto-generating slugs
from django.core.validators import MinValueValidator, MaxValueValidator

# Import CONTENT_STATUSES from practice.models (its single source of truth)
from practice.models import CONTENT_STATUSES

# If you want to associate Articles with Topics, you would import Topic here
# from courses.models import Topic # Example: if you decide to add a topic field to Article


class Article(models.Model):
    """
    Stores each article created by a tutor/staff.
    """
    title = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True) # Blank for auto-generation
    content = models.TextField(help_text="Full content of the article (supports Markdown if you implement a renderer)")
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='authored_articles',
        help_text="The user (tutor/staff) who created this article."
    )
    status = models.CharField(
        max_length=20,
        choices=CONTENT_STATUSES, # Use imported CONTENT_STATUSES
        default='DRAFT',
        help_text="Current status of the article (e.g., Draft, Pending Approval, Published)."
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    # Example of adding a Topic foreign key if desired in the future:
    # topic = models.ForeignKey(
    #     Topic,
    #     on_delete=models.SET_NULL,
    #     null=True,
    #     blank=True,
    #     related_name='articles',
    #     help_text="The main topic this article belongs to."
    # )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    @property
    def average_rating(self):
        """Calculates the average rating for the article."""
        return self.ratings.aggregate(models.Avg('score'))['score__avg'] or 0.0

    @property
    def total_likes(self):
        """Returns the total number of likes for the article."""
        return self.likes.count()


class Comment(models.Model):
    """
    Stores comments on articles.
    """
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='article_comments')
    content = models.TextField(help_text="The content of the comment.")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at'] # Order by oldest first for comments

    def __str__(self):
        return f"Comment by {self.user.username} on {self.article.title}"


class Like(models.Model):
    """
    Stores likes on articles. Ensures a user can only like an article once.
    """
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='article_likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('article', 'user') # Ensures one like per user per article
        ordering = ['-created_at']

    def __str__(self):
        return f"Like by {self.user.username} on {self.article.title}"


class Rating(models.Model):
    """
    Stores ratings for articles (e.g., 1-5 stars). Ensures a user can only rate an article once.
    """
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='article_ratings')
    score = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating score (1 to 5)."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('article', 'user') # Ensures one rating per user per article
        ordering = ['-created_at']

    def __str__(self):
        return f"Rating {self.score} by {self.user.username} on {self.article.title}"

