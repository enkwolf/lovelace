import time
from django import template
from datetime import datetime

register = template.Library()

# {% multiple_choice_exercise %}
@register.inclusion_tag("lti/multiple-choice-exercise.html", takes_context=True)
def multiple_choice_exercise(context):
    return context

# {% checkbox_exercise %}
@register.inclusion_tag("lti/checkbox-exercise.html", takes_context=True)
def checkbox_exercise(context):
    return context

# {% textfield_exercise %}
@register.inclusion_tag("lti/textfield-exercise.html", takes_context=True)
def textfield_exercise(context):
    return context

# {% file_upload_exercise %}
@register.inclusion_tag("lti/file-upload-exercise.html", takes_context=True)
def file_upload_exercise(context):
    return context
