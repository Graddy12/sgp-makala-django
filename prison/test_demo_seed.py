"""Regression checks for non-destructive reconstruction of the demo dataset."""
from datetime import timedelta
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.models import Role, User
from core.models import AuditLog, Notification
from prison.models import Cellule, Detenu, DocumentJudiciaire, Jugement, Transfert, Visite


class DemoSeedTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.media_directory = TemporaryDirectory(prefix='sgp-demo-seed-test-')
        cls.media_override = override_settings(MEDIA_ROOT=cls.media_directory.name)
        cls.media_override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.media_override.disable()
        cls.media_directory.cleanup()

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(
            email=settings.SGP_ADMIN_EMAIL, password='OnlyForSeedTests!2026',
            nom='Administrateur', prenom='Test', matricule='TEST-ADMIN',
        )
        call_command('seed_demo', stdout=StringIO())

    def seed(self):
        call_command('seed_demo', stdout=StringIO())

    @staticmethod
    def counts():
        return tuple(model.objects.count() for model in (
            User, Cellule, Detenu, Jugement, Visite, Transfert, DocumentJudiciaire,
            AuditLog, Notification,
        ))

    def test_dataset_is_populated_consistent_and_fictional(self):
        self.assertEqual(self.counts(), (9, 20, 120, 47, 216, 12, 179, 126, 3))
        self.assertEqual(Detenu.objects.filter(statut_judiciaire__in=['prevenu', 'condamne']).count(), 108)
        self.assertEqual(sum(Cellule.objects.values_list('capacite_max', flat=True)), 144)
        self.assertEqual(set(User.objects.values_list('role', flat=True)), set(Role.values))
        for user in User.objects.exclude(pk=self.admin.pk):
            self.assertFalse(user.has_usable_password())
            self.assertFalse(user.is_superuser)
        today = timezone.localdate()
        for person in Detenu.objects.all():
            age = today.year - person.date_naissance.year - ((today.month, today.day) < (person.date_naissance.month, person.date_naissance.day))
            self.assertGreaterEqual(age, 18)
            self.assertIn('fictif', person.motif_inculpation)
            self.assertTrue((Path(settings.MEDIA_ROOT) / 'photos' / person.photo).is_file())
            if person.statut_judiciaire == 'condamne':
                self.assertGreater(person.date_liberation_prevue, today)
            if person.statut_judiciaire in ('transfere', 'libere', 'archive'):
                self.assertIsNone(person.cellule_id)
        for cell in Cellule.objects.all():
            self.assertLessEqual(cell.occupation, cell.capacite_max)
            if cell.statut == 'pleine':
                self.assertEqual(cell.occupation, cell.capacite_max)
            if cell.statut == 'maintenance':
                self.assertEqual(cell.occupation, 0)
        for doc in DocumentJudiciaire.objects.all():
            path = Path(settings.MEDIA_ROOT) / 'documents' / doc.fichier_path
            self.assertTrue(path.read_bytes().startswith(b'%PDF-'))
            self.assertGreater(doc.taille_ko, 0)
            self.assertIn('ficti', doc.description)

    def test_reloading_preserves_records_and_user_changes(self):
        initial_counts = self.counts()
        admin_password = self.admin.password
        person = Detenu.objects.get(pk=900001)
        old_ecrou = person.date_ecrou
        Detenu.objects.filter(pk=person.pk).update(nom='MODIFIÉ PENDANT LA DÉMO', matricule='DEMO-MODIFIE', photo='photo_utilisateur.jpg')
        Cellule.objects.filter(pk=900002).update(code_cellule='CELLULE-MODIFIEE', description='Modifiée par le présentateur')
        Jugement.objects.filter(pk=900001).update(numero_dossier='REFERENCE-MODIFIEE', resume_verdict='Texte corrigé')
        Visite.objects.filter(pk=900001).update(numero_piece='PIECE-MODIFIEE', statut='refusee')
        Transfert.objects.filter(pk=900001).update(notes='Notes modifiées', statut='annule')
        DocumentJudiciaire.objects.filter(pk=900001).update(fichier_path='document_utilisateur.pdf', titre='Titre modifié')
        AuditLog.objects.filter(pk=900001).update(description='Description modifiée')
        Notification.objects.filter(pk=900001).update(titre='Titre modifié', is_read=True)
        staff = User.objects.get(pk=900001)
        staff.set_password('AgentConfiguredDuringDemo!2026')
        staff.save(update_fields=['password'])
        staff_password = staff.password

        # Advancing the restart date must not move an existing record's dates.
        with patch('prison.management.commands.seed_demo.timezone.localdate', return_value=timezone.localdate() + timedelta(days=10)):
            self.seed()

        self.assertEqual(self.counts(), initial_counts)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.password, admin_password)
        person.refresh_from_db()
        self.assertEqual(person.nom, 'MODIFIÉ PENDANT LA DÉMO')
        self.assertEqual(person.matricule, 'DEMO-MODIFIE')
        self.assertEqual(person.photo, 'photo_utilisateur.jpg')
        self.assertEqual(person.date_ecrou, old_ecrou)
        self.assertEqual(Cellule.objects.get(pk=900002).code_cellule, 'CELLULE-MODIFIEE')
        self.assertEqual(Jugement.objects.get(pk=900001).numero_dossier, 'REFERENCE-MODIFIEE')
        self.assertEqual(Visite.objects.get(pk=900001).statut, 'refusee')
        self.assertEqual(Transfert.objects.get(pk=900001).notes, 'Notes modifiées')
        self.assertEqual(DocumentJudiciaire.objects.get(pk=900001).fichier_path, 'document_utilisateur.pdf')
        self.assertEqual(AuditLog.objects.get(pk=900001).description, 'Description modifiée')
        self.assertTrue(Notification.objects.get(pk=900001).is_read)
        staff.refresh_from_db()
        self.assertEqual(staff.password, staff_password)

    def test_reloading_restores_only_missing_demo_files(self):
        portrait = Path(settings.MEDIA_ROOT) / 'photos' / Detenu.objects.get(pk=900001).photo
        document = Path(settings.MEDIA_ROOT) / 'documents' / DocumentJudiciaire.objects.get(pk=900002).fichier_path
        preserved = Path(settings.MEDIA_ROOT) / 'documents' / DocumentJudiciaire.objects.get(pk=900003).fichier_path
        expected_portrait = portrait.read_bytes()
        expected_document = document.read_bytes()
        original_preserved = preserved.read_bytes()
        portrait.unlink()
        document.unlink()
        try:
            preserved.write_bytes(b'PDF edited during the demo')
            self.seed()
            self.assertEqual(portrait.read_bytes(), expected_portrait)
            self.assertEqual(document.read_bytes(), expected_document)
            self.assertEqual(preserved.read_bytes(), b'PDF edited during the demo')
        finally:
            preserved.write_bytes(original_preserved)

    def test_dry_run_does_not_write(self):
        initial_counts = self.counts()
        output = StringIO()
        call_command('seed_demo', dry_run=True, stdout=output)
        self.assertEqual(self.counts(), initial_counts)
        self.assertIn('detenus=120', output.getvalue())


class DemoSeedPreconditionsTests(TestCase):
    def test_missing_admin_explains_bootstrap_without_seeding(self):
        with self.assertRaisesMessage(CommandError, 'bootstrap_admin'):
            call_command('seed_demo', stdout=StringIO())
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(Detenu.objects.count(), 0)
        self.assertEqual(Cellule.objects.count(), 0)
