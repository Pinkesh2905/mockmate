from django.urls import path
from . import views

app_name = "mock_interview"

# Main URL patterns organized by functionality
urlpatterns = [
    # --- Student Interview Flow ---
    path('', views.interview_setup, name='interview_setup'),
    path('start/', views.start_mock_interview, name='start_mock_interview'),
    path('<int:session_id>/start/', views.main_interview, name='main_interview'),
    path('<int:session_id>/review/', views.review_interview, name='review_interview'),
    
    # --- Core Interview Interaction APIs ---
    path('<int:session_id>/ai_interaction/', views.ai_interaction_api, name='ai_interaction_api'),
    path('<int:interview_id>/interact/', views.interact_with_ai, name='interact_with_ai'),  # Legacy endpoint
    
    # --- Enhanced Interview Support APIs ---
    path('<int:session_id>/hints/', views.get_interview_hints_api, name='get_interview_hints_api'),
    path('<int:session_id>/practice-questions/', views.practice_question_api, name='practice_question_api'),
    
    # --- Session Management ---
    path('sessions/<int:session_id>/delete/', views.delete_session, name='delete_session'),
    path('sessions/clear-all/', views.clear_all_sessions, name='clear_all_sessions'),
    
    # --- Interview History and Analytics ---
    path('my-interviews/', views.my_mock_interviews, name='my_mock_interviews'),
    
    # --- System Health and Monitoring ---
    path('api/health/', views.ai_health_check, name='ai_health_check'),
]

# RESTful API endpoints for better API design
api_patterns = [
    # Session-based API endpoints
    path('api/sessions/<int:session_id>/interact/', views.ai_interaction_api, name='api_session_interact'),
    path('api/sessions/<int:session_id>/hints/', views.get_interview_hints_api, name='api_session_hints'),
    path('api/sessions/<int:session_id>/practice/', views.practice_question_api, name='api_session_practice'),
    
    # Legacy compatibility
    path('api/interviews/<int:interview_id>/chat/', views.interact_with_ai, name='api_interview_chat'),
    
    # System endpoints
    path('api/system/health/', views.ai_health_check, name='api_system_health'),
    path('api/system/status/', views.ai_health_check, name='api_system_status'),  # Alias
]

# Mobile-optimized API endpoints
mobile_patterns = [
    path('mobile/setup/', views.interview_setup, name='mobile_setup'),
    path('mobile/sessions/<int:session_id>/start/', views.main_interview, name='mobile_interview'),
    path('mobile/sessions/<int:session_id>/interact/', views.ai_interaction_api, name='mobile_interact'),
    path('mobile/sessions/<int:session_id>/complete/', views.review_interview, name='mobile_review'),
    path('mobile/sessions/', views.my_mock_interviews, name='mobile_sessions'),
    path('mobile/health/', views.ai_health_check, name='mobile_health'),
]

# Versioned API endpoints for future compatibility
v1_patterns = [
    path('api/v1/sessions/<int:session_id>/interact/', views.ai_interaction_api, name='v1_interact'),
    path('api/v1/sessions/<int:session_id>/hints/', views.get_interview_hints_api, name='v1_hints'),
    path('api/v1/sessions/<int:session_id>/practice/', views.practice_question_api, name='v1_practice'),
    path('api/v1/health/', views.ai_health_check, name='v1_health'),
    path('api/v1/user/sessions/', views.my_mock_interviews, name='v1_user_sessions'),
]

# Include additional URL patterns based on configuration
# Uncomment the ones you need:

# For enhanced API support:
# urlpatterns += api_patterns

# For mobile app integration:
# urlpatterns += mobile_patterns  

# For API versioning:
# urlpatterns += v1_patterns

# Backward compatibility aliases - keeping old URL patterns working
compatibility_patterns = [
    # Old naming conventions that might be used elsewhere
    path('delete_session/<int:session_id>/', views.delete_session, name='delete_session_legacy'),
    path('clear_all_sessions/', views.clear_all_sessions, name='clear_all_sessions_legacy'),
    path('<int:session_id>/practice-question/', views.practice_question_api, name='practice_question_legacy'),
]

# Add compatibility patterns to maintain backward compatibility
urlpatterns += compatibility_patterns

# URL pattern validation for critical endpoints
REQUIRED_ENDPOINTS = [
    'interview_setup',
    'main_interview',
    'ai_interaction_api', 
    'review_interview',
    'my_mock_interviews',
    'get_interview_hints_api',
    'practice_question_api',
    'ai_health_check',
    'delete_session',
    'clear_all_sessions'
]

# Future endpoints that may be implemented
FUTURE_ENDPOINTS = {
    # Resume processing
    'parse_resume_api': 'api/resume/parse/',
    'resume_analysis_api': 'api/resume/analyze/',
    
    # Advanced analytics  
    'interview_analytics': 'analytics/',
    'user_progress_api': 'api/user/progress/',
    'performance_trends_api': 'api/user/trends/',
    
    # Tutor/Admin system
    'tutor_dashboard': 'tutor/dashboard/',
    'tutor_review_list': 'tutor/reviews/',
    'tutor_review_detail': 'tutor/reviews/<int:session_id>/',
    'admin_interview_overview': 'admin/interviews/',
    
    # Configuration and settings
    'tts_config_api': 'api/settings/tts/',
    'ai_config_api': 'api/settings/ai/',
    'user_preferences_api': 'api/user/preferences/',
    
    # Export and reporting
    'export_interview_api': 'api/sessions/<int:session_id>/export/',
    'generate_report_api': 'api/sessions/<int:session_id>/report/',
    'bulk_export_api': 'api/user/export/',
    
    # Real-time features
    'interview_websocket': 'ws/interview/<int:session_id>/',
    'live_feedback_api': 'api/sessions/<int:session_id>/live-feedback/',
    
    # Integration endpoints
    'webhook_interview_complete': 'webhooks/interview/complete/',
    'external_calendar_api': 'api/calendar/schedule/',
}

"""
MockMate Interview URLs Documentation
====================================

Core Student Flow:
-----------------
- /mock_interview/ - Interview setup form with resume upload
- /mock_interview/<id>/start/ - Main interview interface with AI Sarah
- /mock_interview/<id>/review/ - Review completed interview with feedback

Primary API Endpoints:
---------------------
- /mock_interview/<id>/ai_interaction/ - Main AI interaction endpoint (POST)
  * Handles all interview conversation flow
  * Supports TTS audio generation
  * Manages interview completion logic

- /mock_interview/<id>/hints/ - Get contextual interview hints (POST)
  * AI-generated strategic advice based on current question
  * Fallback to predefined hints by interview stage
  * Stage-aware recommendations

- /mock_interview/<id>/practice-questions/ - Generate practice questions (POST)
  * AI-generated questions specific to role and skills
  * Categorized by difficulty and question type
  * Includes answering tips and focus areas

Session Management:
------------------
- /mock_interview/my-interviews/ - User's interview history with metrics
- /mock_interview/sessions/<id>/delete/ - Delete specific interview session
- /mock_interview/sessions/clear-all/ - Clear all user sessions (POST)

System Monitoring:
-----------------
- /mock_interview/api/health/ - Comprehensive system health check
  * AI provider status (Gemini/OpenAI)
  * TTS service functionality (edge-tts/gTTS)
  * API key validation
  * Service recommendations

Legacy Compatibility:
--------------------
- /mock_interview/<id>/interact/ - Simplified AI interaction (legacy)
- /mock_interview/delete_session/<id>/ - Old delete endpoint
- /mock_interview/clear_all_sessions/ - Old clear endpoint

Authentication & Permissions:
----------------------------
- All main endpoints require login and student role
- API endpoints use CSRF protection
- Session ownership validation on all operations

HTTP Methods:
------------
- GET: Setup pages, review pages, session lists
- POST: AI interactions, session management, API calls
- DELETE: Session deletion (where applicable)

Response Formats:
----------------
- HTML: Main interview interface pages
- JSON: All API endpoints with standardized structure
- Audio: Generated TTS files served via media URLs

Error Handling:
--------------
- Graceful degradation when AI services fail
- Fallback responses for all critical functions
- Comprehensive logging for debugging
- User-friendly error messages

Future Expansion:
----------------
The URL structure supports future features including:
- Resume processing APIs
- Advanced analytics dashboards  
- Tutor review systems
- Mobile app endpoints
- Webhook integrations
- Real-time features via WebSockets

URL Pattern Guidelines:
----------------------
1. Session-based URLs use session_id for consistency
2. API endpoints follow RESTful conventions
3. Versioning support through v1/ prefix
4. Mobile endpoints use mobile/ prefix
5. Admin/tutor endpoints use role-based prefixes
6. Health/monitoring use api/system/ prefix

All endpoints are designed for scalability and maintain backward compatibility
with existing frontend implementations.
"""