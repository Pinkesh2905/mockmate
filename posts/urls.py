# posts/urls.py
from django.urls import path
from . import views

app_name = 'posts'

urlpatterns = [
    path('', views.feed_view, name='feed'),
    path('like/<uuid:post_id>/', views.toggle_like, name='toggle_like'),
    path('comment/<uuid:post_id>/', views.add_comment, name='add_comment'),
    path('repost/<uuid:post_id>/', views.repost, name='repost'),
    path('<str:username>/', views.user_profile, name='user_profile'),
    path('edit/<uuid:post_id>/', views.edit_post, name='edit_post'),
    path('delete/<uuid:post_id>/', views.delete_post, name='delete_post'),
    # path('view/<uuid:post_id>/', views.view_post_modal, name='view_post_modal'),
    path('<uuid:post_id>/modal/', views.view_post_modal, name='post_modal'),
]
