from django.urls import path
from . import views

app_name = "quizzes"

urlpatterns = [
    # Public/Student Facing Paths
    path('', views.quiz_list, name='quiz_list'),
    path('<slug:slug>/', views.quiz_detail, name='quiz_detail'),
    path('<slug:slug>/take/', views.take_quiz, name='take_quiz'),
    path('<slug:slug>/result/<int:attempt_id>/', views.quiz_result, name='quiz_result'),

    # Tutor/Staff Paths
    path('tutor/my-quizzes/', views.tutor_quiz_list, name='tutor_quiz_list'),
    path('tutor/quizzes/add/', views.quiz_create_edit, name='quiz_add'),
    path('tutor/quizzes/edit/<slug:slug>/', views.quiz_create_edit, name='quiz_edit'),

    # Admin Paths (for approval)
    path('admin_panel/quizzes/<slug:quiz_slug>/<str:action>/', views.admin_quiz_approval, name='admin_quiz_approval'),
]
