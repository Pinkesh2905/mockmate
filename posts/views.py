from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse

from .models import Post, Comment, Like, Repost
from .forms import PostForm, CommentForm
from users.models import UserProfile


# --- FEED (with post creation & feed display) ---
@login_required
def feed_view(request):
    posts = Post.objects.select_related('author').prefetch_related('comments', 'likes', 'reposts').order_by('-created_at')

    if request.method == 'POST':
        post_form = PostForm(request.POST, request.FILES)
        if post_form.is_valid():
            post = post_form.save(commit=False)
            post.author = request.user
            post.save()
            messages.success(request, "Post shared successfully!")
            return redirect('posts:feed')  # Prevent form resubmission
        else:
            messages.error(request, "There was an error sharing your post.")
    else:
        post_form = PostForm()

    comment_form = CommentForm()

    context = {
        'posts': posts,
        'post_form': post_form,
        'comment_form': comment_form,
    }
    return render(request, 'posts/feed.html', context)


# --- LIKE / UNLIKE ---
@login_required
def toggle_like(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    like, created = Like.objects.get_or_create(post=post, user=request.user)

    if not created:
        like.delete()
        liked = False
    else:
        liked = True

    return JsonResponse({'liked': liked, 'like_count': post.likes.count()})


# --- ADD COMMENT ---
@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    parent_id = request.POST.get('parent_id')
    parent_comment = Comment.objects.filter(id=parent_id).first() if parent_id else None

    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.author = request.user
            comment.parent = parent_comment
            comment.save()
            messages.success(request, "Comment added.")
        else:
            messages.error(request, "Failed to add comment.")
    return redirect('posts:feed')



# --- REPOST ---
@login_required
def repost(request, post_id):
    original_post = get_object_or_404(Post, id=post_id)

    # Prevent duplicate reposts by same user
    if Repost.objects.filter(original_post=original_post, user=request.user).exists():
        messages.warning(request, "You have already reposted this.")
    else:
        # 1. Create Repost record (for tracking)
        Repost.objects.create(
            original_post=original_post,
            user=request.user,
            comment=""
        )

        # 2. Create actual Post object so it appears in feed
        Post.objects.create(
            author=request.user,
            content=original_post.content,
            image=original_post.image
        )

        messages.success(request, "Post shared to your feed.")

    return redirect('posts:feed')

@login_required
def edit_post(request, post_id):
    post = get_object_or_404(Post, id=post_id, author=request.user)
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, "Post updated.")
            return redirect('posts:feed')
    else:
        form = PostForm(instance=post)
    return render(request, 'posts/edit_post.html', {'form': form, 'post': post})


@login_required
def delete_post(request, post_id):
    post = get_object_or_404(Post, id=post_id, author=request.user)
    if request.method == 'POST':
        post.delete()
        messages.success(request, "Post deleted.")
    return redirect('posts:feed')

@login_required
def view_post_modal(request, post_id):
    post = get_object_or_404(Post.objects.select_related('author__profile'), id=post_id)
    comments = Comment.objects.filter(post=post).select_related('author__profile').order_by('created_at')
    return render(request, 'posts/post_modal.html', {
        'post': post,
        'comments': comments,
    })


# --- USER PROFILE ---
# --- USER PROFILE ---
# posts/views.py

@login_required
def user_profile(request, username):
    from users.forms import UserUpdateForm, UserProfileUpdateForm
    from users.models import UserProfile

    profile_user = get_object_or_404(UserProfile, user__username=username)

    # Fetch both original posts AND reposts
    original_posts = Post.objects.filter(author=profile_user.user)

    # Fetch reposts made by this user
    reposts = Repost.objects.filter(user=profile_user.user).select_related('original_post')

    posts = []

    # Add original posts
    for post in original_posts:
        post.is_repost = False  # Mark explicitly
        posts.append(post)

    # Add reposts
    for repost in reposts:
        post = repost.original_post
        post.is_repost = True
        post.reposted_by = profile_user.user
        post.reposted_at = repost.created_at
        posts.append(post)

    # Sort by time (latest first)
    posts = sorted(posts, key=lambda p: p.created_at if not getattr(p, 'is_repost', False) else p.reposted_at, reverse=True)

    # Is this my profile?
    is_own_profile = request.user == profile_user.user

    if is_own_profile:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = UserProfileUpdateForm(instance=profile_user)
    else:
        user_form = profile_form = None

    return render(request, 'users/view_profile.html', {
        'profile_user': profile_user,
        'posts': posts,
        'user_form': user_form,
        'profile_form': profile_form,
        'is_own_profile': is_own_profile,
    })


# --- SMART SEARCH RESULTS (Deprecated: moved to core/views.py) ---
# Retained for future in-module use if needed
@login_required
def search_results(request):
    query = request.GET.get('q', '').strip()
    posts = users = []

    if query:
        posts = Post.objects.filter(
            Q(content__icontains=query) |
            Q(author__username__icontains=query) |
            Q(hashtags__name__icontains=query)
        ).distinct().select_related('author')

        users = UserProfile.objects.filter(
            Q(user__username__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query)
        ).select_related('user')

    context = {
        'query': query,
        'posts': posts,
        'users': users,
    }
    return render(request, 'posts/search_results.html', context)
