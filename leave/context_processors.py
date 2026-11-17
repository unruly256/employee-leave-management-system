from django.utils.functional import SimpleLazyObject

from .permissions import role_of


def navigation(request):
    """Expose the signed-in user's role to every template (evaluated only if the template uses it)."""
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}
    return {"nav_role": SimpleLazyObject(lambda: role_of(user))}
