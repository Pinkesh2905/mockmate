# tutor/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import transaction, IntegrityError

# Models from aptitude app
from aptitude.models import AptitudeCategory, AptitudeTopic, AptitudeProblem, PracticeSet
# Forms from aptitude app
from aptitude.forms import AptitudeCategoryForm, AptitudeTopicForm, AptitudeProblemForm, PracticeSetForm

# Models/forms from practice app
from practice.models import PracticeProblem, TestCase, CodeTemplate
from practice.forms import ProblemForm, TestCaseFormSet, CodeTemplateFormSet

# Mock interview models and imports
from mock_interview.models import MockInterviewSession, InterviewTurn

# Role checker from users app
from users.views import is_tutor

def is_tutor_or_admin(user):
    return user.is_staff or hasattr(user, 'is_tutor') and user.is_tutor

@login_required
@user_passes_test(is_tutor, login_url='login')
def tutor_dashboard(request):
    """
    Displays the tutor dashboard.
    Includes both aptitude and practice problems (LeetCode-style).
    """

    if not request.user.profile.is_approved_tutor:
        return render(request, 'tutor/pending_approval.html', {
            "message": "Your tutor account is awaiting admin approval. Please check back later."
        })

    # Retrieve URL params for forms
    show = request.GET.get('show')
    edit_category_id = request.GET.get('edit_category')
    edit_topic_id = request.GET.get('edit_topic')
    edit_aptitude_problem_id = request.GET.get('edit_problem')
    edit_practice_problem_id = request.GET.get('edit_practice_problem')
    edit_practice_set_id = request.GET.get('edit_practice_set')

    # Aptitude app content
    categories = AptitudeCategory.objects.all().order_by('name')
    topics = AptitudeTopic.objects.all().order_by('category__name', 'name')
    aptitude_problems = AptitudeProblem.objects.all().order_by('-created_at')[:10]
    practice_sets = PracticeSet.objects.all().order_by('-created_at')

    # Practice app content (LeetCode-like)
    practice_problems = PracticeProblem.objects.all().order_by('-created_at')[:10]

    # Forms (Aptitude)
    category_form = AptitudeCategoryForm()
    topic_form = AptitudeTopicForm()
    aptitude_problem_form = AptitudeProblemForm()
    practice_set_form = PracticeSetForm()

    # Practice problem forms: always blank by default
    problem_form = ProblemForm()
    testcase_formset = TestCaseFormSet()
    codetemplate_formset = CodeTemplateFormSet()

    # Edit handling - Aptitude
    if edit_category_id:
        try:
            category = get_object_or_404(AptitudeCategory, id=edit_category_id)
            category_form = AptitudeCategoryForm(instance=category)
            show = 'category'
        except:
            messages.error(request, "Category not found.")
            return redirect('tutor:dashboard')

    if edit_topic_id:
        try:
            topic = get_object_or_404(AptitudeTopic, id=edit_topic_id)
            topic_form = AptitudeTopicForm(instance=topic)
            show = 'topic'
        except:
            messages.error(request, "Topic not found.")
            return redirect('tutor:dashboard')

    if edit_aptitude_problem_id:
        try:
            problem = get_object_or_404(AptitudeProblem, id=edit_aptitude_problem_id)
            aptitude_problem_form = AptitudeProblemForm(instance=problem)
            show = 'problem'
        except:
            messages.error(request, "Problem not found.")
            return redirect('tutor:dashboard')

    if edit_practice_set_id:
        try:
            practice_set = get_object_or_404(PracticeSet, id=edit_practice_set_id)
            practice_set_form = PracticeSetForm(instance=practice_set)
            show = 'practice_set'
        except:
            messages.error(request, "Practice set not found.")
            return redirect('tutor:dashboard')

    # Edit handling - PracticeProblem (LeetCode-style)
    if edit_practice_problem_id:
        try:
            practice_problem = get_object_or_404(PracticeProblem, id=edit_practice_problem_id)
            problem_form = ProblemForm(instance=practice_problem)
            testcase_formset = TestCaseFormSet(instance=practice_problem)
            codetemplate_formset = CodeTemplateFormSet(instance=practice_problem)
            show = 'practice_problem'
        except:
            messages.error(request, "Practice problem not found.")
            return redirect('tutor:dashboard')

    context = {
        # Aptitude fields
        'categories': categories,
        'topics': topics,
        'aptitude_problems': aptitude_problems,
        'practice_sets': practice_sets,
        'category_form': category_form,
        'topic_form': topic_form,
        'aptitude_problem_form': aptitude_problem_form,
        'practice_set_form': practice_set_form,
        # Practice fields
        'practice_problems': practice_problems,
        'problem_form': problem_form,
        'testcase_formset': testcase_formset,
        'codetemplate_formset': codetemplate_formset,
        # Misc
        'show': show,
        'edit_category_id': edit_category_id,
        'edit_topic_id': edit_topic_id,
        'edit_aptitude_problem_id': edit_aptitude_problem_id,
        'edit_practice_problem_id': edit_practice_problem_id,
        'edit_practice_set_id': edit_practice_set_id,
    }

    return render(request, 'tutor/dashboard.html', context)

@login_required
@user_passes_test(is_tutor, login_url='login')
def tutor_content_create_update(request):
    """
    Handles creation/updating of all content types:
    Aptitude and Practice problems fully supported.
    """
    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect('tutor:dashboard')

    content_type = request.POST.get('content_type')

    try:
        with transaction.atomic():
            # Aptitude content
            if content_type == 'category':
                category_id = request.POST.get('category_id')
                instance = AptitudeCategory.objects.get(id=category_id) if category_id else None
                form = AptitudeCategoryForm(request.POST, instance=instance)
                if form.is_valid():
                    category = form.save()
                    action = "updated" if instance else "created"
                    messages.success(request, f"Category '{category.name}' {action} successfully!")
                else:
                    for field, errors in form.errors.items():
                        for error in errors:
                            messages.error(request, f"Category error in {field}: {error}")

            elif content_type == 'topic':
                topic_id = request.POST.get('topic_id')
                instance = AptitudeTopic.objects.get(id=topic_id) if topic_id else None
                form = AptitudeTopicForm(request.POST, instance=instance)
                if form.is_valid():
                    topic = form.save()
                    action = "updated" if instance else "created"
                    messages.success(request, f"Topic '{topic.name}' {action} successfully!")
                else:
                    for field, errors in form.errors.items():
                        for error in errors:
                            messages.error(request, f"Topic error in {field}: {error}")

            elif content_type == 'problem':
                problem_id = request.POST.get('problem_id')
                instance = AptitudeProblem.objects.get(id=problem_id) if problem_id else None
                form = AptitudeProblemForm(request.POST, instance=instance)
                if form.is_valid():
                    problem = form.save()
                    action = "updated" if instance else "created"
                    messages.success(request, f"Problem {action} successfully!")
                else:
                    for field, errors in form.errors.items():
                        for error in errors:
                            messages.error(request, f"Problem error in {field}: {error}")

            elif content_type == 'practice_set':
                practice_set_id = request.POST.get('practice_set_id')
                instance = PracticeSet.objects.get(id=practice_set_id) if practice_set_id else None
                form = PracticeSetForm(request.POST, instance=instance)
                if form.is_valid():
                    practice_set = form.save(commit=False)
                    practice_set.created_by = request.user
                    practice_set.save()
                    form.save_m2m()  # Save many-to-many relationships
                    action = "updated" if instance else "created"
                    messages.success(request, f"Practice Set '{practice_set.title}' {action} successfully!")
                else:
                    for field, errors in form.errors.items():
                        for error in errors:
                            messages.error(request, f"Practice Set error in {field}: {error}")

            # Practice problem section (LeetCode-like)
            elif content_type == 'practice_problem':
                practice_problem_id = request.POST.get('practice_problem_id')
                instance = PracticeProblem.objects.get(id=practice_problem_id) if practice_problem_id else None
                problem_form = ProblemForm(request.POST, instance=instance)
                testcase_formset = TestCaseFormSet(request.POST, instance=instance)
                codetemplate_formset = CodeTemplateFormSet(request.POST, instance=instance)

                if problem_form.is_valid() and testcase_formset.is_valid() and codetemplate_formset.is_valid():
                    practice_problem = problem_form.save(commit=False)
                    practice_problem.created_by = request.user
                    practice_problem.save()
                    problem_form.save_m2m()
                    testcase_formset.instance = practice_problem
                    testcase_formset.save()
                    codetemplate_formset.instance = practice_problem
                    codetemplate_formset.save()
                    action = "updated" if instance else "created"
                    messages.success(request, f"Practice Problem '{practice_problem.title}' {action} successfully!")
                else:
                    for field, errors in problem_form.errors.items():
                        for error in errors:
                            messages.error(request, f"Practice Problem error in {field}: {error}")
                    for form in list(testcase_formset):
                        for field, errors in form.errors.items():
                            for error in errors:
                                messages.error(request, f"Test Case error in {field}: {error}")
                    for form in list(codetemplate_formset):
                        for field, errors in form.errors.items():
                            for error in errors:
                                messages.error(request, f"Code Template error in {field}: {error}")
            else:
                messages.error(request, "Invalid content type.")
    except AptitudeCategory.DoesNotExist:
        messages.error(request, "Category not found.")
    except AptitudeTopic.DoesNotExist:
        messages.error(request, "Topic not found.")
    except AptitudeProblem.DoesNotExist:
        messages.error(request, "Aptitude problem not found.")
    except PracticeSet.DoesNotExist:
        messages.error(request, "Practice set not found.")
    except PracticeProblem.DoesNotExist:
        messages.error(request, "Practice problem not found.")
    except IntegrityError as e:
        messages.error(request, f"Database error: {e}")
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {e}")

    return redirect('tutor:dashboard')

# @login_required
# @user_passes_test(is_tutor_or_admin)
# def tutor_interview_review_list(request):
#     """
#     Shows list of mock interview sessions for review.
#     """
#     sessions = MockInterviewSession.objects.filter(
#         status__in=['REVIEW_PENDING', 'COMPLETED']
#     ).order_by('-created_at')
#     return render(request, 'tutor/mock_interview_review_list.html', {'sessions': sessions})

# @login_required
# @user_passes_test(is_tutor_or_admin)
# def tutor_review_interview_detail(request, session_id):
#     """
#     Shows detailed view of a mock interview session for review and scoring.
#     """
#     session = get_object_or_404(MockInterviewSession, id=session_id)
#     turns = InterviewTurn.objects.filter(session=session).order_by('turn_number')

#     if request.method == 'POST':
#         tutor_feedback = request.POST.get('tutor_feedback')
#         tutor_score = request.POST.get('tutor_score')
#         status = request.POST.get('status')
#         session.overall_feedback = tutor_feedback

#         try:
#             session.score = float(tutor_score) if tutor_score else None
#         except ValueError:
#             session.score = None

#         session.status = status
#         session.save()
#         messages.success(request, "Review saved successfully.")
#         return redirect('tutor:mock_interview_review_list')

#     return render(request, 'tutor/mock_interview_review_detail.html', {
#         'session': session,
#         'turns': turns
#     })
