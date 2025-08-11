from django.urls import path
from . import views

app_name = "articles"

urlpatterns = [
    # Public/Student Facing Paths
    path('', views.article_list, name='article_list'),
    path('<slug:slug>/', views.article_detail, name='article_detail'),
    path('<slug:slug>/comment/', views.add_comment, name='add_comment'),
    path('<slug:slug>/like/', views.toggle_like, name='toggle_like'),
    path('<slug:slug>/rate/', views.submit_rating, name='submit_rating'),

    # Tutor/Staff Paths
    path('tutor/my-articles/', views.tutor_article_list, name='tutor_article_list'),
    path('tutor/articles/add/', views.article_create_edit, name='article_add'),
    path('tutor/articles/edit/<slug:slug>/', views.article_create_edit, name='article_edit'),

    # Admin Paths (for approval)
    path('admin_panel/articles/<slug:article_slug>/<str:action>/', views.admin_article_approval, name='admin_article_approval'),
]
