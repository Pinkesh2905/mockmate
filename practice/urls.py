from django.urls import path
from . import views

app_name = "practice"

urlpatterns = [
    # Main student views
    path('', views.problem_list, name='problem_list'),
    path('dashboard/', views.user_dashboard, name='user_dashboard'),
    path('profile/<str:username>/', views.user_profile, name='user_profile'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('my-badges/', views.my_badges, name='my_badges'),
    
    # Problem views
    path('problem/<slug:slug>/', views.problem_detail, name='problem_detail'),
    path('problem/<slug:slug>/run/', views.run_code, name='run_code'),
    path('problem/<slug:slug>/submit/', views.submit_solution, name='submit_solution'),
    path('problem/<slug:slug>/submissions/', views.my_submissions, name='my_submissions'),
    path('problem/<slug:slug>/run-samples/', views.run_code_against_samples, name='run_samples'),
    path('problem/<slug:slug>/template/<str:language>/', views.get_language_template, name='get_template'),
    path('problem/<slug:slug>/hints/', views.get_problem_hints, name='get_hints'),
    
    # Discussion views
    path('problem/<slug:slug>/discussions/', views.problem_discussions, name='problem_discussions'),
    path('problem/<slug:slug>/discussions/create/', views.create_discussion, name='create_discussion'),
    path('discussion/<int:discussion_id>/vote/', views.vote_discussion, name='vote_discussion'),
    
    # Video solutions
    path('problem/<slug:slug>/add-video-solution/', views.add_video_solution, name='add_video_solution'),
    
    # Tutor/Staff Paths
    path('tutor/dashboard/', views.tutor_dashboard, name='tutor_dashboard'),
    path('tutor/problems/add/', views.problem_create_edit, name='problem_add'),
    path('tutor/problems/edit/<slug:slug>/', views.problem_create_edit, name='problem_edit'),
    path('tutor/bulk-upload/', views.bulk_problem_upload, name='bulk_problem_upload'),
    
    # Admin Paths
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/tutors/<int:user_id>/approve/', views.admin_approve_tutor, name='admin_approve_tutor'),
    path('admin/problems/<slug:problem_slug>/<str:action>/', views.admin_problem_approval, name='admin_problem_approval'),
    
    path('submission/<uuid:submission_id>/', views.get_submission_details, name='get_submission_details'),
]