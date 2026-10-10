from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import Role, User
from prison.models import Cellule, Detenu


class DemoViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('views@example.invalid', 'Test-only-password!', nom='Test', prenom='Admin', role=Role.ADMIN)
        self.cell = Cellule.objects.create(code_cellule='VIEW-C01', pavillon='A', bloc='A', capacite_max=30)
        Cellule.objects.create(code_cellule='MAINT-C01', pavillon='B', bloc='B', capacite_max=40, statut='maintenance')
        Detenu.objects.bulk_create([Detenu(matricule=f'TEST-{i:04}', nom='Nom & test', prenom='Demo', date_naissance='1990-01-01', lieu_naissance='Kinshasa', motif_inculpation='Dossier fictif', cellule=self.cell, created_by=self.user) for i in range(26)])
        Detenu.objects.create(matricule='LIBERE', nom='Libéré', prenom='Demo', date_naissance='1990-01-01', lieu_naissance='Kinshasa', motif_inculpation='Fictif', created_by=self.user, statut_judiciaire='libere')
        self.client.force_login(self.user)

    def test_dashboard_counts_present_people_and_renders_accessible_charts(self):
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.context['totalDetenus'], 26)
        self.assertEqual(response.context['capaciteTotale'], 30)
        self.assertEqual(response.context['tauxOccupation'], 86.7)
        self.assertTrue(response.context['by_statut'])
        self.assertTrue(response.context['by_danger'])

    def test_pagination_preserves_encoded_filters(self):
        response = self.client.get(reverse('prison:detenus'), {'search': 'Nom & test', 'page': 2})
        self.assertEqual(response.context['page_obj'].number, 2)
        self.assertEqual(len(response.context['page_obj']), 11)
        self.assertEqual(response.context['pagination_query'], 'search=Nom+%26+test')

    def test_list_pages_render_and_default_photo_has_fallback(self):
        for name in ['prison:jugements', 'prison:visites', 'prison:documents', 'prison:transferts', 'prison:cellules', 'core:reports', 'core:audit']:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
        response = self.client.get(reverse('core:media_photo', args=['default_detenu.png']))
        self.assertEqual(response.status_code, 200)

    def test_health_and_demo_startup_opt_out(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse('core:health')).json()['status'], 'ok')
        with override_settings(DEMO_MODE=False), patch('core.management.commands.prepare_demo.call_command') as seed:
            call_command('prepare_demo', stdout=StringIO())
            seed.assert_not_called()
