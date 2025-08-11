from django.urls import path
from . import views

app_name = 'courses'

urlpatterns = [
    # 📚 Course browsing (public) - This is the default view for the courses app
    path('', views.course_list, name='list'),
    path('<int:id>/', views.course_detail, name='detail'),
    
    # 🎓 Enrollment (requires login)
    path('<int:id>/enroll/', views.enroll_in_course, name='enroll'),
    
    # 📖 Lesson viewing
    path('<int:course_id>/lesson/<int:lesson_id>/', views.lesson_detail, name='lesson_detail'),
    
    # 📋 User's enrolled courses
    path('my-courses/', views.my_courses, name='my_courses'),
    
    # 🔄 AJAX endpoints
    path('lesson/<int:lesson_id>/watch/', views.mark_lesson_watched, name='mark_watched'),

    # 👨‍🏫 Tutor Dashboard/Course Management
    path('tutor-dashboard/', views.tutor_course_list, name='tutor_course_list'), # Tutor's course list
    path('tutor-dashboard/create/', views.course_create, name='course_create'), # Create new course
    path('tutor-dashboard/edit/<int:pk>/', views.course_edit, name='course_edit'), # Edit existing course
    path('tutor-dashboard/delete/<int:pk>/', views.course_delete, name='course_delete'), # Delete course
]
