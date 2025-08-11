# posts/admin.py

from django.contrib import admin
from .models import Post, Comment, Like, Repost

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['author', 'created_at', 'content']

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['author', 'created_at', 'content']

@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ('user', 'post', 'created_at')
    search_fields = ('user__username', 'post__content')

@admin.register(Repost)
class RepostAdmin(admin.ModelAdmin):
    list_display = ('user', 'original_post', 'created_at')
    search_fields = ('user__username', 'original_post__content')
