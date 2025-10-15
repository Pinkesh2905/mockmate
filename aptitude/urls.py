from django.urls import path
from . import views

app_name = "aptitude"

urlpatterns = [
    # Dashboard
    path("", views.aptitude_dashboard, name="dashboard"),

    # Category -> Topics
    path("category/<int:category_id>/", views.topic_list, name="topic_list"),

    # Topic -> Problems
    path("topic/<int:topic_id>/", views.problem_list, name="problem_list"),

    # Problem detail (single problem attempt)
    path("problem/<int:problem_id>/", views.problem_detail, name="problem_detail"),

    # Practice set detail + submission
    path("practice-set/<int:set_id>/", views.practice_set_detail, name="practice_set_detail"),

    # Practice set result
    path("practice-set/<int:set_id>/result/", views.practice_set_result, name="practice_set_result"),

    # User progress page
    path("progress/", views.user_progress, name="user_progress"),
]
