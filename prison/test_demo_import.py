import json
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import Role, User
from core.models import AuditLog
from prison.models import Cellule, Detenu


@override_settings(DEMO_MODE=True)
class DemoImportTests(TestCase):
    def setUp(self):
        self.media = tempfile.TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        override = override_settings(MEDIA_ROOT=self.media.name)
        override.enable()
        self.addCleanup(override.disable)
        self.user = User.objects.create_user('review@example.invalid', 'Test-only-Password!', nom='Test', prenom='Admin', role=Role.ADMIN)
        self.client.force_login(self.user)
        self.payload = json.loads((Path(settings.BASE_DIR) / 'demo' / 'enrollment_day_j.json').read_text(encoding='utf-8'))
        self.cell = Cellule.objects.create(code_cellule=self.payload['detenu']['cellule_code'], pavillon='Démo', bloc='A', capacite_max=5)
        self.url = reverse('prison:detenus_import')

    def preview(self, payload=None):
        upload = SimpleUploadedFile('test.json', json.dumps(payload or self.payload).encode(), content_type='application/json')
        return self.client.post(self.url, {'json_file': upload})

    def test_preview_then_confirm_creates_photo_audit_and_prevents_replay(self):
        response = self.preview()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Detenu.objects.count(), 0)
        token = response.context['token']
        response = self.client.post(self.url, {'action': 'confirm', 'token': token})
        self.assertEqual(response.status_code, 302)
        detenu = Detenu.objects.get()
        self.assertEqual(detenu.cellule, self.cell)
        self.assertTrue((Path(self.media.name) / 'photos' / detenu.photo).exists())
        self.assertEqual(AuditLog.objects.filter(action='IMPORT_DEMO_JSON').count(), 1)
        self.client.post(self.url, {'action': 'confirm', 'token': token})
        self.assertEqual(Detenu.objects.count(), 1)

    def test_confirm_rechecks_cell_capacity(self):
        token = self.preview().context['token']
        self.cell.statut = 'maintenance'
        self.cell.save()
        response = self.client.post(self.url, {'action': 'confirm', 'token': token})
        self.assertContains(response, 'pleine ou en maintenance')
        self.assertFalse(Detenu.objects.exists())

    def test_rejects_tampered_preview_and_untrusted_portrait(self):
        token = self.preview().context['token']
        self.client.post(self.url, {'action': 'confirm', 'token': token + 'tampered'})
        self.assertFalse(Detenu.objects.exists())
        self.payload['detenu']['portrait'] = '../../.env'
        response = self.preview()
        self.assertContains(response, 'portraits fictifs')
        self.assertNotIn('token', response.context)

    def test_rejects_malformed_dates_and_unknown_fields_without_database_write(self):
        for key, value in [('date_naissance', 'not-a-date'), ('genre', 'X'), ('is_superuser', 'true')]:
            payload = json.loads(json.dumps(self.payload))
            payload['detenu'][key] = value
            response = self.preview(payload)
            self.assertEqual(response.status_code, 200)
            self.assertNotIn('token', response.context)
        self.assertFalse(Detenu.objects.exists())

    def test_sample_preview_and_download(self):
        self.assertIn('token', self.client.post(self.url, {'action': 'sample'}).context)
        response = self.client.get(reverse('prison:demo_enrollment_sample'))
        self.assertEqual(json.loads(b''.join(response.streaming_content)), self.payload)

    def test_demo_disabled_and_role_permissions(self):
        with override_settings(DEMO_MODE=False):
            self.assertEqual(self.client.get(self.url).status_code, 404)
        self.user.role = Role.AGENT
        self.user.save()
        self.assertRedirects(self.client.get(self.url), reverse('core:forbidden'), fetch_redirect_response=False)

    def test_manual_enrollment_validates_before_saving(self):
        response = self.client.post(reverse('prison:detenus_create'), {
            'nom': 'TEST', 'prenom': 'Demo', 'date_naissance': 'not-a-date',
            'lieu_naissance': 'Kinshasa', 'motif_inculpation': 'Fictif',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Detenu.objects.exists())
