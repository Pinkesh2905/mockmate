from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse

from .models import (
    AptitudeCategory,
    AptitudeTopic,
    AptitudeProblem,
    AptitudeSubmission,
    PracticeSet
)


def aptitude_dashboard(request):
    """
    Dashboard showing all categories and progress if user is logged in.
    """
    categories = AptitudeCategory.objects.all()

    user_progress = {}
    if request.user.is_authenticated:
        total_attempted = AptitudeSubmission.objects.filter(user=request.user).count()
        total_correct = AptitudeSubmission.objects.filter(user=request.user, is_correct=True).count()
        user_progress = {
            "attempted": total_attempted,
            "correct": total_correct,
            "accuracy": round((total_correct / total_attempted) * 100, 2) if total_attempted else 0
        }

    return render(request, "aptitude/dashboard.html", {
        "categories": categories,
        "user_progress": user_progress
    })


def topic_list(request, category_id):
    """
    Show topics under a category.
    """
    category = get_object_or_404(AptitudeCategory, id=category_id)
    topics = category.topics.all()
    return render(request, "aptitude/topic_list.html", {
        "category": category,
        "topics": topics
    })


def problem_list(request, topic_id):
    """
    Show all problems under a topic.
    """
    topic = get_object_or_404(AptitudeTopic, id=topic_id)
    problems = topic.problems.all()
    return render(request, "aptitude/problem_list.html", {
        "topic": topic,
        "problems": problems
    })


@login_required
def problem_detail(request, problem_id):
    """
    Show a single problem and allow submission.
    """
    problem = get_object_or_404(AptitudeProblem, id=problem_id)
    user_submission = None

    if request.method == "POST":
        selected_option = request.POST.get("option")
        if selected_option in ["A", "B", "C", "D"]:
            submission = AptitudeSubmission.objects.create(
                user=request.user,
                problem=problem,
                selected_option=selected_option
            )
            messages.success(request, "Your answer has been submitted!")
            return redirect("aptitude:problem_detail", problem_id=problem.id)
        else:
            messages.error(request, "Invalid option selected.")

    if request.user.is_authenticated:
        user_submission = AptitudeSubmission.objects.filter(user=request.user, problem=problem).last()

    return render(request, "aptitude/problem_detail.html", {
        "problem": problem,
        "user_submission": user_submission
    })


@login_required
def practice_set_detail(request, set_id):
    """
    Show problems inside a practice set and handle submissions.
    """
    practice_set = get_object_or_404(PracticeSet, id=set_id)
    problems = practice_set.problems.all()

    if request.method == "POST":
        for problem in problems:
            selected_option = request.POST.get(f"problem_{problem.id}")
            if selected_option in ["A", "B", "C", "D"]:
                AptitudeSubmission.objects.create(
                    user=request.user,
                    problem=problem,
                    selected_option=selected_option
                )
        messages.success(request, "Your answers have been submitted!")
        return redirect("aptitude:practice_set_result", set_id=practice_set.id)

    return render(request, "aptitude/practice_set.html", {
        "practice_set": practice_set,
        "problems": problems
    })


@login_required
def practice_set_result(request, set_id):
    """
    Show result after solving a practice set.
    """
    practice_set = get_object_or_404(PracticeSet, id=set_id)
    problems = practice_set.problems.all()

    user_submissions = AptitudeSubmission.objects.filter(
        user=request.user,
        problem__in=problems
    )

    total = problems.count()
    attempted = user_submissions.count()
    correct = user_submissions.filter(is_correct=True).count()

    result_data = {
        "total": total,
        "attempted": attempted,
        "correct": correct,
        "accuracy": round((correct / attempted) * 100, 2) if attempted else 0
    }

    return render(request, "aptitude/practice_set_result.html", {
        "practice_set": practice_set,
        "result_data": result_data,
        "submissions": user_submissions
    })


@login_required
def user_progress(request):
    """
    Show detailed progress for the logged-in user.
    """
    submissions = AptitudeSubmission.objects.filter(user=request.user)
    categories = AptitudeCategory.objects.all()

    category_stats = []
    for category in categories:
        problems = AptitudeProblem.objects.filter(topic__category=category)
        total = problems.count()
        attempted = submissions.filter(problem__in=problems).count()
        correct = submissions.filter(problem__in=problems, is_correct=True).count()
        accuracy = round((correct / attempted) * 100, 2) if attempted else 0

        category_stats.append({
            "category": category,
            "total": total,
            "attempted": attempted,
            "correct": correct,
            "accuracy": accuracy
        })

    return render(request, "aptitude/user_progress.html", {
        "category_stats": category_stats
    })
