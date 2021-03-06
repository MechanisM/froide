from django import template
from django.utils.safestring import mark_safe
from django.utils.html import escape

from foirequest.models import FoiRequest

from helper.text_utils import unescape

register = template.Library()


def highlight_request(message):
    content = unescape(message.get_content().replace("\r\n", "\n"))
    description = message.request.description
    description = description.replace("\r\n", "\n")
    try:
        index = content.index(description)
    except ValueError:
        return content
    offset = index + len(description)
    return mark_safe('<div class="foldin">%s</div><div class="highlight">%s</div><div class="foldin">%s</div>' % (escape(content[:index]),
            escape(description), escape(content[offset:])))


def check_same_request(context, foirequest, user, var_name):
    same_requests = FoiRequest.objects.filter(user=user, same_as=foirequest)
    if same_requests:
        context[var_name] = same_requests[0]
    else:
        context[var_name] = False
    return ""


register.simple_tag(highlight_request)
register.simple_tag(takes_context=True)(check_same_request)
