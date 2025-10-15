from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Prefetch, Count
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import Post, Comment, Like, Repost
from .forms import PostForm, CommentForm
from users.models import UserProfile


@login_required
def feed_view(request):
    """
    Enhanced feed view with optimized queries
    """
    # Optimize queries with select_related and prefetch_related
    posts = Post.objects.select_related(
        'author', 
        'author__profile'
    ).prefetch_related(
        Prefetch('comments', queryset=Comment.objects.select_related('author')),
        Prefetch('likes', queryset=Like.objects.select_related('user')),
        'reposts'
    ).annotate(
        like_count=Count('likes'),
        comment_count=Count('comments')
    ).order_by('-created_at')

    if request.method == 'POST':
        post_form = PostForm(request.POST, request.FILES)
        if post_form.is_valid():
            post = post_form.save(commit=False)
            post.author = request.user
            post.save()
            messages.success(request, "Post shared successfully!")
            return redirect('posts:feed')
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


@login_required
@require_POST
def toggle_like(request, post_id):
    """
    Toggle like/unlike with AJAX support
    """
    post = get_object_or_404(Post, id=post_id)
    like, created = Like.objects.get_or_create(post=post, user=request.user)

    if not created:
        like.delete()
        liked = False
    else:
        liked = True

    like_count = post.likes.count()
    
    return JsonResponse({
        'liked': liked, 
        'like_count': like_count,
        'success': True
    })


@login_required
@require_POST
def add_comment(request, post_id):
    """
    Add comment with parent comment support (nested replies)
    """
    post = get_object_or_404(Post, id=post_id)
    parent_id = request.POST.get('parent_id')
    parent_comment = None
    
    if parent_id:
        parent_comment = get_object_or_404(Comment, id=parent_id, post=post)

    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.author = request.user
        comment.parent = parent_comment
        comment.save()
        messages.success(request, "Comment added successfully.")
    else:
        messages.error(request, "Failed to add comment. " + str(form.errors))
    
    return redirect('posts:feed')


@login_required
@require_POST
def repost(request, post_id):
    """
    Enhanced repost functionality - tracks reposts without duplicating posts
    """
    original_post = get_object_or_404(Post, id=post_id)

    # Prevent reposting own posts
    if original_post.author == request.user:
        messages.warning(request, "You cannot repost your own post.")
        return redirect('posts:feed')

    # Check for duplicate repost
    repost_obj, created = Repost.objects.get_or_create(
        original_post=original_post,
        user=request.user,
        defaults={'comment': ''}
    )

    if not created:
        messages.warning(request, "You have already reposted this.")
    else:
        messages.success(request, "Post reposted to your profile.")

    return redirect('posts:feed')


@login_required
def edit_post(request, post_id):
    """
    Edit post - only author can edit
    """
    post = get_object_or_404(Post, id=post_id, author=request.user)
    
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, "Post updated successfully.")
            return redirect('posts:feed')
        else:
            messages.error(request, "Error updating post.")
    else:
        form = PostForm(instance=post)
    
    return render(request, 'posts/edit_post.html', {'form': form, 'post': post})


@login_required
@require_POST
def delete_post(request, post_id):
    """
    Delete post - only author can delete
    """
    post = get_object_or_404(Post, id=post_id, author=request.user)
    post.delete()
    messages.success(request, "Post deleted successfully.")
    return redirect('posts:feed')


@login_required
def view_post_modal(request, post_id):
    """
    View post in modal with optimized queries
    """
    post = get_object_or_404(
        Post.objects.select_related('author', 'author__profile'),
        id=post_id
    )
    
    comments = Comment.objects.filter(
        post=post
    ).select_related(
        'author', 'author__profile'
    ).prefetch_related(
        'replies'
    ).order_by('created_at')
    
    is_liked = False
    if request.user.is_authenticated:
        is_liked = post.is_liked_by(request.user)
    
    return render(request, 'posts/post_modal.html', {
        'post': post,
        'comments': comments,
        'is_liked': is_liked,
    })


@login_required
def post_detail(request, post_id):
    """
    Detailed post view with all interactions
    """
    post = get_object_or_404(
        Post.objects.select_related('author', 'author__profile').prefetch_related(
            Prefetch('comments', queryset=Comment.objects.select_related('author', 'author__profile')),
            'likes',
            'reposts'
        ),
        id=post_id
    )
    
    comment_form = CommentForm()
    
    context = {
        'post': post,
        'comment_form': comment_form,
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def user_profile(request, username):
    """
    Enhanced user profile with posts and reposts
    """
    from users.forms import UserUpdateForm, UserProfileUpdateForm

    profile_user = get_object_or_404(UserProfile, user__username=username)

    # Fetch original posts
    original_posts = Post.objects.filter(
        author=profile_user.user
    ).select_related('author').prefetch_related('likes', 'comments', 'reposts')

    # Fetch reposts
    reposts = Repost.objects.filter(
        user=profile_user.user
    ).select_related('original_post__author', 'user')

    posts = []

    # Add original posts
    for post in original_posts:
        post.is_repost = False
        post.display_time = post.created_at
        posts.append(post)

    # Add reposts
    for repost in reposts:
        post = repost.original_post
        post.is_repost = True
        post.reposted_by = profile_user.user
        post.reposted_at = repost.created_at
        post.display_time = repost.created_at
        posts.append(post)

    # Sort by display time
    posts = sorted(posts, key=lambda p: p.display_time, reverse=True)

    # Check if viewing own profile
    is_own_profile = request.user == profile_user.user

    user_form = profile_form = None
    if is_own_profile:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = UserProfileUpdateForm(instance=profile_user)

    context = {
        'profile_user': profile_user,
        'posts': posts,
        'user_form': user_form,
        'profile_form': profile_form,
        'is_own_profile': is_own_profile,
    }
    return render(request, 'users/view_profile.html', context)


@login_required
def search_results(request):
    """
    Enhanced search with optimized queries
    """
    query = request.GET.get('q', '').strip()
    posts = []
    users = []

    if query:
        # Search posts
        posts = Post.objects.filter(
            Q(content__icontains=query) |
            Q(author__username__icontains=query) |
            Q(hashtags__name__icontains=query)
        ).distinct().select_related(
            'author', 'author__profile'
        ).prefetch_related('likes', 'comments')

        # Search users
        users = UserProfile.objects.filter(
            Q(user__username__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(bio__icontains=query)
        ).select_related('user')

    context = {
        'query': query,
        'posts': posts,
        'users': users,
    }
    return render(request, 'posts/search_results.html', context)