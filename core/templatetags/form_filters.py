from django import template

register = template.Library()

@register.filter(name='add_class')
def add_class(value, arg):
    """
    Adds a CSS class to a form field.
    Usage: {{ field|add_class:"my-class" }}
    """
    return value.as_widget(attrs={'class': arg})

@register.filter(name='add_attr')
def add_attr(field, css):
    """
    Adds an HTML attribute to a form field.
    Usage: {{ field|add_attr:"placeholder:Enter your text" }}
    """
    attrs = {}
    definitions = css.split(',')
    for d in definitions:
        if ':' in d:
            key, value = d.split(':')
            attrs[key] = value
        else:
            attrs[d] = True
    return field.as_widget(attrs=attrs)

@register.filter
def split(value, delimiter):
    """Split a string by delimiter"""
    if value:
        return value.split(delimiter)
    return []

@register.filter
def trim_whitespace(value):
    """
    Removes leading and trailing whitespace from a string.
    """
    if isinstance(value, str):
        return value.strip()
    return value