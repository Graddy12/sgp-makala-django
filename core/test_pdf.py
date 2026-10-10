"""Exercise PDF exports with photos, free text and realistic report sizes."""
from datetime import date, datetime, time
from io import BytesIO
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone
from PIL import Image as PILImage
from reportlab.platypus import Paragraph

from accounts.models import User
from core.pdf import _photo_path, fiche_ecrou_pdf, rapport_global_pdf
from prison.models import Cellule, Detenu, DocumentJudiciaire, Jugement, Transfert, Visite

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

    def _export_with_text(self):
        rendered = []

        def record_paragraph(text, style):
            paragraph = Paragraph(text, style)
            rendered.append(paragraph.getPlainText())
            return paragraph

        with patch('core.pdf.Paragraph', side_effect=record_paragraph):
            response = fiche_ecrou_pdf(self.detenu)
        return response, '\n'.join(rendered)

    def test_complete_record_includes_actual_cell_and_related_sections(self):
        cellule = Cellule.objects.create(
            code_cellule='DEMO-CELL-01', pavillon='Pavillon & <démo>', bloc='Bloc <B>',
            statut='isolement', capacite_max=2, description='Cellule fictive & <description>',
        )
        self.detenu.cellule = cellule
        self.detenu.adresse = '123 avenue <fictive> & quartier test'
        self.detenu.date_liberation_effective = timezone.make_aware(datetime(2026, 10, 11, 10, 30))
        self.detenu.save()
        document = DocumentJudiciaire.objects.create(
            detenu=self.detenu, titre='Mandat fictif <original> & copie', type_doc='mandat_depot',
            fichier_path='document_demo.pdf', taille_ko=12, description='Description <fictive> & complète',
            uploade_par=self.agent,
        )
        Visite.objects.create(
            detenu=self.detenu, nom_visiteur='Visiteur <fictif>', prenom_visiteur='A & B',
            lien_parente='Famille', numero_piece='DEMO-ID-001', date_visite=date(2026, 10, 10),
            heure_debut=time(10, 0), heure_fin=time(11, 0), statut='terminee',
            objet_visite='Visite <familiale> & échange', effets_apportes='Vêtements & livres <démo>',
            enregistre_par=self.agent,
        )
        Transfert.objects.create(
            detenu=self.detenu, etablissement_provenance='Prison fictive A',
            etablissement_destination='Centre <B> & annexe', date_transfert=date(2026, 10, 12),
            motif_transfert='Motif <fictif> & administratif', notes='Notes <démo> & suivi',
            statut='planifie', autorise_par=self.agent,
        )
        response, plain_text = self._export_with_text()
        self.assertTrue(response.content.startswith(b'%PDF-'))
        self.assertGreaterEqual(_page_count(response.content), 2)
        for value in (
            cellule.code_cellule, cellule.pavillon, cellule.bloc, cellule.get_statut_display(),
            'Occupation réelle', '1 / 2 place(s)', cellule.description,
            self.detenu.adresse, '11/10/2026 10:30', self.agent.full_name, self.agent.matricule,
            'Documents judiciaires', document.titre, document.get_type_doc_display(),
            'Historique des visites', 'A & B Visiteur <fictif>', '10:00 — 11:00',
            'Visite <familiale> & échange', 'Vêtements & livres <démo>',
            'Historique des transferts', 'Centre <B> & annexe', 'Motif <fictif> & administratif',
            'Notes <démo> & suivi', 'Suivi administratif du dossier',
        ):
            with self.subTest(value=value):
                self.assertIn(value, plain_text)
        if PdfReader:
            extracted = '\n'.join(page.extract_text() for page in PdfReader(BytesIO(response.content)).pages)
            self.assertIn(cellule.code_cellule, extracted)
            self.assertIn('Centre <B> & annexe', extracted)

    def test_unassigned_record_shows_empty_sections_without_inventing_cell(self):
        response, plain_text = self._export_with_text()
        self.assertTrue(response.content.startswith(b'%PDF-'))
        for value in (
            'Aucune cellule actuellement affectée.', 'Aucun jugement enregistré.',
            'Aucun document judiciaire enregistré.', 'Aucune visite enregistrée.',
            'Aucun transfert enregistré.', 'Non renseignée',
        ):
            with self.subTest(value=value):
                self.assertIn(value, plain_text)
        self.assertNotIn('DEMO-CELL-01', plain_text)

    def test_inactive_record_with_cell_reference_has_no_active_assignment(self):
        cellule = Cellule.objects.create(
            code_cellule='DEMO-REF-01', pavillon='Pavillon référence', bloc='Bloc A', capacite_max=5,
        )
        for statut in ('libere', 'archive'):
            with self.subTest(statut=statut):
                self.detenu.cellule = cellule
                self.detenu.statut_judiciaire = statut
                self.detenu.save(update_fields=['cellule', 'statut_judiciaire'])
                response, plain_text = self._export_with_text()
                self.assertTrue(response.content.startswith(b'%PDF-'))
                self.assertIn('Affectation pénitentiaire', plain_text)
                self.assertIn('Aucune affectation active.', plain_text)
                self.assertIn('Référence de cellule conservée', plain_text)
                self.assertIn(cellule.code_cellule, plain_text)
                self.assertNotIn('Occupation réelle', plain_text)

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
