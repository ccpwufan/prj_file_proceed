import markdown as md
from django import template
from django.utils.safestring import mark_safe
from django.template.defaultfilters import stringfilter

register = template.Library()

@register.filter
@stringfilter
def markdown(value):
    """
    Convert markdown string to HTML
    """
    # Configure markdown extensions
    extensions = [
        'markdown.extensions.fenced_code',
        'markdown.extensions.codehilite',
        'markdown.extensions.tables',
        'markdown.extensions.toc',
        'markdown.extensions.nl2br',
    ]
    
    # Convert markdown to HTML
    html = md.markdown(value, extensions=extensions)
    
    return mark_safe(html)