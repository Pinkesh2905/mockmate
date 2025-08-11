# mockmate01/users/urls.py
from django.urls import path
from . import views

app_name = 'users' # Namespace for this app's URLs

urlpatterns = [
    path('signup/', views.signup, name='signup'), # Main signup view
    path('profile/', views.profile, name='profile'), # User profile page
    path('profile/<str:username>/', views.public_profile, name='public_profile'), # Public profile view by username
]
