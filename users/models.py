# mockmate01/users/models.py
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    """
    Extends Django's built-in User model to store additional profile information.
    """
    ROLE_CHOICES = [
        ('STUDENT', 'Student'),
        ('TUTOR', 'Tutor'),
        ('ADMIN', 'Admin'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile') # IMPORTANT: related_name='profile'
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='STUDENT', help_text="Role of the user on the platform.")
    is_approved_tutor = models.BooleanField(default=False, help_text="Designates if a tutor account has been approved by an admin.")
    
    # Profile fields
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, help_text="Profile picture")
    bio = models.TextField(blank=True, null=True, max_length=500, help_text="A short biography about the user.") # Added max_length
    github = models.URLField(blank=True, null=True, help_text="Link to GitHub profile")
    linkedin = models.URLField(blank=True, null=True, help_text="Link to LinkedIn profile")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self):
        return f"{self.user.username}'s profile"

    def get_role_display(self):
        """Returns the human-readable role."""
        return dict(self.ROLE_CHOICES).get(self.role, self.role)

# --- Signals to create and save UserProfile automatically ---
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Signal receiver to create a UserProfile whenever a new User is created.
    """
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Signal receiver to save the UserProfile whenever the User is saved.
    """
    # Ensure profile exists before saving, especially for existing users
    if hasattr(instance, 'profile'):
        instance.profile.save()

