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