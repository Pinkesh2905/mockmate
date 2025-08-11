# mockmate01/tutor/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import transaction, IntegrityError
from django.utils.text import slugify
from django.views.decorators.http import require_POST
from django.core.exceptions import ValidationError
from io import TextIOWrapper
import csv

# Models from respective apps
from courses.models import Course, Lesson
from quizzes.models import Quiz, Question, Answer
from articles.models import Article
from practice.models import PracticeProblem, TestCase

# Forms from respective apps
from courses.forms import CourseForm, LessonFormSet
from quizzes.forms import QuizForm, QuestionFormSet, AnswerFormSet
from articles.forms import ArticleForm
from practice.forms import ProblemForm, TestCaseFormSet

# Role checker from users app
from users.views import is_tutor
from users.models import UserProfile 


from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from mock_interview.models import MockInterviewSession, InterviewTurn

# Utility to check if user is tutor/admin
def is_tutor_or_admin(user):
    return user.is_staff or hasattr(user, 'is_tutor') and user.is_tutor

# Helper function to ensure unique slug
def generate_unique_slug(model, title):
    """Generates a unique URL-friendly slug from a title."""
    base_slug = slugify(title)
    slug = base_slug
    counter = 1
    while model.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug

# --- Tutor Dashboard View ---
@login_required
@user_passes_test(is_tutor, login_url='login')
def tutor_dashboard(request):
    """
    Displays the tutor dashboard with all their created content.
    - Shows a pending approval message if the tutor is not yet approved.
    - Lists courses, quizzes, articles, and practice problems.
    """
    if not request.user.profile.is_approved_tutor:
        return render(request, 'tutor/pending_approval.html', {
            "message": "Your tutor account is awaiting admin approval. Please check back later."
        })

    # Retrieve all content created by the current tutor
    courses = Course.objects.filter(created_by=request.user).order_by('-created_at')
    quizzes = Quiz.objects.filter(created_by=request.user).order_by('-created_at')
    articles = Article.objects.filter(created_by=request.user).order_by('-created_at')
    practice_problems = PracticeProblem.objects.filter(created_by=request.user).order_by('-created_at')

    # Initialize empty forms for creation modals
    course_form = CourseForm()
    quiz_form = QuizForm()
    article_form = ArticleForm()
    problem_form = ProblemForm()

    context = {
        'courses': courses,
        'quizzes': quizzes,
        'articles': articles,
        'practice_problems': practice_problems,
        'course_form': course_form,
        'quiz_form': quiz_form,
        'article_form': article_form,
        'problem_form': problem_form,
    }
    return render(request, 'tutor/dashboard.html', context)


# --- Content Creation/Update View (Handles all content types via form) ---
@login_required
@user_passes_test(is_tutor, login_url='login')
def tutor_content_create_update(request):
    """
    Handles the creation and updating of all content types (courses, quizzes, etc.)
    This single view processes POST requests from the dashboard modals.
    """
    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect('tutor:dashboard')

    content_type = request.POST.get('content_type')
    slug = request.POST.get('slug', None)

    try:
        with transaction.atomic():
            if content_type == 'course':
                instance = Course.objects.filter(slug=slug, created_by=request.user).first() if slug else None
                course_form = CourseForm(request.POST, request.FILES, instance=instance)
                lesson_formset = LessonFormSet(request.POST, request.FILES, prefix='lessons', instance=instance)
                
                if course_form.is_valid() and lesson_formset.is_valid():
                    course = course_form.save(commit=False)
                    course.created_by = request.user
                    if not course.slug:
                        course.slug = generate_unique_slug(Course, course.title)
                    course.save()
                    course_form.save_m2m()
                    lesson_formset.instance = course
                    lesson_formset.save()
                    messages.success(request, f"Course '{course.title}' saved successfully!")
                else:
                    errors = course_form.errors.as_data()
                    for form in lesson_formset:
                        errors.update(form.errors.as_data())
                    for field, errs in errors.items():
                        for err in errs:
                            messages.error(request, f"Course form error on field '{field}': {err}")
                    raise IntegrityError("Form validation failed.")

            elif content_type == 'quiz':
                instance = Quiz.objects.filter(slug=slug, created_by=request.user).first() if slug else None
                quiz_form = QuizForm(request.POST, instance=instance)
                
                if quiz_form.is_valid():
                    quiz = quiz_form.save(commit=False)
                    quiz.created_by = request.user
                    if not quiz.slug:
                        quiz.slug = generate_unique_slug(Quiz, quiz.title)
                    quiz.save()
                    question_formset = QuestionFormSet(request.POST, prefix='questions', instance=quiz)
                    if question_formset.is_valid():
                        questions = question_formset.save(commit=False)
                        for question in questions:
                            question.quiz = quiz
                            question.save()
                            answer_formset = AnswerFormSet(request.POST, prefix=f'answers-{question.id}', instance=question)
                            if answer_formset.is_valid():
                                answer_formset.save()
                            else:
                                for form in answer_formset:
                                    messages.error(request, f"Answer formset error: {form.errors}")
                                raise IntegrityError("Answer formset validation failed.")
                        messages.success(request, f"Quiz '{quiz.title}' saved successfully.")
                    else:
                        for form in question_formset:
                            messages.error(request, f"Question formset error: {form.errors}")
                        raise IntegrityError("Question formset validation failed.")
                else:
                    messages.error(request, "Error saving quiz.")

            elif content_type == 'article':
                instance = Article.objects.filter(slug=slug, created_by=request.user).first() if slug else None
                article_form = ArticleForm(request.POST, instance=instance)
                
                if article_form.is_valid():
                    article = article_form.save(commit=False)
                    article.created_by = request.user
                    if not article.slug:
                        article.slug = generate_unique_slug(Article, article.title)
                    article.status = 'PENDING_APPROVAL'
                    article.save()
                    messages.success(request, f"Article '{article.title}' saved successfully.")
                else:
                    messages.error(request, "Error saving article.")

            elif content_type == 'practice':
                instance = PracticeProblem.objects.filter(slug=slug, created_by=request.user).first() if slug else None
                problem_form = ProblemForm(request.POST, instance=instance)
                testcase_formset = TestCaseFormSet(request.POST, prefix='testcases', instance=instance)

                if problem_form.is_valid() and testcase_formset.is_valid():
                    problem = problem_form.save(commit=False)
                    problem.created_by = request.user
                    if not problem.slug:
                        problem.slug = generate_unique_slug(PracticeProblem, problem.title)
                    problem.save()
                    problem_form.save_m2m()
                    testcase_formset.instance = problem
                    testcase_formset.save()
                    messages.success(request, f"Practice Problem '{problem.title}' saved successfully.")
                else:
                    errors = problem_form.errors.as_data()
                    for form in testcase_formset:
                        errors.update(form.errors.as_data())
                    for field, errs in errors.items():
                        for err in errs:
                            messages.error(request, f"Practice Problem form error on field '{field}': {err}")
                    raise IntegrityError("Form validation failed.")
            else:
                messages.error(request, "Invalid content type.")
    except IntegrityError as e:
        print(f"Transaction rolled back due to error: {e}")
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {e}")
    return redirect('tutor:dashboard')


# --- CSV Upload View for Bulk Content Creation ---
@login_required
@user_passes_test(is_tutor, login_url='login')
@require_POST
def upload_csv(request):
    """
    Handles bulk content creation via CSV file upload.
    The CSV must have a 'type' column to specify the content type.
    """
    if 'file' not in request.FILES:
        messages.error(request, "No file was uploaded.")
        return redirect('tutor:dashboard')

    csv_file = request.FILES['file']

    if not csv_file.name.endswith('.csv'):
        messages.error(request, "Please upload a CSV file.")
        return redirect('tutor:dashboard')

    # Use TextIOWrapper to read the uploaded file as a text file
    csv_data = TextIOWrapper(csv_file, encoding='utf-8')
    reader = csv.DictReader(csv_data)
    
    created_items = 0
    failed_rows = []

    try:
        with transaction.atomic():
            for row_num, row in enumerate(reader, start=1):
                try:
                    row_type = row.get('type', '').lower().strip()
                    title = row.get('title', '').strip()

                    if not row_type or not title:
                        raise ValueError("Missing 'type' or 'title' column.")
                    
                    if row_type == 'course':
                        Course.objects.create(
                            title=title,
                            slug=generate_unique_slug(Course, title),
                            description=row.get('description', ''),
                            created_by=request.user
                        )
                    elif row_type == 'article':
                        Article.objects.create(
                            title=title,
                            slug=generate_unique_slug(Article, title),
                            content=row.get('content', ''),
                            status='PENDING_APPROVAL',
                            created_by=request.user
                        )
                    elif row_type == 'practice':
                        PracticeProblem.objects.create(
                            title=title,
                            slug=generate_unique_slug(PracticeProblem, title),
                            statement=row.get('statement', ''),
                            difficulty=row.get('difficulty', 'EASY'),
                            created_by=request.user
                        )
                    else:
                        raise ValueError(f"Unsupported content type '{row_type}'.")
                    
                    created_items += 1
                except Exception as e:
                    failed_rows.append((row_num, str(e)))

    except (IntegrityError, ValueError) as e:
        messages.error(request, f"An error occurred during transaction: {e}")

    # Display success and error messages
    if created_items:
        messages.success(request, f"{created_items} items added successfully via CSV.")
    if failed_rows:
        error_text = "; ".join([f"Row {num}: {error}" for num, error in failed_rows])
        messages.error(request, f"Some rows failed to import: {error_text}")

    return redirect('tutor:dashboard')


@login_required
@user_passes_test(is_tutor_or_admin)
def tutor_interview_review_list(request):
    sessions = MockInterviewSession.objects.filter(status__in=['REVIEW_PENDING', 'COMPLETED']).order_by('-created_at')
    return render(request, 'tutor/mock_interview_review_list.html', {'sessions': sessions})

@login_required
@user_passes_test(is_tutor_or_admin)
def tutor_review_interview_detail(request, session_id):
    session = get_object_or_404(MockInterviewSession, id=session_id)
    turns = InterviewTurn.objects.filter(session=session).order_by('turn_number')

    if request.method == 'POST':
        tutor_feedback = request.POST.get('tutor_feedback')
        tutor_score = request.POST.get('tutor_score')
        status = request.POST.get('status')

        session.overall_feedback = tutor_feedback
        try:
            session.score = float(tutor_score) if tutor_score else None
        except ValueError:
            session.score = None
        session.status = status
        session.save()

        messages.success(request, "Review saved successfully.")
        return redirect('mock_interview:tutor_interview_review_list')

    return render(request, 'tutor/mock_interview_review_detail.html', {
        'session': session,
        'turns': turns
    })
