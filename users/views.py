from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth.models import User
from django.urls import reverse

from .models import UserProfile
from .forms import SignupForm, UserUpdateForm, UserProfileUpdateForm
from posts.models import Post, Repost  # ✅ Importing posts to show in profile


# --- Role helper functions ---
def is_student(user):
    return user.is_authenticated and hasattr(user, 'profile') and user.profile.role == 'STUDENT'

def is_tutor(user):
    return user.is_authenticated and hasattr(user, 'profile') and user.profile.role == 'TUTOR' and user.profile.is_approved_tutor

def is_admin(user):
    return user.is_authenticated and user.is_superuser


# --- Signup View ---
def signup(request):
    """
    Handles user registration.
    - Creates a new User and assigns a UserProfile role.
    - Logs the user in immediately.
    - Redirects to dashboard after signup.
    """
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()

            selected_role = form.cleaned_data.get('role', 'STUDENT')

            # Use the signal-created profile, but fallback just in case
            if hasattr(user, 'profile'):
                user.profile.role = selected_role
                user.profile.save()
            else:
                UserProfile.objects.create(user=user, role=selected_role)

            auth_login(request, user)
            messages.success(request, "Account created successfully! Welcome to MockMate.")
            return redirect('dashboard_redirect')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = SignupForm()

    return render(request, 'users/signup.html', {'form': form})


# --- Logged-in User Profile View ---
@login_required(login_url='login')
def profile(request):
    """
    Displays and updates the logged-in user's profile.
    """
    user_profile = get_object_or_404(UserProfile, user=request.user)
    is_admin_user = is_admin(request.user)

    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = UserProfileUpdateForm(request.POST, request.FILES, instance=user_profile)

        # Prevent role or approval changes for non-admins
        if not is_admin_user:
            if 'role' in profile_form.fields:
                del profile_form.fields['role']
            if 'is_approved_tutor' in profile_form.fields:
                del profile_form.fields['is_approved_tutor']

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Your profile has been updated successfully!")
            return redirect('users:profile')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = UserProfileUpdateForm(instance=user_profile)

        if not is_admin_user:
            if 'role' in profile_form.fields:
                del profile_form.fields['role']
            if 'is_approved_tutor' in profile_form.fields:
                del profile_form.fields['is_approved_tutor']

    # Fetch logged-in user's posts
    user_posts = Post.objects.filter(author=request.user).order_by('-created_at')

    context = {
        'user_profile': user_profile,
        'user_form': user_form,
        'profile_form': profile_form,
        'is_admin_user': is_admin_user,
        'user_posts': user_posts,
        'is_own_profile': True,
    }

    return render(request, 'users/profile.html', context)


# --- Public User Profile View ---
def public_profile(request, username):
    user_profile = get_object_or_404(UserProfile, user__username=username)
    
    reposts = Repost.objects.filter(user=user_profile.user).select_related("original_post__author", "original_post__author__profile")
    reposted_posts = [re.original_post for re in reposts]
    
    user_posts = list(Post.objects.filter(author=user_profile.user)) + reposted_posts
    user_posts = sorted(user_posts, key=lambda p: p.created_at, reverse=True)

    context = {
        'user_profile': user_profile,
        'user_posts': user_posts,
        'is_own_profile': request.user == user_profile.user,
        'is_admin_user': request.user.is_staff,
    }
    return render(request, 'users/view_profile.html', context)

