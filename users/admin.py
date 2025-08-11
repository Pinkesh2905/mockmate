from django.contrib import admin
from .models import UserProfile # Import UserProfile from users.models

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'is_approved_tutor', 'created_at')
    list_filter = ('role', 'is_approved_tutor')
    search_fields = ('user__username', 'user__email', 'bio')
    readonly_fields = ('created_at', 'updated_at')
    # Allow admins to change roles and approval status
    fields = ('user', 'role', 'is_approved_tutor', 'avatar', 'bio', 'github', 'linkedin', 'created_at', 'updated_at')

