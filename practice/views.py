from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.contrib import messages
from django.urls import reverse
from django.template.defaultfilters import slugify

from .models import PracticeProblem, PracticeSubmission, TestCase
from users.models import UserProfile
from articles.models import Article
from .forms import ProblemForm

import requests
from django.conf import settings
import json

JDOODLE_CLIENT_ID = settings.JDOODLE_CLIENT_ID
JDOODLE_CLIENT_SECRET = settings.JDOODLE_CLIENT_SECRET
JDOODLE_API_URL = "https://api.jdoodle.com/v1/execute"

# --- Role Checks (fixed to use user.profile) ---
def is_student(user):
    return user.is_authenticated and hasattr(user, 'profile') and user.profile.role == 'STUDENT'

def is_tutor(user):
    return user.is_authenticated and hasattr(user, 'profile') and user.profile.role == 'TUTOR' and user.profile.is_approved_tutor

def is_admin(user):
    return user.is_authenticated and user.is_superuser

# --- Student Views ---
@login_required(login_url='login')
@user_passes_test(is_student, login_url='login')
def problem_list(request):
    problems = PracticeProblem.objects.filter(status='PUBLISHED').order_by('-created_at')
    return render(request, "practice/problem_list.html", {"problems": problems})

@login_required(login_url='login')
@user_passes_test(is_student, login_url='login')
def problem_detail(request, slug):
    problem = get_object_or_404(PracticeProblem, slug=slug, status='PUBLISHED')
    sample_test_cases = problem.test_cases.filter(is_sample=True).order_by('id')
    language = request.GET.get("language", "python3")
    if language == "python3":
        starter = problem.template_python or "# Write your Python solution here"
    elif language == "cpp":
        starter = problem.template_cpp or "// Write your C++ solution here"
    elif language == "java":
        starter = problem.template_java or "// Write your Java solution here"
    else:
        starter = "# No starter template found"
    return render(request, "practice/problem_detail.html", {
        "problem": problem,
        "starter_code": starter,
        "language": language,
        "sample_test_cases": sample_test_cases,
    })

@login_required(login_url='login')
@user_passes_test(is_student, login_url='login')
@csrf_exempt
def run_submission(request, slug):
    if request.method != "POST":
        return JsonResponse({"error": "POST request required"}, status=400)
    problem = get_object_or_404(PracticeProblem, slug=slug, status='PUBLISHED')
    user_code = request.POST.get("code")
    language = request.POST.get("language", "python3")
    input_data = request.POST.get("input", "")
    payload = {
        "clientId": JDOODLE_CLIENT_ID,
        "clientSecret": JDOODLE_CLIENT_SECRET,
        "script": user_code,
        "language": language,
        "versionIndex": "0",
        "stdin": input_data
    }
    try:
        jdoodle_response = requests.post(JDOODLE_API_URL, json=payload)
        jdoodle_data = jdoodle_response.json()
        return JsonResponse({
            "output": jdoodle_data.get("output", "No output received").strip(),
            "cpuTime": jdoodle_data.get("cpuTime", ""),
            "memory": jdoodle_data.get("memory", ""),
            "statusCode": jdoodle_data.get("statusCode", ""),
            "error": jdoodle_data.get("error", "")
        })
    except requests.exceptions.RequestException as e:
        return JsonResponse({"error": f"Network or JDoodle API error: {str(e)}"}, status=500)
    except Exception as e:
        return JsonResponse({"error": f"An unexpected error occurred: {str(e)}"}, status=500)

@login_required(login_url='login')
@user_passes_test(is_student, login_url='login')
@csrf_exempt
def submit_solution(request, slug):
    if request.method != "POST":
        return JsonResponse({"error": "POST request required"}, status=400)
    problem = get_object_or_404(PracticeProblem, slug=slug, status='PUBLISHED')
    user_code = request.POST.get("code")
    language = request.POST.get("language", "python3")
    all_test_cases = problem.test_cases.all().order_by('id')
    submission_test_results = []
    overall_status = 'PENDING'
    all_tests_passed = True
    total_cpu_time = 0.0
    max_memory = 0.0
    submission = PracticeSubmission.objects.create(
        user=request.user,
        problem=problem,
        code=user_code,
        language=language,
        status='PENDING',
        raw_output="Processing...",
        test_results=[]
    )
    try:
        for test_case in all_test_cases:
            payload = {
                "clientId": JDOODLE_CLIENT_ID,
                "clientSecret": JDOODLE_CLIENT_SECRET,
                "script": user_code,
                "language": language,
                "versionIndex": "0",
                "stdin": test_case.input
            }
            jdoodle_response = requests.post(JDOODLE_API_URL, json=payload)
            jdoodle_data = jdoodle_response.json()
            result = {
                "test_case_id": test_case.id,
                "input": test_case.input if test_case.is_sample else "Hidden",
                "expected_output": test_case.expected_output if test_case.is_sample else "Hidden",
                "actual_output": jdoodle_data.get("output", "No output").strip(),
                "cpuTime": jdoodle_data.get("cpuTime", 0.0),
                "memory": jdoodle_data.get("memory", 0.0),
                "statusCode": jdoodle_data.get("statusCode", ""),
                "error": jdoodle_data.get("error", ""),
                "status": "FAIL"
            }
            try:
                total_cpu_time += float(jdoodle_data.get("cpuTime", 0.0))
                max_memory = max(max_memory, float(jdoodle_data.get("memory", 0.0)))
            except ValueError:
                pass
            if jdoodle_data.get("statusCode") == 200:
                if jdoodle_data.get("output", "").strip().replace('\r\n', '\n') == test_case.expected_output.strip().replace('\r\n', '\n'):
                    result["status"] = "PASS"
                else:
                    result["status"] = "WRONG_ANSWER"
                    all_tests_passed = False
            elif jdoodle_data.get("statusCode") == 400:
                result["status"] = "COMPILATION_ERROR"
                all_tests_passed = False
            elif "Time Limit Exceeded" in jdoodle_data.get("output", ""):
                result["status"] = "TIME_LIMIT_EXCEEDED"
                all_tests_passed = False
            elif jdoodle_data.get("error"):
                result["status"] = "RUNTIME_ERROR"
                all_tests_passed = False
            else:
                result["status"] = "UNKNOWN_ERROR"
                all_tests_passed = False
            submission_test_results.append(result)
            if result["status"] not in ["PASS", "WRONG_ANSWER"]:
                break
        if all_tests_passed and all_test_cases:
            overall_status = 'ACCEPTED'
        elif any(r["status"] == "COMPILATION_ERROR" for r in submission_test_results):
            overall_status = 'COMPILATION_ERROR'
        elif any(r["status"] == "TIME_LIMIT_EXCEEDED" for r in submission_test_results):
            overall_status = 'TIME_LIMIT_EXCEEDED'
        elif any(r["status"] == "RUNTIME_ERROR" for r in submission_test_results):
            overall_status = 'RUNTIME_ERROR'
        elif not all_tests_passed:
            overall_status = 'WRONG_ANSWER'
        elif not all_test_cases:
            overall_status = 'UNKNOWN_ERROR'
        submission.status = overall_status
        submission.test_results = submission_test_results
        submission.raw_output = json.dumps(jdoodle_data)
        submission.cpu_time = f"{total_cpu_time:.2f} sec"
        submission.memory = f"{max_memory:.2f} KB"
        submission.save()
        return JsonResponse({
            "status": overall_status,
            "test_results": submission_test_results,
            "cpuTime": submission.cpu_time,
            "memory": submission.memory,
            "redirect_url": reverse('practice:my_submissions', args=[problem.slug])
        })
    except requests.exceptions.RequestException as e:
        submission.status = 'UNKNOWN_ERROR'
        submission.raw_output = f"Network error: {str(e)}"
        submission.save()
        return JsonResponse({"error": f"Network error: {str(e)}"}, status=500)
    except Exception as e:
        submission.status = 'UNKNOWN_ERROR'
        submission.raw_output = f"Unexpected error: {str(e)}"
        submission.save()
        return JsonResponse({"error": f"Unexpected error: {str(e)}"}, status=500)

@login_required(login_url='login')
@user_passes_test(is_student, login_url='login')
def my_submissions(request, slug):
    problem = get_object_or_404(PracticeProblem, slug=slug, status='PUBLISHED')
    submissions = PracticeSubmission.objects.filter(user=request.user, problem=problem).order_by('-submission_time')
    return render(request, "practice/my_submissions.html", {
        "problem": problem,
        "submissions": submissions
    })


# --- Tutor/Staff Specific Views ---
@login_required(login_url='login') # Changed login_url to global 'login'
@user_passes_test(is_tutor, login_url='login') # Changed login_url to global 'login'
def tutor_dashboard(request):
    """
    Tutor's main dashboard to manage their content.
    """
    # Get problems created by this tutor, ordered by status and creation date
    problems = PracticeProblem.objects.filter(created_by=request.user).order_by('status', '-created_at')
    # You can add counts for courses, quizzes, articles here too
    return render(request, 'tutor/dashboard.html', {'problems': problems})


@login_required(login_url='login') # Changed login_url to global 'login'
@user_passes_test(is_tutor, login_url='login') # Changed login_url to global 'login'
def problem_create_edit(request, slug=None):
    """
    Allows tutors to create new problems or edit their existing problems.
    """
    problem = None
    if slug:
        problem = get_object_or_404(PracticeProblem, slug=slug, created_by=request.user) # Tutors can only edit their own problems

    if request.method == 'POST':
        form = ProblemForm(request.POST, instance=problem)
        formset = TestCaseFormSet(request.POST, instance=problem)

        if form.is_valid() and formset.is_valid():
            new_problem = form.save(commit=False)
            if not problem: # If creating a new problem
                new_problem.created_by = request.user
                new_problem.status = 'PENDING_APPROVAL' # Default status for new tutor problems
            new_problem.save()

            formset.instance = new_problem
            formset.save()

            messages.success(request, f'Problem "{new_problem.title}" saved successfully. It is now pending admin approval.')
            return redirect('practice:tutor_dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ProblemForm(instance=problem)
        formset = TestCaseFormSet(instance=problem)

    context = {
        'form': form,
        'formset': formset,
        'problem': problem,
        'is_new': problem is None
    }
    return render(request, 'tutor/problem_create_edit.html', context)


# --- Admin Specific Views ---
@login_required(login_url='login') # Changed login_url to global 'login'
@user_passes_test(is_admin, login_url='login') # Changed login_url to global 'login'
def admin_dashboard(request):
    """
    Admin's main dashboard to oversee the platform.
    """
    # Get unapproved tutors
    pending_tutors = UserProfile.objects.filter(role='TUTOR', is_approved_tutor=False)
    # Get problems pending approval
    pending_problems = PracticeProblem.objects.filter(status='PENDING_APPROVAL').order_by('-created_at')
    # Get articles pending approval (NEW)
    pending_articles = Article.objects.filter(status='PENDING_APPROVAL').order_by('-created_at')

    context = {
        'pending_tutors': pending_tutors,
        'pending_problems': pending_problems,
        'pending_articles': pending_articles, # Add to context
    }
    return render(request, 'admin/dashboard.html', context)


@login_required(login_url='login') # Changed login_url to global 'login'
@user_passes_test(is_admin, login_url='login') # Changed login_url to global 'login')
def admin_approve_tutor(request, user_id):
    """
    Admin action to approve a tutor account.
    """
    user_profile = get_object_or_404(UserProfile, user__id=user_id, role='TUTOR', is_approved_tutor=False)
    user_profile.is_approved_tutor = True
    user_profile.save()
    messages.success(request, f'Tutor {user_profile.user.username} has been approved.')
    return redirect('practice:admin_dashboard') # Redirect back to admin dashboard


@login_required(login_url='login') # Changed login_url to global 'login'
@user_passes_test(is_admin, login_url='login') # Changed login_url to global 'login')
def admin_problem_approval(request, problem_slug, action):
    """
    Admin action to approve, reject, or archive a problem.
    """
    problem = get_object_or_404(PracticeProblem, slug=problem_slug)

    if action == 'publish':
        problem.status = 'PUBLISHED'
        messages.success(request, f'Problem "{problem.title}" has been published.')
    elif action == 'reject':
        problem.status = 'DRAFT' # Or a specific 'REJECTED' status if you add one
        messages.warning(request, f'Problem "{problem.title}" has been moved back to draft status.')
    elif action == 'archive':
        problem.status = 'ARCHIVED'
        messages.info(request, f'Problem "{problem.title}" has been archived.')
    else:
        messages.error(request, 'Invalid action.')
        return redirect('practice:admin_dashboard')

    problem.save()
    return redirect('practice:admin_dashboard')
