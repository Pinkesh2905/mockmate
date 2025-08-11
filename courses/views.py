from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test # user_passes_test added
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils import timezone
from django.db import models # Import models for Q objects

from .models import Course, Enrollment, Lesson, WatchedLesson, Certificate
# Import UserProfile from users.models
from users.models import UserProfile
# Import forms from this app
from .forms import CourseForm, LessonFormSet

# Helper functions for role-based checks (now correctly reference UserProfile from users.models)
# It's generally better to centralize these in a shared utility file (e.g., in 'core' or a new 'utils' app)
# or in the 'users' app itself, but for now, they work here.
def is_student(user):
    return user.is_authenticated and hasattr(user, 'profile') and user.profile.role == 'STUDENT'

def is_tutor(user):
    return user.is_authenticated and hasattr(user, 'profile') and user.profile.role == 'TUTOR' and user.profile.is_approved_tutor

def is_admin(user):
    return user.is_authenticated and user.is_superuser


def course_list(request):
    """
    Displays a list of available courses with search & category filter.
    Made public so users can browse before signing up.
    """
    # Only show published courses to public and students
    if request.user.is_authenticated and (is_admin(request.user) or is_tutor(request.user)):
        qs = Course.objects.all() # Admins/Tutors can see all courses
    else:
        qs = Course.objects.filter(status='PUBLISHED') # Public/Students only see published

    q = request.GET.get("q", "")
    cat = request.GET.get("category", "")
    level = request.GET.get("level", "")

    if q:
        qs = qs.filter(title__icontains=q)
    if cat:
        qs = qs.filter(category=cat)
    if level:
        qs = qs.filter(level=level)

    paginator = Paginator(qs, 9)  # Show 9 courses per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    categories = Course.objects.values_list("category", flat=True).distinct()
    levels = Course.objects.values_list("level", flat=True).distinct()

    return render(request, "courses/course_list.html", {
        "courses": page_obj,
        "page_obj": page_obj,
        "search_query": q,
        "current_category": cat,
        "current_level": level,
        "categories": categories,
        "levels": levels,
        "is_paginated": page_obj.has_other_pages(),
    })


def course_detail(request, id):
    """
    Displays details of a single course, including lessons.
    """
    course = get_object_or_404(Course, id=id)
    lessons = course.lessons.all().order_by('order') # Get all lessons for the course

    enrolled = False
    watched_lessons = []
    if request.user.is_authenticated:
        enrolled = Enrollment.objects.filter(user=request.user, course=course).exists()
        watched_lessons = WatchedLesson.objects.filter(user=request.user, lesson__course=course).values_list('lesson__id', flat=True)

    # If user is not enrolled and the course is not published, deny access (unless admin/tutor)
    if not enrolled and course.status != 'PUBLISHED':
        if not (request.user.is_authenticated and (is_admin(request.user) or (is_tutor(request.user) and course.created_by == request.user))):
            messages.error(request, "This course is not published or you are not authorized to view it.")
            return redirect('courses:list')

    return render(request, "courses/course_detail.html", {
        "course": course,
        "lessons": lessons,
        "enrolled": enrolled,
        "watched_lessons": watched_lessons,
    })


@login_required
def enroll_in_course(request, id):
    """
    Handles user enrollment in a course.
    """
    course = get_object_or_404(Course, id=id)
    # Check if already enrolled
    if Enrollment.objects.filter(user=request.user, course=course).exists():
        messages.info(request, "You are already enrolled in this course.")
        return redirect('courses:detail', id=course.id)

    # Create enrollment
    Enrollment.objects.create(user=request.user, course=course)
    messages.success(request, f"You have successfully enrolled in {course.title}!")
    return redirect('courses:detail', id=course.id)


@login_required
def lesson_detail(request, course_id, lesson_id):
    """
    Displays a single lesson within a course.
    """
    course = get_object_or_404(Course, id=course_id)
    lesson = get_object_or_404(Lesson, id=lesson_id, course=course)
    all_lessons = course.lessons.all().order_by('order')

    enrolled = False
    watched_lessons = []
    if request.user.is_authenticated:
        enrolled = Enrollment.objects.filter(user=request.user, course=course).exists()
        watched_lessons = WatchedLesson.objects.filter(user=request.user, lesson__course=course).values_list('lesson__id', flat=True)

    # Access control:
    # 1. User must be enrolled OR lesson must be a free preview
    # 2. If not enrolled and not free preview, then only admin/tutor (who created it) can view
    if not enrolled and not lesson.is_free_preview:
        if not (request.user.is_authenticated and (is_admin(request.user) or (is_tutor(request.user) and (course.created_by == request.user or lesson.created_by == request.user)))):
            messages.error(request, "You are not authorized to view this lesson. Please enroll in the course.")
            return redirect('courses:detail', id=course.id)

    return render(request, "courses/lesson_detail.html", {
        "course": course,
        "lesson": lesson,
        "all_lessons": all_lessons,
        "watched_lessons": watched_lessons,
        "enrolled": enrolled,
    })


@login_required
def mark_lesson_watched(request, lesson_id):
    """
    AJAX endpoint to mark a lesson as watched
    """
    if request.method == 'POST':
        lesson = get_object_or_404(Lesson, id=lesson_id)
        
        # Check enrollment
        enrolled = Enrollment.objects.filter(
            user=request.user, 
            course=lesson.course
        ).exists()
        
        if not enrolled and not lesson.is_free_preview:
            return JsonResponse({'error': 'Not enrolled'}, status=403)
        
        watched_lesson, created = WatchedLesson.objects.get_or_create(
            user=request.user,
            lesson=lesson
        )
        
        return JsonResponse({
            'success': True,
            'created': created,
            'progress': lesson.course.get_completion_percentage(request.user)
        })
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
def my_courses(request):
    """
    Displays a list of courses the current user is enrolled in.
    """
    enrollments = Enrollment.objects.filter(user=request.user).order_by('-enrolled_at')
    
    # Calculate overall progress (simple average for display)
    total_progress = sum([e.progress for e in enrollments])
    overall_progress = int(total_progress / len(enrollments)) if enrollments else 0

    return render(request, "courses/my_courses.html", {
        "enrollments": enrollments,
        "overall_progress": overall_progress,
    })


@login_required
@user_passes_test(is_tutor, login_url='/login/')
def tutor_course_list(request):
    """
    Tutor's dashboard to manage their courses.
    Tutors can see their own courses (draft, pending, published) and published courses by others.
    Admins can see all courses.
    """
    if is_admin(request.user):
        courses = Course.objects.all().order_by('-created_at')
    else: # is_tutor
        courses = Course.objects.filter(
            models.Q(created_by=request.user) | models.Q(status='PUBLISHED')
        ).order_by('-created_at')

    return render(request, 'courses/tutor_course_list.html', {'courses': courses})


@login_required
@user_passes_test(is_tutor, login_url='/login/')
def course_create(request):
    """
    Allows tutors to create a new course.
    """
    if request.method == 'POST':
        course_form = CourseForm(request.POST, request.FILES)
        lesson_formset = LessonFormSet(request.POST, request.FILES, prefix='lessons')

        if course_form.is_valid() and lesson_formset.is_valid():
            course = course_form.save(commit=False)
            course.created_by = request.user
            # Set initial status for new courses created by tutors
            course.status = 'PENDING_APPROVAL'
            course.save()
            course_form.save_m2m() # Save ManyToMany relationships (e.g., topics)

            lessons = lesson_formset.save(commit=False)
            for lesson in lessons:
                lesson.course = course
                lesson.created_by = request.user # Assign creator to lesson as well
                lesson.save()
            lesson_formset.save_m2m() # Save ManyToMany for lessons if any

            # Update total_lessons count after saving all lessons
            course.total_lessons = course.lessons.count()
            course.save(update_fields=['total_lessons'])

            messages.success(request, "Course created successfully and is pending approval!")
            return redirect('courses:tutor_course_list')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        course_form = CourseForm()
        lesson_formset = LessonFormSet(prefix='lessons')

    context = {
        'course_form': course_form,
        'lesson_formset': lesson_formset,
    }
    return render(request, 'courses/course_form.html', context)


@login_required
@user_passes_test(is_tutor, login_url='/login/')
def course_edit(request, pk):
    """
    Allows tutors to edit an existing course.
    Only allows editing if the user created the course or is an admin.
    """
    course = get_object_or_404(Course, pk=pk)

    # Authorization check
    if not (is_admin(request.user) or (is_tutor(request.user) and course.created_by == request.user)):
        messages.error(request, "You are not authorized to edit this course.")
        return redirect('courses:tutor_course_list')

    if request.method == 'POST':
        course_form = CourseForm(request.POST, request.FILES, instance=course)
        lesson_formset = LessonFormSet(request.POST, request.FILES, instance=course, prefix='lessons')

        if course_form.is_valid() and lesson_formset.is_valid():
            course = course_form.save(commit=False)
            # Admins can change status, tutors cannot change status here directly
            if not is_admin(request.user):
                # If tutor, ensure status remains unchanged from its current value
                # This prevents a tutor from trying to publish a course directly via edit
                course.status = Course.objects.get(pk=pk).status
            course.save()
            course_form.save_m2m()

            lessons = lesson_formset.save(commit=False)
            for lesson in lessons:
                lesson.course = course
                if not lesson.created_by: # Assign created_by if not already set (for new lessons in formset)
                    lesson.created_by = request.user
                lesson.save()
            for lesson in lesson_formset.deleted_objects:
                lesson.delete() # Delete lessons marked for deletion

            # Update total_lessons count after saving all lessons
            course.total_lessons = course.lessons.count()
            course.save(update_fields=['total_lessons'])

            messages.success(request, "Course updated successfully!")
            return redirect('courses:tutor_course_list')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        course_form = CourseForm(instance=course)
        lesson_formset = LessonFormSet(instance=course, prefix='lessons')

    context = {
        'course': course,
        'course_form': course_form,
        'lesson_formset': lesson_formset,
    }
    return render(request, 'courses/course_form.html', context)


@login_required
@user_passes_test(is_tutor, login_url='/login/')
def course_delete(request, pk):
    """
    Allows tutors to delete a course.
    Only allows deletion if the user created the course or is an admin.
    """
    course = get_object_or_404(Course, pk=pk)

    # Authorization check
    if not (is_admin(request.user) or (is_tutor(request.user) and course.created_by == request.user)):
        messages.error(request, "You are not authorized to delete this course.")
        return redirect('courses:tutor_course_list')

    if request.method == 'POST':
        course.delete()
        messages.success(request, "Course deleted successfully!")
        return redirect('courses:tutor_course_list')

    return render(request, 'courses/course_confirm_delete.html', {'course': course})

