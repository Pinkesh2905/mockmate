from django.contrib import admin
from .models import Article, Comment, Like, Rating

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_by', 'status', 'created_at', 'updated_at', 'average_rating', 'total_likes')
    prepopulated_fields = {'slug': ('title',)}
    search_fields = ('title', 'content', 'created_by__username')
    list_filter = ('status', 'created_at', 'created_by')
    # Make created_by and status editable by admins
    fields = (
        'title', 'slug', 'content', 'created_by', 'status',
        'created_at', 'updated_at' # Add these for display, but make them readonly
    )
    readonly_fields = ('created_at', 'updated_at')

    # Override save_model to set created_by if not set (e.g., if created via admin by superuser)
    def save_model(self, request, obj, form, change):
        if not obj.pk and not obj.created_by: # Only set if new and created_by is not manually chosen
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('article', 'user', 'created_at', 'content')
    search_fields = ('article__title', 'user__username', 'content')
    list_filter = ('created_at', 'user', 'article')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ('article', 'user', 'created_at')
    search_fields = ('article__title', 'user__username')
    list_filter = ('created_at', 'user', 'article')
    readonly_fields = ('created_at',)

@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('article', 'user', 'score', 'created_at', 'updated_at')
    search_fields = ('article__title', 'user__username')
    list_filter = ('score', 'created_at', 'user', 'article')
    readonly_fields = ('created_at', 'updated_at')
