from django import template
from django.utils.html import format_html

from leave.permissions import is_hr as _is_hr

register = template.Library()

STATUS_ICONS = {
    "Pending": "bi-hourglass-split",
    "Approved": "bi-check-circle-fill",
    "Rejected": "bi-x-circle-fill",
    "Cancelled": "bi-slash-circle-fill",
}


@register.filter
def is_hr(user):
    return _is_hr(user)


@register.filter
def first_name(full_name):
    parts = str(full_name or "").split()
    return parts[0] if parts else ""


@register.filter
def initials(full_name):
    parts = str(full_name or "").split()
    return "".join(p[0] for p in parts[:2]).upper() or "?"


@register.simple_tag
def status_badge(status):
    icon = STATUS_ICONS.get(status, "bi-circle-fill")
    return format_html(
        '<span class="status status-{}"><i class="bi {}" aria-hidden="true"></i>{}</span>',
        str(status).lower(), icon, status,
    )


@register.simple_tag
def date_range(start, end):
    """'4 May 2027', '4–6 May 2027', '28 Apr – 3 May 2027' or the full form across years."""
    if start == end:
        return f"{start.day} {start:%b %Y}"
    if start.year == end.year and start.month == end.month:
        return f"{start.day}\u2013{end.day} {end:%b %Y}"
    if start.year == end.year:
        return f"{start.day} {start:%b} \u2013 {end.day} {end:%b %Y}"
    return f"{start.day} {start:%b %Y} \u2013 {end.day} {end:%b %Y}"


@register.simple_tag(takes_context=True)
def page_url(context, page_number):
    """Link to another page of a list while keeping the current filters."""
    query = context["request"].GET.copy()
    query["page"] = page_number
    return "?" + query.urlencode()


@register.filter
def add_class(field, css):
    existing = field.field.widget.attrs.get("class", "")
    return field.as_widget(attrs={"class": f"{existing} {css}".strip()})


@register.simple_tag(takes_context=True)
def nav_active(context, *names):
    match = getattr(context["request"], "resolver_match", None)
    return "active" if match and match.url_name in names else ""
