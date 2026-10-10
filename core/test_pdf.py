"""Exercise PDF exports with photos, free text and realistic report sizes."""
from datetime import date
from io import BytesIO
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings
from PIL import Image as PILImage
from reportlab.platypus import Paragraph

from accounts.models import User
from core.pdf import _photo_path, fiche_ecrou_pdf, rapport_global_pdf
from prison.models import Detenu, Jugement

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None


def _page_count(content):
    if PdfReader:
        return len(PdfReader(BytesIO(content)).pages)
    # Page dictionaries remain readable even when their drawing streams are compressed.
    return len(re.findall(rb'/Type\s*/Page\b', content))


class DetentionPdfTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.agent = User.objects.create_user(
            email='pdf@example.test', password='test-only', nom='Agent', prenom='Démo',
        )
        cls.detenu = Detenu.objects.create(
            matricule='DEMO-PDF-001', nom='Nom & <fiction>', postnom='Très long postnom', prenom='Personne',
            date_naissance=date(1990, 4, 1), lieu_naissance='Kinshasa & environs <démo>',
            motif_inculpation='Motif fictif : montant < 500 & valeur > 100.\nDeuxième ligne.',
            created_by=cls.agent,
        )

    def test_existing_photo_uses_media_photos_and_is_embedded(self):
        with TemporaryDirectory() as folder, override_settings(MEDIA_ROOT=folder):
            photo_folder = Path(folder) / 'photos'
            photo_folder.mkdir()
            photo_path = photo_folder / 'portrait.jpg'
            PILImage.new('RGB', (60, 80), '#336699').save(photo_path)
            self.detenu.photo = 'portrait.jpg'
            self.assertEqual(_photo_path(self.detenu), photo_path.resolve())
            response = fiche_ecrou_pdf(self.detenu)
            self.assertEqual(response['Content-Type'], 'application/pdf')
            self.assertTrue(response.content.startswith(b'%PDF-'))
            self.assertIn(b'/Subtype /Image', response.content)

    def test_photo_cannot_escape_photos_directory(self):
        with TemporaryDirectory() as folder, override_settings(MEDIA_ROOT=folder):
            outside = Path(folder) / 'outside.jpg'
            PILImage.new('RGB', (20, 20)).save(outside)
            self.assertIsNone(_photo_path(SimpleNamespace(photo='../outside.jpg')))
            self.assertIsNone(_photo_path(SimpleNamespace(photo=str(outside))))

    def test_missing_or_damaged_photo_does_not_block_export(self):
        with TemporaryDirectory() as folder, override_settings(MEDIA_ROOT=folder):
            photos = Path(folder) / 'photos'
            photos.mkdir()
            (photos / 'broken.jpg').write_bytes(b'not an image')
            for photo in ('missing.jpg', 'broken.jpg'):
                with self.subTest(photo=photo):
                    self.detenu.photo = photo
                    self.assertTrue(fiche_ecrou_pdf(self.detenu).content.startswith(b'%PDF-'))

    @override_settings(DEMO_MODE=True)
    def test_judgement_special_characters_and_long_verdict_render_as_text(self):
        verdict = 'Verdict fictif : A & B, preuve <annexe> et montant > 500.\n' * 90
        Jugement.objects.create(
            detenu=self.detenu, tribunal='Tribunal A & B <démonstration>', numero_dossier='RP <123> & 456',
            date_jugement=date(2026, 1, 12), type_decision='condamnation', peine_ans=2,
            peine_amende='125.00', resume_verdict=verdict, juge_nom='Juge <fictif> & collègue',
            created_by=self.agent,
        )
        rendered = []

        def record_paragraph(text, style):
            paragraph = Paragraph(text, style)
            rendered.append(paragraph.getPlainText())
            return paragraph

        with patch('core.pdf.Paragraph', side_effect=record_paragraph):
            response = fiche_ecrou_pdf(self.detenu)
        self.assertTrue(response.content.startswith(b'%PDF-'))
        self.assertGreaterEqual(_page_count(response.content), 2)
        plain_text = '\n'.join(rendered)
        self.assertIn('Tribunal A & B <démonstration>', plain_text)
        self.assertIn('RP <123> & 456', plain_text)
        self.assertIn('preuve <annexe> et montant > 500.', plain_text)
        self.assertIn('DÉMONSTRATION — Données entièrement fictives', plain_text)
        if PdfReader:
            extracted = '\n'.join(page.extract_text() for page in PdfReader(BytesIO(response.content)).pages)
            self.assertIn('RP <123> & 456', extracted)
            self.assertIn('preuve <annexe>', extracted)


class GeneralReportPdfTests(SimpleTestCase):
    @override_settings(DEMO_MODE=True)
    def test_120_long_names_generate_multiple_pages_without_layout_failure(self):
        rows = [[
            f'DEMO-2026-{index:04d}',
            f'PERSONNE FICTIVE {index} ' + 'Très long nom composé & famille <démo> ' * 5,
            'Prévenu', 'Faible', 'PAVILLON-DEMONSTRATION-BLOC-A-CELLULE-01', '10/10/2026',
        ] for index in range(120)]
        response = rapport_global_pdf(rows, {'total': 120, 'prevenus': 120, 'condamnes': 0, 'occupation': 75.0})
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF-'))
        self.assertGreaterEqual(_page_count(response.content), 3)
        if PdfReader:
            reader = PdfReader(BytesIO(response.content))
            self.assertTrue(all(float(page.mediabox.width) > float(page.mediabox.height) for page in reader.pages))
            extracted = '\n'.join(page.extract_text() for page in reader.pages)
            self.assertIn('DEMO-2026-0119', extracted)
            self.assertIn('famille <démo>', extracted)

    @override_settings(DEMO_MODE=False)
    def test_empty_report_is_still_a_valid_pdf(self):
        response = rapport_global_pdf([], {'total': 0, 'prevenus': 0, 'condamnes': 0, 'occupation': 0})
        self.assertEqual(_page_count(response.content), 1)
