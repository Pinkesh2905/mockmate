from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.contrib import messages
from django.urls import reverse
from django.template.defaultfilters import slugify
from django.db import transaction # For atomic operations
from django.db import models # Import models for Q objects

from .models import Quiz, Question, Answer, QuizAttempt
# IMPORTANT: Import Course from courses.models
from courses.models import Course
from .forms import QuizForm, QuestionFormSet, AnswerFormSet, QuizAttemptForm

# Import UserProfile and role checkers from users app
from users.models import UserProfile # <--- CORRECTED: UserProfile is now in users.models

# Helper functions for role-based checks (now correctly reference UserProfile from users.models)
# It's generally better to centralize these in a shared utility file (e.g., in 'core' or a new 'utils' app)
# or in the 'users' app itself, but for now, they work here.
def is_student(user):
    return user.is_authenticated and hasattr(user, 'profile') and user.profile.role == 'STUDENT'

def is_tutor(user):
    return user.is_authenticated and hasattr(user, 'profile') and user.profile.role == 'TUTOR' and user.profile.is_approved_tutor

def is_admin(user):
    return user.is_authenticated and user.is_superuser


# --- Public/Student Facing Views ---
@login_required
@user_passes_test(is_student, login_url='/login/')
def quiz_list(request):
    """
    Displays a list of all PUBLISHED quizzes for students.
    """
    quizzes = Quiz.objects.filter(status='PUBLISHED').order_by('-created_at')
    
    # Optionally, filter quizzes by course if a course_slug is provided in URL
    course_slug = request.GET.get('course')
    if course_slug:
        course = get_object_or_404(Course, slug=course_slug)
        quizzes = quizzes.filter(course=course)
        messages.info(request, f"Showing quizzes for course: {course.title}")

    return render(request, 'quizzes/quiz_list.html', {'quizzes': quizzes})

@login_required
@user_passes_test(is_student, login_url='/login/')
def quiz_detail(request, slug):
    """
    Displays details of a single PUBLISHED quiz.
    """
    quiz = get_object_or_404(Quiz, slug=slug, status='PUBLISHED')
    
    # Check if user has attempted this quiz before
    latest_attempt = QuizAttempt.objects.filter(user=request.user, quiz=quiz).order_by('-start_time').first()

    context = {
        'quiz': quiz,
        'latest_attempt': latest_attempt,
    }
    return render(request, 'quizzes/quiz_detail.html', context)

@login_required
@user_passes_test(is_student, login_url='/login/')
def take_quiz(request, slug):
    """
    Allows a student to take a quiz.
    """
    quiz = get_object_or_404(Quiz, slug=slug, status='PUBLISHED')
    questions = quiz.questions.all()

    if not questions.exists():
        messages.warning(request, "This quiz has no questions yet!")
        return redirect('quizzes:quiz_detail', slug=slug)

    if request.method == 'POST':
        form = QuizAttemptForm(request.POST, quiz=quiz)
        if form.is_valid():
            selected_answers = {}
            for field_name, value in form.cleaned_data.items():
                if field_name.startswith('question_'):
                    question_id = int(field_name.replace('question_', ''))
                    selected_answers[str(question_id)] = [int(value)] # Store as list for future multi-choice

            with transaction.atomic():
                attempt = QuizAttempt.objects.create(
                    user=request.user,
                    quiz=quiz,
                    start_time=timezone.now(), # This will be updated to actual start time if using JS timer
                    selected_answers=selected_answers
                )
                attempt.end_time = timezone.now() # For simplicity, end_time is now
                attempt.calculate_score() # This will save the attempt as well

            messages.success(request, "Quiz submitted successfully!")
            return redirect('quizzes:quiz_result', slug=quiz.slug, attempt_id=attempt.id)
        else:
            messages.error(request, "Please answer all questions before submitting.")
    else:
        form = QuizAttemptForm(quiz=quiz)

    context = {
        'quiz': quiz,
        'form': form,
        'questions': questions, # Pass questions to template for rendering form fields
    }
    return render(request, 'quizzes/take_quiz.html', context)


@login_required
@user_passes_test(is_student, login_url='/login/')
def quiz_result(request, slug, attempt_id):
    """
    Displays the result of a specific quiz attempt.
    """
    quiz = get_object_or_404(Quiz, slug=slug, status='PUBLISHED')
    attempt = get_object_or_404(QuizAttempt, id=attempt_id, user=request.user, quiz=quiz)

    # Prepare data for detailed review
    questions_data = []
    for question in quiz.questions.all().order_by('id'):
        correct_answer = question.answers.filter(is_correct=True).first()
        selected_answer_id = attempt.selected_answers.get(str(question.id))
        
        selected_answer = None
        if selected_answer_id and isinstance(selected_answer_id, list):
            selected_answer = question.answers.filter(id=selected_answer_id[0]).first()

        questions_data.append({
            'question': question,
            'answers': question.answers.all(),
            'correct_answer': correct_answer,
            'selected_answer': selected_answer,
            'is_correct': (selected_answer == correct_answer)
        })

    context = {
        'quiz': quiz,
        'attempt': attempt,
        'questions_data': questions_data,
    }
    return render(request, 'quizzes/quiz_result.html', context)


# --- Tutor/Staff Specific Views ---
@login_required
@user_passes_test(is_tutor, login_url='/login/')
def tutor_quiz_list(request):
    """
    Tutor's main dashboard for managing their quizzes.
    """
    quizzes = Quiz.objects.filter(created_by=request.user).order_by('status', '-created_at')
    return render(request, 'tutor/quiz_dashboard.html', {'quizzes': quizzes})

@login_required
@user_passes_test(is_tutor, login_url='/login/')
def quiz_create_edit(request, slug=None):
    """
    Allows tutors to create new quizzes or edit their existing quizzes.
    Handles QuizForm, QuestionFormSet, and AnswerFormSet.
    """
    quiz_instance = None
    if slug:
        quiz_instance = get_object_or_404(Quiz, slug=slug, created_by=request.user)

    if request.method == 'POST':
        form = QuizForm(request.POST, instance=quiz_instance)
        
        if form.is_valid():
            with transaction.atomic(): # Ensure atomicity for quiz and its questions/answers
                new_quiz = form.save(commit=False)
                if not quiz_instance: # If creating a new quiz
                    new_quiz.created_by = request.user
                    new_quiz.status = 'PENDING_APPROVAL'
                new_quiz.save()

                # Handle QuestionFormSet and AnswerFormSet
                question_formset = QuestionFormSet(request.POST, instance=new_quiz)
                if question_formset.is_valid():
                    questions = question_formset.save(commit=False)
                    for question in questions:
                        question.quiz = new_quiz
                        question.save()
                    # Handle deleted questions
                    for question in question_formset.deleted_objects:
                        question.delete()

                    # Now iterate through questions to save answers
                    for i, q_form in enumerate(question_formset):
                        if q_form.instance.pk: # Only process if question exists (not deleted)
                            answer_formset = AnswerFormSet(request.POST, instance=q_form.instance, prefix=f'question-{i}')
                            if answer_formset.is_valid():
                                answers = answer_formset.save(commit=False)
                                for answer in answers:
                                    answer.question = q_form.instance
                                    answer.save()
                                # Handle deleted answers
                                for answer in answer_formset.deleted_objects:
                                    answer.delete()
                            else:
                                messages.error(request, f'Errors in answers for question {i+1}: {answer_formset.errors}')
                                # Re-render with errors
                                return render(request, 'tutor/quiz_create_edit.html', {
                                    'form': form,
                                    'question_formset': question_formset,
                                    'quiz': quiz_instance,
                                    'is_new': quiz_instance is None,
                                })
                else:
                    messages.error(request, f'Errors in questions: {question_formset.errors}')
                    # Re-render with errors
                    return render(request, 'tutor/quiz_create_edit.html', {
                        'form': form,
                        'question_formset': question_formset,
                        'quiz': quiz_instance,
                        'is_new': quiz_instance is None,
                    })

            messages.success(request, f'Quiz "{new_quiz.title}" saved successfully. It is now pending admin approval.')
            return redirect('quizzes:tutor_quiz_list')
        else:
            messages.error(request, 'Please correct the errors in the quiz details.')
    else:
        form = QuizForm(instance=quiz_instance)
        question_formset = QuestionFormSet(instance=quiz_instance)
        # Manually create AnswerFormSets for existing questions
        for i, q_form in enumerate(question_formset):
            q_form.answer_formset = AnswerFormSet(instance=q_form.instance, prefix=f'question-{i}')

    context = {
        'form': form,
        'question_formset': question_formset,
        'quiz': quiz_instance,
        'is_new': quiz_instance is None,
    }
    return render(request, 'tutor/quiz_create_edit.html', context)


# --- Admin Specific Views (linked from practice app's admin_dashboard) ---
@login_required
@user_passes_test(is_admin, login_url='/login/')
def admin_quiz_approval(request, quiz_slug, action):
    """
    Admin action to approve, reject, or archive a quiz.
    """
    quiz = get_object_or_404(Quiz, slug=quiz_slug)

    if action == 'publish':
        quiz.status = 'PUBLISHED'
        messages.success(request, f'Quiz "{quiz.title}" has been published.')
    elif action == 'reject':
        quiz.status = 'DRAFT' # Move back to draft for tutor to revise
        messages.warning(request, f'Quiz "{quiz.title}" has been moved back to draft status.')
    elif action == 'archive':
        quiz.status = 'ARCHIVED'
        messages.info(request, f'Quiz "{quiz.title}" has been archived.')
    else:
        messages.error(request, 'Invalid action.')
        return redirect('practice:admin_dashboard') # Redirect to general admin dashboard

    quiz.save()
    return redirect('practice:admin_dashboard') # Redirect to general admin dashboard

