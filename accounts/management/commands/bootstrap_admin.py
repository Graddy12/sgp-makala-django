from django.conf import settings
from django.core.management.base import BaseCommand

from accounts.models import Role, StatutUser, User


class Command(BaseCommand):
    help = 'Crée le compte administrateur initial depuis .env'

    def handle(self, *args, **options):
        email = settings.SGP_ADMIN_EMAIL
        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.WARNING(f'Admin {email} existe déjà.'))
            return
        user = User.objects.create_user(
            email=email,
            password=settings.SGP_ADMIN_PASSWORD,
            nom=settings.SGP_ADMIN_NOM,
            prenom=settings.SGP_ADMIN_PRENOM,
            telephone=settings.SGP_ADMIN_TELEPHONE or None,
            role=Role.ADMIN,
            statut=StatutUser.ACTIF,
            is_staff=True,
            is_superuser=True,
        )
        self.stdout.write(self.style.SUCCESS(
            f'Admin créé : {user.email} ({user.matricule})'
        ))
