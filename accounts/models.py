from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class Role(models.TextChoices):
    ADMIN = 'administrateur', 'Administrateur Système'
    DIRECTEUR = 'directeur', 'Directeur de Prison'
    GREFFIER = 'greffier', 'Greffier en Chef'
    AGENT = 'agent_penitentiaire', 'Agent Pénitentiaire'
    VISITES = 'responsable_visites', 'Responsable des Visites'


class StatutUser(models.TextChoices):
    ACTIF = 'actif', 'Actif'
    INACTIF = 'inactif', 'Inactif'


ROLE_BADGES = {
    Role.ADMIN: 'bg-danger',
    Role.DIRECTEUR: 'bg-primary',
    Role.GREFFIER: 'bg-info text-dark',
    Role.AGENT: 'bg-secondary',
    Role.VISITES: 'bg-success',
}


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError('Email obligatoire')
        email = self.normalize_email(email)
        import random
        matricule = extra.pop('matricule', None) or f'USR-{random.randint(1000, 9999)}'
        while self.model.objects.filter(matricule=matricule).exists():
            matricule = f'USR-{random.randint(1000, 9999)}'
        user = self.model(email=email, matricule=matricule, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault('role', Role.ADMIN)
        extra.setdefault('statut', StatutUser.ACTIF)
        extra.setdefault('is_staff', True)
        extra.setdefault('is_superuser', True)
        extra.setdefault('nom', extra.get('nom', 'Admin'))
        extra.setdefault('prenom', extra.get('prenom', 'Systeme'))
        return self.create_user(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    matricule = models.CharField(max_length=50, unique=True)
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    email = models.EmailField(max_length=150, unique=True)
    role = models.CharField(max_length=30, choices=Role.choices, default=Role.AGENT)
    statut = models.CharField(max_length=20, choices=StatutUser.choices, default=StatutUser.ACTIF)
    telephone = models.CharField(max_length=30, blank=True, null=True)
    photo = models.CharField(max_length=255, default='default_avatar.png')
    derniere_connexion = models.DateTimeField(blank=True, null=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nom', 'prenom']

    class Meta:
        db_table = 'users'
        ordering = ['nom', 'prenom']

    def __str__(self):
        return f'{self.prenom} {self.nom}'

    @property
    def full_name(self):
        return f'{self.prenom} {self.nom}'

    @property
    def role_label(self):
        return self.get_role_display()

    @property
    def role_badge(self):
        return ROLE_BADGES.get(self.role, 'bg-secondary')

    def has_role(self, *roles):
        return self.role in roles

    def is_admin(self):
        return self.role == Role.ADMIN

    def can_write_detenus(self):
        return self.role in (Role.ADMIN, Role.DIRECTEUR, Role.GREFFIER)

    def can_write_transferts(self):
        return self.role in (Role.ADMIN, Role.DIRECTEUR)

    def can_write_visites(self):
        return self.role in (
            Role.ADMIN, Role.DIRECTEUR, Role.GREFFIER,
            Role.AGENT, Role.VISITES,
        )

    def can_manage_users(self):
        return self.role == Role.ADMIN

    def can_view_audit(self):
        return self.role in (Role.ADMIN, Role.DIRECTEUR)

    def can_backup(self):
        return self.role == Role.ADMIN
