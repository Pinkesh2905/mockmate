from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse, HttpResponseForbidden, Http404
from django.contrib import messages
from django.urls import reverse
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg, Max, F
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from django.conf import settings

from .models import (
    PracticeProblem, PracticeSubmission, TestCase, 
    UserProblemStats, UserStats, Category, Tag, Discussion, DiscussionVote,
    Badge, UserBadge, ProblemVideoSolution, PROGRAMMING_LANGUAGES
)
from users.models import UserProfile
from .forms import (
    ProblemForm, TestCaseFormSet, ProblemFilterForm,
    DiscussionForm, CustomTestForm, ProblemVideoSolutionForm,
    TestCaseUploadForm, BulkProblemUploadForm
)
from .services import CodeExecutionService, TestCaseService, BadgeService
from .utils import get_default_code_template

import csv
import io
import json
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)

# --- Role Checks ---
def is_student(user):
    return user.is_authenticated and hasattr(user, 'profile') and user.profile.role == 'STUDENT'

def is_tutor(user):
    return user.is_authenticated and hasattr(user, 'profile') and user.profile.role == 'TUTOR' and user.profile.is_approved_tutor

def is_admin(user):
    return user.is_authenticated and user.is_superuser

def get_or_create_user_stats(user):
    """Get or create user statistics"""
    user_stats, created = UserStats.objects.get_or_create(user=user)
    return user_stats

# --- Main Views ---
@login_required(login_url='login')
@user_passes_test(is_student, login_url='login')
def problem_list(request):
    """Enhanced problem list with filtering and search"""
    problems = PracticeProblem.objects.filter(
        status='PUBLISHED'
    ).select_related('category', 'created_by').prefetch_related('tags')
    
    # Get user stats for problem status
    user_stats_dict = {}
    if request.user.is_authenticated:
        user_problem_stats = UserProblemStats.objects.filter(
            user=request.user
        ).select_related('problem')
        user_stats_dict = {stat.problem_id: stat for stat in user_problem_stats}
    
    # Initialize filter form
    filter_form = ProblemFilterForm(request.GET)
    
    # Apply filters
    if filter_form.is_valid():
        # Difficulty filter
        if filter_form.cleaned_data['difficulty']:
            problems = problems.filter(difficulty=filter_form.cleaned_data['difficulty'])
        
        # Category filter
        if filter_form.cleaned_data['category']:
            problems = problems.filter(category=filter_form.cleaned_data['category'])
        
        # Tags filter
        if filter_form.cleaned_data['tags']:
            problems = problems.filter(tags__in=filter_form.cleaned_data['tags']).distinct()
        
        # Search filter
        if filter_form.cleaned_data['search']:
            search_term = filter_form.cleaned_data['search']
            problems = problems.filter(
                Q(title__icontains=search_term) |
                Q(statement__icontains=search_term) |
                Q(companies__icontains=search_term)
            )
        
        # Company filter
        if filter_form.cleaned_data['company']:
            problems = problems.filter(companies__icontains=filter_form.cleaned_data['company'])
        
        # Status filter
        if filter_form.cleaned_data['status']:
            status = filter_form.cleaned_data['status']
            if status == 'solved':
                solved_problem_ids = [stat.problem_id for stat in user_stats_dict.values() if stat.is_solved]
                problems = problems.filter(id__in=solved_problem_ids)
            elif status == 'attempted':
                attempted_problem_ids = [stat.problem_id for stat in user_stats_dict.values() if stat.is_attempted and not stat.is_solved]
                problems = problems.filter(id__in=attempted_problem_ids)
            elif status == 'not_attempted':
                attempted_problem_ids = [stat.problem_id for stat in user_stats_dict.values()]
                problems = problems.exclude(id__in=attempted_problem_ids)
    
    # Sorting
    sort_by = request.GET.get('sort', 'newest')
    if sort_by == 'difficulty':
        problems = problems.order_by('difficulty', 'title')
    elif sort_by == 'acceptance':
        problems = problems.order_by('-acceptance_rate', 'title')
    elif sort_by == 'title':
        problems = problems.order_by('title')
    else:  # newest
        problems = problems.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(problems, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Add problem status to each problem
    for problem in page_obj.object_list:
        problem.user_status = user_stats_dict.get(problem.id)
    
    # Get statistics for sidebar
    stats = {
        'total_problems': PracticeProblem.objects.filter(status='PUBLISHED').count(),
        'easy_problems': PracticeProblem.objects.filter(status='PUBLISHED', difficulty='EASY').count(),
        'medium_problems': PracticeProblem.objects.filter(status='PUBLISHED', difficulty='MEDIUM').count(),
        'hard_problems': PracticeProblem.objects.filter(status='PUBLISHED', difficulty='HARD').count(),
        'categories': Category.objects.annotate(problem_count=Count('problems')).filter(problem_count__gt=0),
        'popular_tags': Tag.objects.annotate(problem_count=Count('problems')).filter(problem_count__gt=0).order_by('-problem_count')[:10]
    }
    
    user_stats = get_or_create_user_stats(request.user)
    
    context = {
        'page_obj': page_obj,
        'filter_form': filter_form,
        'stats': stats,
        'user_stats': user_stats,
        'sort_by': sort_by
    }
    
    return render(request, "practice/problem_list.html", context)

@login_required(login_url='login')
@user_passes_test(is_student, login_url='login')
def problem_detail(request, slug):
    """Enhanced problem detail view"""
    try:
        problem = get_object_or_404(PracticeProblem, slug=slug, status='PUBLISHED')
    except Http404:
        messages.error(request, 'Problem not found or not available.')
        return redirect('practice:problem_list')
    
    # Get or create user problem stats
    user_problem_stats, created = UserProblemStats.objects.get_or_create(
        user=request.user,
        problem=problem
    )
    
    # Mark as attempted if not already
    if not user_problem_stats.is_attempted:
        user_problem_stats.is_attempted = True
        user_problem_stats.save()
    
    # Get sample test cases
    sample_test_cases = problem.test_cases.filter(is_sample=True).order_by('order', 'created_at')
    
    # Get code template for selected language
    language = request.GET.get("language", "python3")
    starter_code = get_default_code_template(language, problem.title)
    
    # Get user's recent submissions - FIXED: submission_time -> submitted_at
    recent_submissions = PracticeSubmission.objects.filter(
        user=request.user,
        problem=problem
    ).order_by('-submitted_at')[:5]
    
    # Get discussions count
    discussions_count = problem.discussions.count()
    
    # Get similar problems
    similar_problems = PracticeProblem.objects.filter(
        Q(category=problem.category) | Q(tags__in=problem.tags.all())
    ).exclude(id=problem.id).filter(status='PUBLISHED').distinct()[:5]

    # Get problem video solutions
    video_solutions = problem.video_solutions.all().order_by('-is_premium', '-created_at')
    
    # Get available languages
    supported_codes = {'python3', 'cpp17', 'java', 'javascript', 'csharp'}
    available_languages = [lang for lang in PROGRAMMING_LANGUAGES if lang[0] in supported_codes]
    
    editor_config = {
        'language': language,
        'starter_code': starter_code,
        'monaco_language_map': {
            'python3': 'python',
            'cpp17': 'cpp',
            'java': 'java',
            'javascript': 'javascript',
            'csharp': 'csharp',
        }
    }
    
    context = {
        "problem": problem,
        "starter_code": starter_code,
        "language": language,
        "sample_test_cases": sample_test_cases,
        "user_problem_stats": user_problem_stats,
        "recent_submissions": recent_submissions,
        "discussions_count": discussions_count,
        "similar_problems": similar_problems,
        "available_languages": available_languages,
        "video_solutions": video_solutions,
        "editor_config_json": json.dumps(editor_config),
    }
    
    return render(request, "practice/problem_detail.html", context)

@login_required(login_url='login')
@user_passes_test(is_student, login_url='login')
@csrf_exempt
@require_http_methods(["POST"])
def run_code_against_samples(request, slug):
    """Run code against sample test cases only"""
    problem = get_object_or_404(PracticeProblem, slug=slug, status='PUBLISHED')
    
    user_code = request.POST.get("code", "").strip()
    language = request.POST.get("language", "python3")
    
    if not user_code:
        return JsonResponse({"error": "Code cannot be empty"}, status=400)
    
    try:
        # Get sample test cases only
        sample_test_cases = problem.test_cases.filter(is_sample=True).order_by('order', 'created_at')
        
        if not sample_test_cases.exists():
            return JsonResponse({"error": "No sample test cases available"}, status=400)
        
        # Use the execution service
        execution_service = CodeExecutionService()
        results = execution_service.run_against_test_cases(user_code, language, sample_test_cases, problem.time_limit)
        
        # Calculate summary
        passed_tests = sum(1 for r in results if r["passed"])
        total_tests = len(results)
        total_time = sum(float(r.get("execution_time", 0)) for r in results)
        
        return JsonResponse({
            "results": results,
            "summary": {
                "passed": passed_tests,
                "total": total_tests,
                "all_passed": passed_tests == total_tests,
                "total_time": f"{total_time:.3f}s",
            }
        })
        
    except Exception as e:
        logger.error(f"Error running code against samples: {str(e)}")
        return JsonResponse({"error": f"Execution error: {str(e)}"}, status=500)

@login_required(login_url='login')
@require_http_methods(["POST"])
@transaction.atomic
def submit_solution(request, slug):
    """
    Handles the submission of a solution for a problem.
    This view now runs a full evaluation against all test cases.
    """
    try:
        data = json.loads(request.body)
        code = data.get('code')
        language = data.get('language')
        
        if not code or not language:
            return JsonResponse({'error': 'Code and language are required.'}, status=400)

        problem = get_object_or_404(PracticeProblem, slug=slug, status='PUBLISHED')

        # 1. Create a submission record with 'PENDING' status
        submission = PracticeSubmission.objects.create(
            user=request.user,
            problem=problem,
            language=language,
            code=code,
            status='PENDING'
        )
        
        # 2. Call the evaluation service to run code against all test cases
        evaluation_result = CodeExecutionService.evaluate_submission(submission)
        
        # 3. Update the submission record with the final results
        submission.status = evaluation_result['status']
        submission.results = evaluation_result['results']
        submission.passed_cases = evaluation_result['passed_cases']
        submission.total_cases = evaluation_result['total_cases']
        submission.execution_time = evaluation_result.get('execution_time')
        submission.memory_used = evaluation_result.get('memory_used')
        submission.save()
        
        # 4. Update user and problem statistics based on the outcome
        TestCaseService.update_user_problem_stats(
            request.user, 
            problem, 
            submission, 
            submission.status
        )

        # 5. Return the full result to the frontend
        return JsonResponse({
            'submission_id': str(submission.id),
            'status': submission.status,
            'passed_cases': submission.passed_cases,
            'total_cases': submission.total_cases,
            'execution_time': submission.execution_time,
            'memory_used': submission.memory_used,
            'results': submission.results
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON in request body.'}, status=400)
    except Exception as e:
        logger.error(f"Error during submission for slug {slug}: {e}", exc_info=True)
        return JsonResponse({'error': 'An unexpected server error occurred.'}, status=500)

@login_required(login_url='login')
@user_passes_test(is_student, login_url='login')
@csrf_exempt
@require_http_methods(["POST"])
def run_code(request, slug):
    """Run code against custom input"""
    problem = get_object_or_404(PracticeProblem, slug=slug, status='PUBLISHED')
    
    user_code = request.POST.get("code", "").strip()
    language = request.POST.get("language", "python3")
    input_data = request.POST.get("input", "")
    
    if not user_code:
        return JsonResponse({"error": "Code cannot be empty"}, status=400)
    
    try:
        execution_service = CodeExecutionService()
        result = execution_service.run_code(language, user_code, input_data)
        return JsonResponse(result)
        
    except Exception as e:
        logger.error(f"Error running code: {str(e)}")
        return JsonResponse({"error": f"Execution error: {str(e)}"}, status=500)

@login_required(login_url='login')
@user_passes_test(is_student, login_url='login')
def my_submissions(request, slug):
    """View user's submissions for a specific problem"""
    problem = get_object_or_404(PracticeProblem, slug=slug, status='PUBLISHED')
    
    # FIXED: submission_time -> submitted_at
    submissions = PracticeSubmission.objects.filter(
        user=request.user,
        problem=problem
    ).order_by('-submitted_at')
    
    # Pagination
    paginator = Paginator(submissions, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get statistics
    stats = {
        'total_submissions': submissions.count(),
        'accepted_submissions': submissions.filter(status='ACCEPTED').count(),
        'best_runtime': submissions.filter(execution_time__isnull=False).aggregate(Min('execution_time'))['execution_time__min'] or 0,
        'average_runtime': submissions.filter(execution_time__isnull=False).aggregate(Avg('execution_time'))['execution_time__avg'] or 0,
    }
    
    context = {
        "problem": problem,
        "page_obj": page_obj,
        "stats": stats
    }
    
    return render(request, "practice/my_submissions.html", context)

@login_required(login_url='login')
@user_passes_test(is_student, login_url='login')
def user_dashboard(request):
    """User dashboard with statistics and recent activity"""
    user_stats = get_or_create_user_stats(request.user)
    
    # Get recent submissions - FIXED: submission_time -> submitted_at
    recent_submissions = PracticeSubmission.objects.filter(
        user=request.user
    ).select_related('problem').order_by('-submitted_at')[:10]
    
    # Get recently attempted problems
    recent_problems = UserProblemStats.objects.filter(
        user=request.user,
        is_attempted=True
    ).select_related('problem').order_by('-updated_at')[:5]
    
    # Get solved problems by difficulty
    solved_problems = UserProblemStats.objects.filter(
        user=request.user,
        is_solved=True
    ).select_related('problem')
    
    # Language usage statistics
    language_stats = {}
    for submission in PracticeSubmission.objects.filter(user=request.user):
        lang = submission.get_language_display()
        language_stats[lang] = language_stats.get(lang, 0) + 1
    
    # Weekly activity (submissions per day for last 7 days) - FIXED: submission_time -> submitted_at
    week_activity = {}
    for i in range(7):
        date = timezone.now().date() - timedelta(days=i)
        count = PracticeSubmission.objects.filter(
            user=request.user,
            submitted_at__date=date
        ).count()
        week_activity[date.strftime('%a')] = count
    
    context = {
        'user_stats': user_stats,
        'recent_submissions': recent_submissions,
        'recent_problems': recent_problems,
        'solved_problems': solved_problems,
        'language_stats': language_stats,
        'week_activity': week_activity,
    }
    
    return render(request, 'practice/user_dashboard.html', context)

# --- Tutor/Staff Views ---
@login_required(login_url='login')
@user_passes_test(is_tutor, login_url='login')
def tutor_dashboard(request):
    """Tutor's main dashboard to manage content"""
    problems = PracticeProblem.objects.filter(created_by=request.user).order_by('status', '-created_at')
    
    # Statistics
    stats = {
        'total_problems': problems.count(),
        'published_problems': problems.filter(status='PUBLISHED').count(),
        'pending_problems': problems.filter(status='PENDING_APPROVAL').count(),
        'draft_problems': problems.filter(status='DRAFT').count(),
    }
    
    context = {
        'problems': problems,
        'stats': stats
    }
    
    return render(request, 'tutor/dashboard.html', context)

@login_required(login_url='login')
@user_passes_test(is_tutor, login_url='login')
def problem_create_edit(request, slug=None):
    """Create or edit a problem with CSV test case upload"""
    problem = None
    if slug:
        problem = get_object_or_404(PracticeProblem, slug=slug, created_by=request.user)

    if request.method == 'POST':
        form = ProblemForm(request.POST, instance=problem)
        test_formset = TestCaseFormSet(request.POST, instance=problem)
        csv_form = TestCaseUploadForm(request.POST, request.FILES)

        # Handle CSV upload
        if 'upload_csv' in request.POST and csv_form.is_valid():
            try:
                csv_file = csv_form.cleaned_data['csv_file']
                TestCaseService.import_test_cases_from_csv(problem or form.instance, csv_file)
                messages.success(request, 'Test cases imported successfully from CSV!')
                return redirect('practice:problem_edit', slug=problem.slug if problem else form.instance.slug)
            except Exception as e:
                messages.error(request, f'Error importing CSV: {str(e)}')

        # Handle regular form submission
        if form.is_valid() and test_formset.is_valid():
            try:
                with transaction.atomic():
                    new_problem = form.save(commit=False)
                    if not problem:  # Creating new problem
                        new_problem.created_by = request.user
                        if not new_problem.is_private:
                            new_problem.status = 'PENDING_APPROVAL'
                        else:
                            new_problem.status = 'PRIVATE'
                    new_problem.save()
                    form.save_m2m()  # Save many-to-many fields like tags

                    # Save test cases
                    test_formset.instance = new_problem
                    test_formset.save()

                    messages.success(request, f'Problem "{new_problem.title}" saved successfully!')
                    return redirect('practice:tutor_dashboard')
            except Exception as e:
                messages.error(request, f'Error saving problem: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ProblemForm(instance=problem)
        test_formset = TestCaseFormSet(instance=problem)
        csv_form = TestCaseUploadForm()

    context = {
        'form': form,
        'test_formset': test_formset,
        'csv_form': csv_form,
        'problem': problem,
        'is_new': problem is None
    }
    
    return render(request, 'tutor/problem_create_edit.html', context)

@login_required(login_url='login')
@user_passes_test(is_tutor, login_url='login')
def bulk_problem_upload(request):
    """Bulk upload problems from CSV"""
    if request.method == 'POST':
        form = BulkProblemUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                csv_file = form.cleaned_data['csv_file']
                imported_count = TestCaseService.import_problems_from_csv(csv_file, request.user)
                messages.success(request, f'Successfully imported {imported_count} problems!')
                return redirect('practice:tutor_dashboard')
            except Exception as e:
                messages.error(request, f'Error importing problems: {str(e)}')
    else:
        form = BulkProblemUploadForm()
    
    context = {'form': form}
    return render(request, 'tutor/bulk_upload.html', context)

# --- Additional Views ---
@login_required(login_url='login')
@user_passes_test(is_student, login_url='login')
def problem_discussions(request, slug):
    """View discussions for a problem"""
    problem = get_object_or_404(PracticeProblem, slug=slug, status='PUBLISHED')
    
    discussions = problem.discussions.select_related('user').order_by('-is_pinned', '-created_at')
    
    # Filter by discussion type
    discussion_type = request.GET.get('type', 'all')
    if discussion_type == 'solutions':
        discussions = discussions.filter(is_solution=True)
    elif discussion_type == 'questions':
        discussions = discussions.filter(is_solution=False)
    
    # Pagination
    paginator = Paginator(discussions, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'problem': problem,
        'page_obj': page_obj,
        'discussion_type': discussion_type
    }
    
    return render(request, 'practice/discussions.html', context)

@login_required(login_url='login')
@user_passes_test(is_student, login_url='login')
def create_discussion(request, slug):
    """Create a new discussion for a problem"""
    problem = get_object_or_404(PracticeProblem, slug=slug, status='PUBLISHED')
    
    if request.method == 'POST':
        form = DiscussionForm(request.POST)
        if form.is_valid():
            discussion = form.save(commit=False)
            discussion.problem = problem
            discussion.user = request.user
            discussion.save()
            
            messages.success(request, 'Discussion created successfully!')
            return redirect('practice:problem_discussions', slug=slug)
    else:
        form = DiscussionForm()
    
    context = {
        'problem': problem,
        'form': form
    }
    
    return render(request, 'practice/create_discussion.html', context)

@login_required(login_url='login')
def user_profile(request, username):
    """User profile and statistics page"""
    try:
        user_profile = UserProfile.objects.get(user__username=username)
        user_stats = get_or_create_user_stats(user_profile.user)
        user_badges = UserBadge.objects.filter(user=user_profile.user).select_related('badge').order_by('-awarded_at')
        
        # Calculate rank based on problems solved
        better_users = UserStats.objects.filter(problems_solved__gt=user_stats.problems_solved).count()
        user_stats.rank = better_users + 1
        user_stats.save()
        
        context = {
            'user_profile': user_profile,
            'user_stats': user_stats,
            'user_badges': user_badges,
        }
        return render(request, 'practice/user_profile.html', context)
    except UserProfile.DoesNotExist:
        messages.error(request, 'User not found.')
        redirect('practice:problem_list')

@login_required(login_url='login')
def leaderboard(request):
    """Global leaderboard for users"""
    leaderboard_data = UserStats.objects.filter(
        problems_solved__gt=0
    ).select_related('user').order_by('-problems_solved', '-total_points')[:100]
    
    context = {
        'leaderboard_data': leaderboard_data,
    }
    return render(request, 'practice/leaderboard.html', context)

@login_required(login_url='login')
def my_badges(request):
    """Displays a user's earned badges"""
    user_badges = UserBadge.objects.filter(user=request.user).select_related('badge').order_by('-awarded_at')
    context = {
        'user_badges': user_badges
    }
    return render(request, 'practice/my_badges.html', context)

# --- Admin Views ---
@login_required(login_url='login')
@user_passes_test(is_admin, login_url='login')
def admin_dashboard(request):
    """Admin dashboard for platform oversight"""
    pending_tutors = UserProfile.objects.filter(role='TUTOR', is_approved_tutor=False)
    pending_problems = PracticeProblem.objects.filter(status='PENDING_APPROVAL').order_by('-created_at')
    
    # Platform statistics
    stats = {
        'total_users': UserProfile.objects.count(),
        'total_problems': PracticeProblem.objects.filter(status='PUBLISHED').count(),
        'total_submissions': PracticeSubmission.objects.count(),
        'active_users': UserStats.objects.filter(
            last_solved_date__gte=timezone.now().date() - timedelta(days=7)
        ).count(),
    }

    context = {
        'pending_tutors': pending_tutors,
        'pending_problems': pending_problems,
        'stats': stats,
    }
    
    return render(request, 'admin/dashboard.html', context)

@login_required(login_url='login')
@user_passes_test(is_admin, login_url='login')
def admin_approve_tutor(request, user_id):
    """Approve a tutor account"""
    user_profile = get_object_or_404(UserProfile, user__id=user_id, role='TUTOR', is_approved_tutor=False)
    user_profile.is_approved_tutor = True
    user_profile.save()
    
    messages.success(request, f'Tutor {user_profile.user.username} has been approved.')
    return redirect('practice:admin_dashboard')

@login_required(login_url='login')
@user_passes_test(is_admin, login_url='login')
def admin_problem_approval(request, problem_slug, action):
    """Handle problem approval actions"""
    problem = get_object_or_404(PracticeProblem, slug=problem_slug)

    if action == 'publish':
        problem.status = 'PUBLISHED'
        messages.success(request, f'Problem "{problem.title}" has been published.')
    elif action == 'reject':
        problem.status = 'DRAFT'
        messages.warning(request, f'Problem "{problem.title}" has been rejected.')
    elif action == 'archive':
        problem.status = 'ARCHIVED'
        messages.info(request, f'Problem "{problem.title}" has been archived.')
    else:
        messages.error(request, 'Invalid action.')
        return redirect('practice:admin_dashboard')

    problem.save()
    return redirect('practice:admin_dashboard')

# --- AJAX Views ---
@login_required(login_url='login')
@csrf_exempt
def vote_discussion(request, discussion_id):
    """Handle voting on discussions"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)
    
    discussion = get_object_or_404(Discussion, id=discussion_id)
    vote_value = int(request.POST.get('vote', 0))
    
    if vote_value not in [1, -1]:
        return JsonResponse({'error': 'Invalid vote'}, status=400)
    
    vote, created = DiscussionVote.objects.get_or_create(
        discussion=discussion,
        user=request.user,
        defaults={'vote': vote_value}
    )
    
    if not created:
        if vote.vote == vote_value:
            # Remove vote if same vote
            vote.delete()
            vote_value = 0
        else:
            # Update vote
            vote.vote = vote_value
            vote.save()
    
    # Update discussion vote counts
    discussion.upvotes = discussion.votes.filter(vote=1).count()
    discussion.downvotes = discussion.votes.filter(vote=-1).count()
    discussion.save()
    
    return JsonResponse({
        'upvotes': discussion.upvotes,
        'downvotes': discussion.downvotes,
        'user_vote': vote_value
    })

@login_required(login_url='login')
def get_problem_hints(request, slug):
    """Get hints for a problem"""
    problem = get_object_or_404(PracticeProblem, slug=slug, status='PUBLISHED')
    
    # Check if user has attempted the problem
    user_stats = UserProblemStats.objects.filter(user=request.user, problem=problem).first()
    if not user_stats or not user_stats.is_attempted:
        return JsonResponse({'error': 'Attempt the problem first to unlock hints'}, status=403)
    
    return JsonResponse({'hints': problem.hints})

@login_required(login_url='login')
def get_language_template(request, slug, language):
    """Get code template for specific language"""
    problem = get_object_or_404(PracticeProblem, slug=slug, status='PUBLISHED')
    template = get_default_code_template(language, problem.title)
    return JsonResponse({'template': template})

@login_required(login_url='login')
@user_passes_test(is_tutor, login_url='login')
def add_video_solution(request, slug):
    """Tutor/Staff view to add a video solution to a problem"""
    problem = get_object_or_404(PracticeProblem, slug=slug)
    
    if request.method == 'POST':
        form = ProblemVideoSolutionForm(request.POST)
        if form.is_valid():
            video_solution = form.save(commit=False)
            video_solution.problem = problem
            video_solution.user = request.user
            video_solution.save()
            messages.success(request, 'Video solution added successfully!')
            return redirect('practice:problem_detail', slug=slug)
    else:
        form = ProblemVideoSolutionForm()
    
    context = {
        'form': form,
        'problem': problem,
    }
    
    return render(request, 'tutor/add_video_solution.html', context)

@login_required(login_url='login')
def get_submission_details(request, submission_id):
    submission = get_object_or_404(PracticeSubmission, id=submission_id, user=request.user)
    return JsonResponse({
        'id': submission.id,
        'status': submission.status,
        'language': submission.get_language_display(),
        'code': submission.code,
        'passed_cases': submission.passed_cases,
        'total_cases': submission.total_cases,
        'execution_time': f"{submission.execution_time or 0:.3f}s",
        'memory_used': f"{submission.memory_used or 0} KB",
        'submitted_at': submission.submitted_at.strftime("%b %d, %Y, %I:%M %p"),
        'results': submission.results,
    })