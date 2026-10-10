from datetime import date, time, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Role, User
from prison.models import Cellule, Detenu, Visite


class DossierTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            'dossier@example.invalid', 'Test-only-password!',
            nom='Test', prenom='Greffier', role=Role.ADMIN,
        )
        self.cell = Cellule.objects.create(
            code_cellule='PAV-TEST-C03', pavillon='Pavillon de test',
            bloc='Bloc de test', capacite_max=4,
            description='Description de la cellule test',
        )
        self.detenu = Detenu.objects.create(
            matricule='DOSSIER-TEST', nom='TEST', postnom='DOSSIER',
            prenom='David', date_naissance=date(1990, 5, 6),
            lieu_naissance='Kinshasa', adresse='Adresse du dossier test',
            motif_inculpation='Motif du dossier test', cellule=self.cell,
            created_by=self.user,
        )
        self.url = reverse('prison:detenus_show', args=[self.detenu.pk])
        self.client.force_login(self.user)

    def test_dossier_exposes_real_assignment_and_identity(self):
        response = self.client.get(self.url)
        self.assertContains(response, self.cell.code_cellule)
        self.assertContains(response, self.cell.pavillon)
        self.assertContains(response, self.cell.bloc)
        self.assertContains(response, self.cell.description)
        self.assertContains(response, reverse('prison:cellules_show', args=[self.cell.pk]))
        self.assertContains(response, self.detenu.adresse)
        self.assertContains(response, self.detenu.motif_inculpation)
        self.assertContains(response, self.user.full_name)
        self.assertContains(response, 'aria-valuenow="1"')
        today = timezone.localdate()
        expected_age = today.year - 1990 - ((today.month, today.day) < (5, 6))
        self.assertEqual(response.context['age_detenu'], expected_age)

    def test_all_visits_and_full_visitor_details_are_available(self):
        first_day = date(2026, 1, 1)
        Visite.objects.bulk_create([
            Visite(
                detenu=self.detenu, nom_visiteur=f'VISITEUR-{i:02}',
                prenom_visiteur='Test', lien_parente='Famille',
                numero_piece=f'PIECE-{i:02}', telephone='000-TEST',
                date_visite=first_day + timedelta(days=i),
                heure_debut=time(9, 30), heure_fin=time(10, 0),
                objet_visite='Objet de la visite test',
                effets_apportes='Effets de la visite test', enregistre_par=self.user,
            )
            for i in range(25)
        ])
        response = self.client.get(self.url)
        self.assertEqual(len(response.context['visites']), 25)
        # The oldest visit was omitted by the former twenty-visit limit.
        self.assertContains(response, 'Test VISITEUR-00')
        self.assertContains(response, 'PIECE-00')
        self.assertContains(response, '000-TEST')
        self.assertContains(response, 'Objet de la visite test')
        self.assertContains(response, 'Effets de la visite test')

    def test_missing_assignment_is_distinguished_from_inactive_dossier(self):
        self.detenu.cellule = None
        self.detenu.save()
        response = self.client.get(self.url)
        self.assertContains(response, 'Cellule non affectée')
        self.assertContains(response, 'Renseigner la cellule')
        self.assertNotContains(response, self.cell.code_cellule)
        self.detenu.statut_judiciaire = 'transfere'
        self.detenu.save()
        response = self.client.get(self.url)
        self.assertContains(response, 'Aucune affectation active')
        self.assertNotContains(response, 'Renseigner la cellule')
        self.assertNotContains(response, self.cell.code_cellule)
        self.user.role = Role.AGENT
        self.user.save()
        self.detenu.statut_judiciaire = 'prevenu'
        self.detenu.save()
        response = self.client.get(self.url)
        self.assertContains(response, 'Cellule non affectée')
        self.assertNotContains(response, 'Renseigner la cellule')
