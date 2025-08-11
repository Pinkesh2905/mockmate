from django.urls import path
from . import views

app_name = "practice"

urlpatterns = [
    path('', views.problem_list, name='problem_list'),
    path('<slug:slug>/', views.problem_detail, name='problem_detail'),
    path('<slug:slug>/run/', views.run_submission, name='run_submission'),
    path('<slug:slug>/submit/', views.submit_solution, name='submit_solution'), # Added submit_solution
    path('<slug:slug>/submissions/', views.my_submissions, name='my_submissions'),
    
    # Tutor/Staff Paths
    path('tutor-dashboard/', views.tutor_dashboard, name='tutor_dashboard'),
    path('tutor-dashboard/problems/add/', views.problem_create_edit, name='problem_add'),
    path('tutor-dashboard/problems/edit/<slug:slug>/', views.problem_create_edit, name='problem_edit'),

    # Admin Paths (for approval)
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-dashboard/tutors/<int:user_id>/approve/', views.admin_approve_tutor, name='admin_approve_tutor'),
    path('admin-dashboard/problems/<slug:problem_slug>/<str:action>/', views.admin_problem_approval, name='admin_problem_approval'),
    
    # REMOVED: Registration paths (e.g., 'register/student/', 'register/tutor/', 'tutor_approval/')
    # These functionalities are now handled by the 'users' app or the admin interface.
    # path('register/student/', views.student_register, name='student_register'), # REMOVE THIS
    # path('register/tutor/', views.tutor_register, name='tutor_register'),     # REMOVE THIS
    # path('tutor-approval/', views.tutor_approval_list, name='tutor_approval_list'), # REMOVE THIS
    # path('tutor-approval/<int:pk>/', views.tutor_approve_deny, name='tutor_approve_deny'), # REMOVE THIS
]

