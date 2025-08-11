from django.urls import path
from . import views

app_name = "mock_interview"

# Group URLs by functionality for better organization
urlpatterns = [
    # --- Student Interview Flow ---
    path('', views.interview_setup, name='interview_setup'),
    path('start/', views.start_mock_interview, name='start_mock_interview'),  # New endpoint
    path('<int:session_id>/start/', views.main_interview, name='main_interview'),
    path('<int:session_id>/review/', views.review_interview, name='review_interview'),
    
    # --- Interview Interaction APIs ---
    path('<int:session_id>/api/interact/', views.ai_interaction_api, name='ai_interaction_api'),
    path('<int:interview_id>/api/interact-simple/', views.interact_with_ai, name='interact_with_ai'),  # New simplified endpoint
    path('<int:session_id>/api/hints/', views.get_interview_hints_api, name='get_interview_hints_api'),
    path('<int:session_id>/api/practice-question/', views.practice_question_api, name='practice_question_api'),
    
    path('delete_session/<int:session_id>/', views.delete_session, name='delete_session'),
    path('clear_all_sessions/', views.clear_all_sessions, name='clear_all_sessions'),

    
    # --- Resume Processing ---
    path('api/parse-resume/', views.parse_resume_api, name='parse_resume_api'),
    
    # --- Interview History and Analytics ---
    path('my-interviews/', views.my_mock_interviews, name='my_mock_interviews'),
    path('analytics/', views.interview_analytics, name='interview_analytics'),  # New analytics endpoint
    
    # --- Tutor/Admin Paths ---
    path('tutor/reviews/', views.tutor_interview_review_list, name='tutor_interview_review_list'),
    path('tutor/reviews/<int:session_id>/', views.tutor_review_interview_detail, name='tutor_review_interview_detail'),
    
    # --- System Health and Monitoring ---
    path('api/health/', views.ai_health_check, name='ai_health_check'),  # New health check endpoint
    # path('api/test-tts/', views.test_tts_api, name='test_tts_api'),  # Temporary TTS debugging endpoint
]

# API versioning patterns (future use)
# These should be used with a separate URL namespace when needed
v1_api_patterns = [
    # Core interview interaction
    path('api/v1/interview/<int:session_id>/interact/', views.ai_interaction_api, name='ai_interaction_api_v1'),
    path('api/v1/interview/<int:interview_id>/interact-simple/', views.interact_with_ai, name='interact_with_ai_v1'),
    
    # Enhanced features
    path('api/v1/interview/<int:session_id>/hints/', views.get_interview_hints_api, name='get_interview_hints_api_v1'),
    path('api/v1/interview/<int:session_id>/practice-question/', views.practice_question_api, name='practice_question_api_v1'),
    
    # Resume processing
    path('api/v1/resume/parse/', views.parse_resume_api, name='parse_resume_api_v1'),
    
    # Analytics and monitoring
    path('api/v1/analytics/', views.interview_analytics, name='interview_analytics_v1'),
    path('api/v1/health/', views.ai_health_check, name='ai_health_check_v1'),
    
    # Interview management
    path('api/v1/interview/start/', views.start_mock_interview, name='start_mock_interview_v1'),
]

# Development and testing patterns
# Uncomment these for development/testing purposes
debug_patterns = [
    # Direct AI testing endpoints
    # path('debug/ai-test/', views.debug_ai_test, name='debug_ai_test'),
    # path('debug/tts-test/', views.debug_tts_test, name='debug_tts_test'),
    # path('debug/resume-test/', views.debug_resume_test, name='debug_resume_test'),
]

# Admin-only patterns for system management
admin_patterns = [
    # System monitoring
    path('admin/system-status/', views.ai_health_check, name='admin_system_status'),
    
    # Bulk operations (if needed in future)
    # path('admin/bulk-review/', views.admin_bulk_review, name='admin_bulk_review'),
    # path('admin/export-data/', views.admin_export_data, name='admin_export_data'),
]

# Optional: Include admin patterns if user wants them active
# urlpatterns += admin_patterns

# Uncomment and modify when ready to implement API versioning
# Note: You'll need to handle namespace conflicts when enabling this
# urlpatterns += v1_api_patterns

# For development, uncomment to enable debug endpoints
# urlpatterns += debug_patterns