# mock_interview/templatetags/form_filters.py

from django import template
from django.template.defaultfilters import stringfilter
import re

register = template.Library()

@register.filter
@stringfilter
def split(value, delimiter=','):
    """
    Split a string by delimiter and return a list.
    Usage: {{ "apple,banana,cherry"|split:"," }}
    """
    if not value:
        return []
    return [item.strip() for item in value.split(delimiter) if item.strip()]

@register.filter
@stringfilter
def trim_whitespace(value):
    """
    Remove leading and trailing whitespace from a string.
    Usage: {{ "  hello world  "|trim_whitespace }}
    """
    return value.strip() if value else ""

@register.filter
def get_item(dictionary, key):
    """
    Get an item from a dictionary using a variable key.
    Usage: {{ mydict|get_item:dynamic_key }}
    """
    return dictionary.get(key) if dictionary else None

@register.filter
def percentage(value, total):
    """
    Calculate percentage of value relative to total.
    Usage: {{ score|percentage:100 }}
    """
    try:
        return round((float(value) / float(total)) * 100, 1) if total != 0 else 0
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter
def duration_format(seconds):
    """
    Format duration in seconds to human-readable format.
    Usage: {{ 3661|duration_format }} -> "1h 1m 1s"
    """
    try:
        seconds = int(float(seconds))
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        parts = []
        if hours:
            parts.append(f"{hours}h")
        if minutes:
            parts.append(f"{minutes}m")
        if seconds or not parts:
            parts.append(f"{seconds}s")
        
        return " ".join(parts)
    except (ValueError, TypeError):
        return "0s"

@register.filter
def json_parse(value):
    """
    Parse JSON string to Python object.
    Usage: {{ json_string|json_parse }}
    """
    import json
    try:
        return json.loads(value) if value else {}
    except (json.JSONDecodeError, TypeError):
        return {}

@register.filter
def skill_color(skill):
    """
    Assign color class based on skill type for better UI.
    Usage: {{ skill|skill_color }}
    """
    skill_lower = skill.lower().strip()
    
    # Technical skills
    tech_skills = ['python', 'javascript', 'java', 'react', 'django', 'node.js', 'sql', 'html', 'css']
    if any(tech in skill_lower for tech in tech_skills):
        return 'skill-tech'
    
    # Soft skills
    soft_skills = ['communication', 'leadership', 'teamwork', 'management', 'problem-solving']
    if any(soft in skill_lower for soft in soft_skills):
        return 'skill-soft'
    
    # Design skills
    design_skills = ['design', 'ui', 'ux', 'photoshop', 'illustrator', 'figma']
    if any(design in skill_lower for design in design_skills):
        return 'skill-design'
    
    return 'skill-default'

@register.filter
def truncate_smart(value, length=100):
    """
    Truncate text at word boundaries, not mid-word.
    Usage: {{ long_text|truncate_smart:50 }}
    """
    if not value or len(value) <= length:
        return value
    
    truncated = value[:length]
    # Find the last space to avoid cutting words
    last_space = truncated.rfind(' ')
    if last_space > 0:
        truncated = truncated[:last_space]
    
    return truncated + "..."

@register.filter
def score_grade(score):
    """
    Convert numeric score to letter grade.
    Usage: {{ 85|score_grade }} -> "B+"
    """
    try:
        score = float(score)
        if score >= 97:
            return "A+"
        elif score >= 93:
            return "A"
        elif score >= 90:
            return "A-"
        elif score >= 87:
            return "B+"
        elif score >= 83:
            return "B"
        elif score >= 80:
            return "B-"
        elif score >= 77:
            return "C+"
        elif score >= 73:
            return "C"
        elif score >= 70:
            return "C-"
        elif score >= 67:
            return "D+"
        elif score >= 65:
            return "D"
        else:
            return "F"
    except (ValueError, TypeError):
        return "N/A"

@register.filter
def format_number(value):
    """
    Format number with appropriate suffixes (K, M, B).
    Usage: {{ 1500|format_number }} -> "1.5K"
    """
    try:
        num = float(value)
        if abs(num) >= 1000000000:
            return f"{num/1000000000:.1f}B"
        elif abs(num) >= 1000000:
            return f"{num/1000000:.1f}M"
        elif abs(num) >= 1000:
            return f"{num/1000:.1f}K"
        else:
            return str(int(num)) if num.is_integer() else f"{num:.1f}"
    except (ValueError, TypeError):
        return str(value)

@register.filter
def multiply(value, arg):
    """
    Multiply two values.
    Usage: {{ score|multiply:3.6 }}
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def divide(value, arg):
    """
    Divide two values.
    Usage: {{ total|divide:count }}
    """
    try:
        return float(value) / float(arg) if float(arg) != 0 else 0
    except (ValueError, TypeError):
        return 0

@register.filter
def add_class(field, css_class):
    """
    Add CSS class to form field.
    Usage: {{ form.field|add_class:"form-control" }}
    """
    try:
        existing_classes = field.field.widget.attrs.get('class', '')
        field.field.widget.attrs['class'] = f"{existing_classes} {css_class}".strip()
        return field
    except AttributeError:
        return field

@register.filter
def confidence_level(score):
    """
    Convert numeric confidence score to descriptive level.
    Usage: {{ 85|confidence_level }} -> "High"
    """
    try:
        score = float(score)
        if score >= 90:
            return "Excellent"
        elif score >= 80:
            return "High"
        elif score >= 70:
            return "Good"
        elif score >= 60:
            return "Fair"
        elif score >= 50:
            return "Developing"
        else:
            return "Needs Improvement"
    except (ValueError, TypeError):
        return "Unknown"

@register.simple_tag
def interview_progress_color(current, total):
    """
    Get color based on interview progress.
    Usage: {% interview_progress_color current_question total_questions %}
    """
    try:
        progress = (current / total) * 100
        if progress < 30:
            return "#ef4444"  # Red
        elif progress < 70:
            return "#f59e0b"  # Amber
        else:
            return "#10b981"  # Green
    except (ValueError, TypeError, ZeroDivisionError):
        return "#6b7280"  # Gray

@register.simple_tag
def skill_icon(skill):
    """
    Get appropriate icon for a skill.
    Usage: {% skill_icon "Python" %}
    """
    skill_lower = skill.lower().strip()
    
    icon_map = {
        'python': 'fab fa-python',
        'javascript': 'fab fa-js-square',
        'react': 'fab fa-react',
        'node.js': 'fab fa-node-js',
        'html': 'fab fa-html5',
        'css': 'fab fa-css3-alt',
        'git': 'fab fa-git-alt',
        'github': 'fab fa-github',
        'docker': 'fab fa-docker',
        'aws': 'fab fa-aws',
        'communication': 'fas fa-comments',
        'leadership': 'fas fa-users',
        'management': 'fas fa-tasks',
        'design': 'fas fa-palette',
        'analytics': 'fas fa-chart-line',
        'database': 'fas fa-database',
    }
    
    # Check for exact matches first
    for key, icon in icon_map.items():
        if key in skill_lower:
            return icon
    
    # Default icon
    return 'fas fa-cog'

# Date and time filters
@register.filter
def time_ago(value):
    """
    Format datetime to human-readable 'time ago' format.
    Usage: {{ created_at|time_ago }}
    """
    from django.utils import timezone
    from datetime import datetime, timedelta
    
    try:
        if isinstance(value, str):
            value = datetime.fromisoformat(value.replace('Z', '+00:00'))
        
        now = timezone.now()
        if value.tzinfo is None:
            value = timezone.make_aware(value)
        
        diff = now - value
        
        if diff.days > 7:
            return value.strftime('%b %d, %Y')
        elif diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "Just now"
    except (ValueError, TypeError, AttributeError):
        return str(value)

@register.filter
def status_badge(status):
    """
    Get appropriate badge class for status.
    Usage: {{ interview.status|status_badge }}
    """
    status_classes = {
        'STARTED': 'badge-warning',
        'COMPLETED': 'badge-success',
        'REVIEWED': 'badge-info',
        'PENDING': 'badge-secondary',
        'CANCELLED': 'badge-danger',
    }
    return status_classes.get(status, 'badge-secondary')

from django import template

register = template.Library()

@register.filter
def split(value, delimiter=','):
    """Split a string by delimiter and return a list"""
    if not value:
        return []
    return [item.strip() for item in value.split(delimiter) if item.strip()]

@register.filter
def trim(value):
    """Remove leading and trailing whitespace"""
    if not value:
        return ''
    return value.strip()
