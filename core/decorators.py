from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def role_required(*roles):
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.has_role(*roles):
                messages.error(request, "Accès refusé : permissions insuffisantes.")
                return redirect('core:forbidden')
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator
