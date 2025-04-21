from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()

@register.filter
@stringfilter
def capitalize_name(value):
    """
    Capitalizes each word in a name string, handling special cases like 'Mc' and 'Mac'
    """
    if not value:
        return value
    
    # Split the name into parts
    parts = value.split()
    capitalized_parts = []
    
    for part in parts:
        # Handle special cases
        if part.lower().startswith('mc') and len(part) > 2:
            capitalized_parts.append('Mc' + part[2:].capitalize())
        elif part.lower().startswith('mac') and len(part) > 3:
            capitalized_parts.append('Mac' + part[3:].capitalize())
        else:
            capitalized_parts.append(part.capitalize())
    
    return ' '.join(capitalized_parts) 