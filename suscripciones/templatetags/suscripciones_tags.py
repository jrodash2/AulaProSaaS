from django import template

register = template.Library()


@register.filter
def in_values(value, values):
    return str(value) in {str(item) for item in (values or [])}
