from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from accounts.models import Role, StatutUser, User
from core.decorators import role_required
from core.utils import log_audit


@require_http_methods(['GET', 'POST'])
def login_view(request):
    if request.user.is_authenticated:
        return redirect('core:dashboard')
    if request.method == 'POST':
        email = (request.POST.get('email') or '').strip().lower()
        password = request.POST.get('password') or ''
        user = authenticate(request, username=email, password=password)
        if user is None:
            messages.error(request, 'Email ou mot de passe incorrect.')
        elif user.statut != StatutUser.ACTIF:
            messages.error(request, 'Compte désactivé. Contactez un administrateur.')
        else:
            login(request, user)
            user.derniere_connexion = timezone.now()
            user.save(update_fields=['derniere_connexion'])
            log_audit(request, 'CONNEXION', 'AUTH', f'Connexion de {user.full_name}')
            messages.success(request, f'Bienvenue, {user.prenom} !')
            return redirect('core:dashboard')
    return render(request, 'accounts/login.html')


@login_required
def logout_view(request):
    log_audit(request, 'DECONNEXION', 'AUTH', f'Déconnexion de {request.user.full_name}')
    logout(request)
    messages.info(request, 'Vous êtes déconnecté.')
    return redirect('accounts:login')


@login_required
def profile_view(request):
    return render(request, 'accounts/profile.html')


@login_required
@require_POST
def profile_password(request):
    current = request.POST.get('current_password') or ''
    new1 = request.POST.get('new_password') or ''
    new2 = request.POST.get('new_password_confirm') or ''
    if not request.user.check_password(current):
        messages.error(request, 'Mot de passe actuel incorrect.')
    elif len(new1) < 8:
        messages.error(request, 'Le nouveau mot de passe doit contenir au moins 8 caractères.')
    elif new1 != new2:
        messages.error(request, 'Les nouveaux mots de passe ne correspondent pas.')
    else:
        request.user.set_password(new1)
        request.user.save()
        update_session_auth_hash(request, request.user)
        log_audit(request, 'CHANGEMENT_MDP', 'PROFILE', 'Mot de passe modifié')
        messages.success(request, 'Mot de passe mis à jour.')
    return redirect('accounts:profile')


@role_required(Role.ADMIN)
def users_list(request):
    users = User.objects.all().order_by('nom', 'prenom')
    return render(request, 'accounts/users_index.html', {'users': users})


@role_required(Role.ADMIN)
@require_http_methods(['GET', 'POST'])
def users_create(request):
    if request.method == 'POST':
        nom = (request.POST.get('nom') or '').strip().upper()
        prenom = (request.POST.get('prenom') or '').strip().capitalize()
        email = (request.POST.get('email') or '').strip().lower()
        role = request.POST.get('role') or Role.AGENT
        telephone = (request.POST.get('telephone') or '').strip()
        password = request.POST.get('password') or ''
        if not all([nom, prenom, email, password]):
            messages.error(request, 'Tous les champs obligatoires doivent être remplis.')
        elif User.objects.filter(email=email).exists():
            messages.error(request, 'Cet email est déjà utilisé.')
        else:
            user = User.objects.create_user(
                email=email, password=password, nom=nom, prenom=prenom,
                role=role, telephone=telephone or None, statut=StatutUser.ACTIF,
                is_staff=(role == Role.ADMIN),
            )
            log_audit(request, 'CREATION_USER', 'USERS', f'Compte créé : {user.email} ({user.role})')
            messages.success(request, f'Utilisateur {user.full_name} créé ({user.matricule}).')
            return redirect('accounts:users')
    return render(request, 'accounts/users_create.html', {'roles': Role.choices})


@role_required(Role.ADMIN)
@require_POST
def users_toggle(request, pk):
    user = User.objects.filter(pk=pk).first()
    if not user:
        messages.error(request, 'Utilisateur introuvable.')
    elif user.pk == request.user.pk:
        messages.error(request, 'Vous ne pouvez pas désactiver votre propre compte.')
    else:
        if user.statut == StatutUser.ACTIF:
            user.statut = StatutUser.INACTIF
            user.is_active = False
            action = 'desactivé'
        else:
            user.statut = StatutUser.ACTIF
            user.is_active = True
            action = 'activé'
        user.save(update_fields=['statut', 'is_active', 'updated_at'])
        log_audit(request, 'TOGGLE_USER', 'USERS', f'Compte {user.email} {action}')
        messages.success(request, f'Compte {user.full_name} {action}.')
    return redirect('accounts:users')
