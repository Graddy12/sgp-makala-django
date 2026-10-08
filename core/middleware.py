from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect

from accounts.models import StatutUser


class ActiveUserMiddleware:
    """Invalidate session if user became inactive."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            if user.statut != StatutUser.ACTIF or not user.is_active:
                logout(request)
                messages.error(request, "Votre session n'est plus valide. Veuillez vous reconnecter.")
                return redirect('accounts:login')
        return self.get_response(request)
