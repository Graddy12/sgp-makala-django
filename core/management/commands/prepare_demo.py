from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Recharge les données fictives au démarrage quand DEMO_MODE est actif.'

    def handle(self, *args, **options):
        if settings.DEMO_MODE:
            call_command('seed_demo', stdout=self.stdout, stderr=self.stderr)
