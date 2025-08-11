# mockmate01/tutor/urls.py
from django.urls import path
from . import views
from mock_interview import views as mock_views  # Import mock interview review views

app_name = 'tutor'

urlpatterns = [
    # Tutor Dashboard
    path('dashboard/', views.tutor_dashboard, name='dashboard'),

    # Content Management
    path('create-update/', views.tutor_content_create_update, name='create_update'),
    path('upload-csv/', views.upload_csv, name='upload_csv'),

    # Mock Interview Review Management
    path('mock-interviews/reviews/', 
         mock_views.tutor_interview_review_list, 
         name='mock_interview_review_list'),
         
    path('mock-interviews/reviews/<int:session_id>/', 
         mock_views.tutor_review_interview_detail, 
         name='mock_interview_review_detail'),
]
