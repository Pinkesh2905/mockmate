from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.contrib import messages
from django.urls import reverse
from django.template.defaultfilters import slugify # For auto-generating slugs

from .models import Article, Comment, Like, Rating

# Corrected import for UserProfile
from users.models import UserProfile
from .forms import ArticleForm, CommentForm, RatingForm

# You might want to move these to a common 'utils' or 'auth_helpers' app later
def is_student(user):
    return user.is_authenticated and hasattr(user, 'userprofile') and user.userprofile.role == 'STUDENT'

def is_tutor(user):
    return user.is_authenticated and hasattr(user, 'userprofile') and user.userprofile.role == 'TUTOR' and user.userprofile.is_approved_tutor

def is_admin(user):
    return user.is_authenticated and user.is_superuser


# --- Public/Student Facing Views ---
@login_required(login_url='practice:login') # Ensure login_url is consistent
def article_list(request):
    """
    Displays a list of all PUBLISHED articles for students.
    """
    articles = Article.objects.filter(status='PUBLISHED').order_by('-created_at')
    return render(request, 'articles/article_list.html', {'articles': articles})

@login_required(login_url='practice:login') # Ensure login_url is consistent
def article_detail(request, slug):
    """
    Displays a single PUBLISHED article and handles comments, likes, and ratings.
    """
    article = get_object_or_404(Article, slug=slug, status='PUBLISHED')
    comments = article.comments.all().order_by('created_at')
    
    # Check if user has already liked the article
    user_has_liked = Like.objects.filter(article=article, user=request.user).exists()
    
    # Get user's existing rating if any
    user_rating_obj = Rating.objects.filter(article=article, user=request.user).first()
    user_rating = user_rating_obj.score if user_rating_obj else 0

    comment_form = CommentForm()
    rating_form = RatingForm()

    context = {
        'article': article,
        'comments': comments,
        'comment_form': comment_form,
        'rating_form': rating_form,
        'user_has_liked': user_has_liked,
        'user_rating': user_rating,
    }
    return render(request, 'articles/article_detail.html', context)


@login_required(login_url='practice:login') # Ensure login_url is consistent
@csrf_exempt
def add_comment(request, slug):
    """
    Handles adding a new comment to an article via AJAX.
    """
    if request.method == 'POST':
        article = get_object_or_404(Article, slug=slug, status='PUBLISHED')
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.article = article
            comment.user = request.user
            comment.save()
            return JsonResponse({
                'success': True,
                'username': request.user.username,
                'content': comment.content,
                'created_at': timezone.localtime(comment.created_at).strftime('%b %d, %Y %H:%M')
            })
        else:
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)


@login_required(login_url='practice:login') # Ensure login_url is consistent
@csrf_exempt
def toggle_like(request, slug):
    """
    Handles liking/unliking an article via AJAX.
    """
    if request.method == 'POST':
        article = get_object_or_404(Article, slug=slug, status='PUBLISHED')
        liked = False
        try:
            like = Like.objects.get(article=article, user=request.user)
            like.delete()
            liked = False
            messages.info(request, "Article unliked.")
        except Like.DoesNotExist:
            Like.objects.create(article=article, user=request.user)
            liked = True
            messages.success(request, "Article liked!")
        
        return JsonResponse({'success': True, 'liked': liked, 'total_likes': article.total_likes})
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)


@login_required(login_url='practice:login') # Ensure login_url is consistent
@csrf_exempt
def submit_rating(request, slug):
    """
    Handles submitting/updating an article rating via AJAX.
    """
    if request.method == 'POST':
        article = get_object_or_404(Article, slug=slug, status='PUBLISHED')
        score = request.POST.get('score')
        
        if not score or not score.isdigit() or not (1 <= int(score) <= 5):
            return JsonResponse({'success': False, 'error': 'Invalid score provided.'}, status=400)
        
        try:
            rating = Rating.objects.get(article=article, user=request.user)
            rating.score = int(score)
            rating.save()
            messages.success(request, "Your rating has been updated.")
        except Rating.DoesNotExist:
            Rating.objects.create(article=article, user=request.user, score=int(score))
            messages.success(request, "Thanks for your rating!")
        
        return JsonResponse({'success': True, 'average_rating': article.average_rating})
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)


# --- Tutor/Staff Specific Views ---
@login_required(login_url='practice:login')
@user_passes_test(is_tutor, login_url='practice:login')
def tutor_article_list(request):
    """
    Tutor's view to manage their own articles (draft, pending, published).
    """
    articles = Article.objects.filter(created_by=request.user).order_by('status', '-created_at')
    return render(request, 'articles/tutor/my_articles.html', {'articles': articles})

@login_required(login_url='practice:login')
@user_passes_test(is_tutor, login_url='practice:login')
def article_create_edit(request, slug=None):
    """
    Allows tutors to create new articles or edit their existing ones.
    New articles default to PENDING_APPROVAL.
    """
    article = None
    if slug:
        article = get_object_or_404(Article, slug=slug, created_by=request.user) # Tutors can only edit their own

    if request.method == 'POST':
        form = ArticleForm(request.POST, instance=article)
        if form.is_valid():
            new_article = form.save(commit=False)
            if not article: # If creating a new article
                new_article.created_by = request.user
                new_article.status = 'PENDING_APPROVAL' # Default status for new tutor articles
            new_article.save()
            messages.success(request, f'Article "{new_article.title}" saved successfully. It is now pending admin approval.')
            return redirect('articles:tutor_article_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ArticleForm(instance=article)

    context = {
        'form': form,
        'article': article,
        'is_new': article is None
    }
    return render(request, 'articles/tutor/article_create_edit.html', context)


# --- Admin Specific Views ---
@login_required(login_url='practice:login')
@user_passes_test(is_admin, login_url='practice:login')
def admin_article_approval(request, article_slug, action):
    """
    Admin action to approve, reject, or archive an article.
    """
    article = get_object_or_404(Article, slug=article_slug)

    if action == 'publish':
        article.status = 'PUBLISHED'
        messages.success(request, f'Article "{article.title}" has been published.')
    elif action == 'reject':
        article.status = 'DRAFT' # Move back to draft for tutor to revise
        messages.warning(request, f'Article "{article.title}" has been moved back to draft status.')
    elif action == 'archive':
        article.status = 'ARCHIVED'
        messages.info(request, f'Article "{article.title}" has been archived.')
    else:
        messages.error(request, 'Invalid action.')
        return redirect('practice:admin_dashboard') # Redirect to practice admin dashboard for now

    article.save()
    return redirect('practice:admin_dashboard') # Redirect to admin dashboard
