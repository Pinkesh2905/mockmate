# mockmate01/mockmate01/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')), 
    path('courses/', include('courses.urls')),
    path('quizzes/', include('quizzes.urls')),
    path('practice/', include('practice.urls')),
    path('articles/', include('articles.urls')),
    path('aptitude/', include('aptitude.urls')),
    path('mock-interview/', include('mock_interview.urls')),
    path('tutor/', include('tutor.urls', namespace='tutor')),
    path('posts/', include('posts.urls', namespace='posts')),
    
    # Django's built-in authentication URLs (for login, logout, password reset)
    # These provide 'login', 'logout', 'password_reset', etc. view names globally.
    path('accounts/', include('django.contrib.auth.urls')), 
    
    # The 'users' app handles custom signup and profile management
    path('users/', include('users.urls')), 
]

# Only for development: serve media files
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
