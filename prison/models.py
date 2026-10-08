from datetime import timedelta
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class StatutCellule(models.TextChoices):
    DISPONIBLE = 'disponible', 'Disponible'
    PLEINE = 'pleine', 'Pleine'
    MAINTENANCE = 'maintenance', 'En maintenance'
    ISOLEMENT = 'isolement', "Cellule d'isolement"


class Genre(models.TextChoices):
    M = 'M', 'Masculin'
    F = 'F', 'Féminin'


class EtatCivil(models.TextChoices):
    CELIBATAIRE = 'celibataire', 'Célibataire'
    MARIE = 'marie', 'Marié(e)'
    DIVORCE = 'divorce', 'Divorcé(e)'
    VEUF = 'veuf', 'Veuf/Veuve'


class StatutJudiciaire(models.TextChoices):
    PREVENU = 'prevenu', 'Prévenu'
    CONDAMNE = 'condamne', 'Condamné'
    TRANSFERE = 'transfere', 'Transféré'
    LIBERE = 'libere', 'Libéré'
    DECEDE = 'decede', 'Décédé'
    ARCHIVE = 'archive', 'Archivé'


class NiveauDangerosite(models.TextChoices):
    FAIBLE = 'faible', 'Faible'
    MOYEN = 'moyen', 'Moyen'
    ELEVE = 'eleve', 'Élevé'
    CRITIQUE = 'critique', 'Critique'


class TypeDecision(models.TextChoices):
    CONDAMNATION = 'condamnation', 'Condamnation'
    ACQUITTEMENT = 'acquittement', 'Acquittement'
    RENVOI = 'renvoi', 'Renvoi'
    LIBERATION_COND = 'liberation_conditionnelle', 'Libération conditionnelle'


class StatutTransfert(models.TextChoices):
    PLANIFIE = 'planifie', 'Planifié'
    EN_COURS = 'en_cours', "En cours d'exécution"
    EFFECTUE = 'effectue', 'Effectué'
    ANNULE = 'annule', 'Annulé'


class StatutVisite(models.TextChoices):
    DEMANDE = 'demande', 'En attente'
    AUTORISEE = 'autorisee', 'Autorisée'
    REFUSEE = 'refusee', 'Refusée'
    TERMINEE = 'terminee', 'Terminée'
    ANNULEE = 'annulee', 'Annulée'


class TypeDocument(models.TextChoices):
    MANDAT = 'mandat_depot', 'Mandat de Dépôt'
    ACCUSATION = 'acte_accusation', "Acte d'Accusation"
    MEDICALE = 'fiche_medicale', 'Fiche Médicale'
    JUGEMENT = 'jugement', 'Copie du Jugement'
    LIBERATION = 'ordre_liberation', 'Ordre de Libération'
    AUTRE = 'autre', 'Autre Document'


STATUT_DETENU_BADGES = {
    'prevenu': 'bg-warning text-dark',
    'condamne': 'bg-danger',
    'transfere': 'bg-info text-dark',
    'libere': 'bg-success',
    'decede': 'bg-dark',
    'archive': 'bg-secondary',
}

DANGER_BADGES = {
    'faible': 'bg-success',
    'moyen': 'bg-info text-dark',
    'eleve': 'bg-warning text-dark',
    'critique': 'bg-danger',
}

CELLULE_BADGES = {
    'disponible': 'bg-success',
    'pleine': 'bg-danger',
    'maintenance': 'bg-warning text-dark',
    'isolement': 'bg-dark',
}


class Cellule(models.Model):
    code_cellule = models.CharField(max_length=30, unique=True)
    pavillon = models.CharField(max_length=50)
    bloc = models.CharField(max_length=50)
    capacite_max = models.PositiveIntegerField(default=10)
    statut = models.CharField(max_length=20, choices=StatutCellule.choices, default=StatutCellule.DISPONIBLE)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cellules'
        ordering = ['pavillon', 'bloc', 'code_cellule']

    def __str__(self):
        return self.code_cellule

    @property
    def occupation(self):
        return self.detenus.filter(
            statut_judiciaire__in=[StatutJudiciaire.PREVENU, StatutJudiciaire.CONDAMNE]
        ).count()

    @property
    def places_libres(self):
        return max(0, self.capacite_max - self.occupation)

    @property
    def is_disponible(self):
        if self.statut == StatutCellule.MAINTENANCE:
            return False
        return self.occupation < self.capacite_max

    @property
    def badge_class(self):
        return CELLULE_BADGES.get(self.statut, 'bg-secondary')

    @classmethod
    def disponibles(cls):
        qs = cls.objects.exclude(statut=StatutCellule.MAINTENANCE)
        return [c for c in qs if c.is_disponible]


class Detenu(models.Model):
    matricule = models.CharField(max_length=50, unique=True)
    nom = models.CharField(max_length=100)
    postnom = models.CharField(max_length=100, blank=True, null=True)
    prenom = models.CharField(max_length=100)
    date_naissance = models.DateField()
    lieu_naissance = models.CharField(max_length=100)
    genre = models.CharField(max_length=1, choices=Genre.choices, default=Genre.M)
    nationalite = models.CharField(max_length=100, default='Congolaise (RDC)')
    etat_civil = models.CharField(max_length=20, choices=EtatCivil.choices, default=EtatCivil.CELIBATAIRE)
    adresse = models.CharField(max_length=255, blank=True, null=True)
    photo = models.CharField(max_length=255, default='default_detenu.png')
    statut_judiciaire = models.CharField(
        max_length=20, choices=StatutJudiciaire.choices, default=StatutJudiciaire.PREVENU
    )
    niveau_dangerosite = models.CharField(
        max_length=20, choices=NiveauDangerosite.choices, default=NiveauDangerosite.FAIBLE
    )
    date_ecrou = models.DateTimeField(default=timezone.now)
    date_liberation_prevue = models.DateField(blank=True, null=True)
    date_liberation_effective = models.DateTimeField(blank=True, null=True)
    motif_inculpation = models.TextField()
    cellule = models.ForeignKey(
        Cellule, on_delete=models.SET_NULL, null=True, blank=True, related_name='detenus'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='detenus_crees'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'detenus'
        ordering = ['-id']

    def __str__(self):
        return f'{self.matricule} — {self.nom} {self.prenom}'

    @property
    def full_name(self):
        parts = [self.nom, self.postnom or '', self.prenom]
        return ' '.join(p for p in parts if p).strip()

    @property
    def badge_statut(self):
        return STATUT_DETENU_BADGES.get(self.statut_judiciaire, 'bg-secondary')

    @property
    def badge_danger(self):
        return DANGER_BADGES.get(self.niveau_dangerosite, 'bg-secondary')

    @classmethod
    def generate_matricule(cls):
        year = timezone.now().year
        prefix = f'MAK-{year}-'
        last = cls.objects.filter(matricule__startswith=prefix).order_by('-matricule').first()
        if last:
            try:
                seq = int(last.matricule.split('-')[-1]) + 1
            except ValueError:
                seq = 1
        else:
            seq = 1
        return f'{prefix}{seq:06d}'

    def archive(self):
        self.statut_judiciaire = StatutJudiciaire.ARCHIVE
        self.save(update_fields=['statut_judiciaire', 'updated_at'])


class Jugement(models.Model):
    detenu = models.ForeignKey(Detenu, on_delete=models.CASCADE, related_name='jugements')
    tribunal = models.CharField(max_length=150)
    numero_dossier = models.CharField(max_length=100)
    date_jugement = models.DateField()
    type_decision = models.CharField(max_length=30, choices=TypeDecision.choices)
    peine_ans = models.PositiveIntegerField(default=0)
    peine_mois = models.PositiveIntegerField(default=0)
    peine_amende = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    resume_verdict = models.TextField()
    document_path = models.CharField(max_length=255, blank=True, null=True)
    juge_nom = models.CharField(max_length=150, blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='jugements_crees'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'jugements'
        ordering = ['-date_jugement', '-id']

    def __str__(self):
        return f'{self.numero_dossier} — {self.get_type_decision_display()}'

    def apply_side_effects(self):
        detenu = self.detenu
        if self.type_decision == TypeDecision.CONDAMNATION:
            liber = self.date_jugement + timedelta(days=365 * self.peine_ans + 30 * self.peine_mois)
            detenu.statut_judiciaire = StatutJudiciaire.CONDAMNE
            detenu.date_liberation_prevue = liber
            detenu.save(update_fields=[
                'statut_judiciaire', 'date_liberation_prevue', 'updated_at'
            ])
        elif self.type_decision in (TypeDecision.ACQUITTEMENT, TypeDecision.LIBERATION_COND):
            detenu.statut_judiciaire = StatutJudiciaire.LIBERE
            detenu.date_liberation_effective = timezone.now()
            detenu.save(update_fields=[
                'statut_judiciaire', 'date_liberation_effective', 'updated_at'
            ])


class Transfert(models.Model):
    detenu = models.ForeignKey(Detenu, on_delete=models.CASCADE, related_name='transferts')
    etablissement_provenance = models.CharField(
        max_length=150, default='Prison Centrale de Makala'
    )
    etablissement_destination = models.CharField(max_length=150)
    motif_transfert = models.TextField()
    date_transfert = models.DateField()
    statut = models.CharField(
        max_length=20, choices=StatutTransfert.choices, default=StatutTransfert.PLANIFIE
    )
    escorte_agents = models.CharField(max_length=255, blank=True, null=True)
    autorise_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transferts_autorises'
    )
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'transferts'
        ordering = ['-date_transfert', '-id']

    def __str__(self):
        return f'Transfert {self.detenu.matricule} → {self.etablissement_destination}'

    def update_statut(self, new_statut):
        self.statut = new_statut
        self.save(update_fields=['statut'])
        if new_statut == StatutTransfert.EFFECTUE:
            detenu = self.detenu
            detenu.statut_judiciaire = StatutJudiciaire.TRANSFERE
            detenu.cellule = None
            detenu.save(update_fields=['statut_judiciaire', 'cellule', 'updated_at'])


class Visite(models.Model):
    detenu = models.ForeignKey(Detenu, on_delete=models.CASCADE, related_name='visites')
    nom_visiteur = models.CharField(max_length=100)
    prenom_visiteur = models.CharField(max_length=100)
    lien_parente = models.CharField(max_length=50)
    type_piece_identite = models.CharField(max_length=50, default="Carte d'Électeur")
    numero_piece = models.CharField(max_length=100)
    telephone = models.CharField(max_length=30, blank=True, null=True)
    date_visite = models.DateField()
    heure_debut = models.TimeField()
    heure_fin = models.TimeField(blank=True, null=True)
    statut = models.CharField(
        max_length=20, choices=StatutVisite.choices, default=StatutVisite.AUTORISEE
    )
    objet_visite = models.CharField(max_length=255, blank=True, null=True)
    effets_apportes = models.TextField(blank=True, null=True)
    enregistre_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='visites_enregistrees'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'visites'
        ordering = ['-date_visite', '-heure_debut']

    def __str__(self):
        return f'{self.prenom_visiteur} {self.nom_visiteur} → {self.detenu.matricule}'

    @property
    def visiteur_full_name(self):
        return f'{self.prenom_visiteur} {self.nom_visiteur}'

    def terminer(self):
        self.heure_fin = timezone.localtime().time()
        self.statut = StatutVisite.TERMINEE
        self.save(update_fields=['heure_fin', 'statut'])


class DocumentJudiciaire(models.Model):
    detenu = models.ForeignKey(Detenu, on_delete=models.CASCADE, related_name='documents')
    titre = models.CharField(max_length=150)
    type_doc = models.CharField(max_length=30, choices=TypeDocument.choices)
    fichier_path = models.CharField(max_length=255)
    taille_ko = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True, null=True)
    uploade_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='documents_uploades'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'documents'
        ordering = ['-created_at']

    def __str__(self):
        return self.titre
