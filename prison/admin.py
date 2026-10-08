from django.contrib import admin
from .models import Cellule, Detenu, Jugement, Transfert, Visite, DocumentJudiciaire


@admin.register(Cellule)
class CelluleAdmin(admin.ModelAdmin):
    list_display = ('code_cellule', 'pavillon', 'bloc', 'capacite_max', 'statut')
    list_filter = ('pavillon', 'statut')
    search_fields = ('code_cellule', 'pavillon', 'bloc')


@admin.register(Detenu)
class DetenuAdmin(admin.ModelAdmin):
    list_display = ('matricule', 'nom', 'prenom', 'statut_judiciaire', 'niveau_dangerosite', 'cellule')
    list_filter = ('statut_judiciaire', 'niveau_dangerosite', 'genre')
    search_fields = ('matricule', 'nom', 'prenom', 'postnom')


@admin.register(Jugement)
class JugementAdmin(admin.ModelAdmin):
    list_display = ('numero_dossier', 'detenu', 'type_decision', 'date_jugement')
    list_filter = ('type_decision',)


@admin.register(Transfert)
class TransfertAdmin(admin.ModelAdmin):
    list_display = ('detenu', 'etablissement_destination', 'date_transfert', 'statut')
    list_filter = ('statut',)


@admin.register(Visite)
class VisiteAdmin(admin.ModelAdmin):
    list_display = ('nom_visiteur', 'prenom_visiteur', 'detenu', 'date_visite', 'statut')
    list_filter = ('statut',)


@admin.register(DocumentJudiciaire)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('titre', 'type_doc', 'detenu', 'created_at')
    list_filter = ('type_doc',)
