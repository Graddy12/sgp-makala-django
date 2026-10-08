from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime, parse_date
from django.views.decorators.http import require_http_methods, require_POST

from accounts.models import Role
from core.decorators import role_required
from core.pdf import fiche_ecrou_pdf
from core.utils import DOC_EXTS, MAX_DOC, MAX_PHOTO, PHOTO_EXTS, log_audit, save_upload
from prison.models import (
    Cellule, Detenu, DocumentJudiciaire, Jugement, StatutJudiciaire,
    StatutTransfert, StatutVisite, Transfert, TypeDocument, Visite,
)


# ─── DÉTENUS ────────────────────────────────────────────────────────────────

@login_required
def detenus_list(request):
    qs = Detenu.objects.select_related('cellule').all()
    search = request.GET.get('search', '').strip()
    statut = request.GET.get('statut', '').strip()
    danger = request.GET.get('dangerosite', '').strip()
    genre = request.GET.get('genre', '').strip()
    cellule_id = request.GET.get('cellule_id', '').strip()
    nationalite = request.GET.get('nationalite', '').strip()
    date_ecrou = request.GET.get('date_ecrou', '').strip()

    if search:
        qs = qs.filter(
            Q(matricule__icontains=search) | Q(nom__icontains=search) |
            Q(postnom__icontains=search) | Q(prenom__icontains=search) |
            Q(motif_inculpation__icontains=search) | Q(nationalite__icontains=search) |
            Q(cellule__code_cellule__icontains=search) | Q(cellule__pavillon__icontains=search)
        )
    if statut:
        qs = qs.filter(statut_judiciaire=statut)
    if danger:
        qs = qs.filter(niveau_dangerosite=danger)
    if genre:
        qs = qs.filter(genre=genre)
    if cellule_id:
        qs = qs.filter(cellule_id=cellule_id)
    if nationalite:
        qs = qs.filter(nationalite__icontains=nationalite)
    if date_ecrou:
        qs = qs.filter(date_ecrou__date=date_ecrou)

    paginator = Paginator(qs, 10)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'prison/detenus_index.html', {
        'page_obj': page,
        'cellules': Cellule.objects.all(),
        'nationalites': Detenu.objects.exclude(nationalite='')
            .values_list('nationalite', flat=True).distinct().order_by('nationalite'),
        'filters': {
            'search': search, 'statut': statut, 'dangerosite': danger,
            'genre': genre, 'cellule_id': cellule_id,
            'nationalite': nationalite, 'date_ecrou': date_ecrou,
        },
    })


@role_required(Role.ADMIN, Role.DIRECTEUR, Role.GREFFIER)
@require_http_methods(['GET', 'POST'])
def detenus_create(request):
    if request.method == 'POST':
        try:
            detenu = _save_detenu_from_post(request, detenu=None)
            log_audit(request, 'CREATION_DETENU', 'DETENUS', f'Écrou {detenu.matricule}')
            messages.success(request, f'Détenu {detenu.full_name} enregistré ({detenu.matricule}).')
            return redirect('prison:detenus_show', pk=detenu.pk)
        except ValueError as e:
            messages.error(request, str(e))
    return render(request, 'prison/detenus_create.html', {
        'cellules': Cellule.disponibles(),
        'preview_matricule': Detenu.generate_matricule(),
        'doc_types': TypeDocument.choices,
    })


@login_required
def detenus_show(request, pk):
    detenu = get_object_or_404(
        Detenu.objects.select_related('cellule', 'created_by'), pk=pk
    )
    return render(request, 'prison/detenus_show.html', {
        'detenu': detenu,
        'jugements': detenu.jugements.select_related('created_by').all(),
        'transferts': detenu.transferts.select_related('autorise_par').all(),
        'visites': detenu.visites.select_related('enregistre_par').all()[:20],
        'documents': detenu.documents.select_related('uploade_par').all(),
    })


@role_required(Role.ADMIN, Role.DIRECTEUR, Role.GREFFIER)
@require_http_methods(['GET', 'POST'])
def detenus_edit(request, pk):
    detenu = get_object_or_404(Detenu, pk=pk)
    if request.method == 'POST':
        try:
            detenu = _save_detenu_from_post(request, detenu=detenu)
            log_audit(request, 'MODIF_DETENU', 'DETENUS', f'Modification {detenu.matricule}')
            messages.success(request, 'Dossier mis à jour.')
            return redirect('prison:detenus_show', pk=detenu.pk)
        except ValueError as e:
            messages.error(request, str(e))
    return render(request, 'prison/detenus_edit.html', {
        'detenu': detenu,
        'cellules': Cellule.objects.all(),
    })


@role_required(Role.ADMIN, Role.DIRECTEUR, Role.GREFFIER)
@require_POST
def detenus_archive(request, pk):
    detenu = get_object_or_404(Detenu, pk=pk)
    detenu.archive()
    log_audit(request, 'ARCHIVE_DETENU', 'DETENUS', f'Archivage {detenu.matricule}')
    messages.success(request, f'{detenu.matricule} archivé.')
    return redirect('prison:detenus')


@login_required
def detenus_print(request, pk):
    detenu = get_object_or_404(Detenu.objects.select_related('cellule'), pk=pk)
    log_audit(request, 'PRINT_FICHE', 'DETENUS', f'Fiche PDF {detenu.matricule}')
    return fiche_ecrou_pdf(detenu)


def _save_detenu_from_post(request, detenu=None):
    nom = (request.POST.get('nom') or '').strip().upper()
    postnom = (request.POST.get('postnom') or '').strip().upper() or None
    prenom = (request.POST.get('prenom') or '').strip().capitalize()
    date_naissance = request.POST.get('date_naissance') or ''
    lieu_naissance = (request.POST.get('lieu_naissance') or '').strip()
    motif = (request.POST.get('motif_inculpation') or '').strip()
    if not all([nom, prenom, date_naissance, lieu_naissance, motif]):
        raise ValueError('Veuillez remplir tous les champs obligatoires (*).')

    is_new = detenu is None
    if is_new:
        detenu = Detenu(matricule=Detenu.generate_matricule(), created_by=request.user)

    detenu.nom = nom
    detenu.postnom = postnom
    detenu.prenom = prenom
    detenu.date_naissance = date_naissance
    detenu.lieu_naissance = lieu_naissance
    detenu.genre = request.POST.get('genre') or 'M'
    detenu.nationalite = (request.POST.get('nationalite') or 'Congolaise (RDC)').strip()
    detenu.etat_civil = request.POST.get('etat_civil') or 'celibataire'
    detenu.adresse = (request.POST.get('adresse') or '').strip() or None
    detenu.statut_judiciaire = request.POST.get('statut_judiciaire') or StatutJudiciaire.PREVENU
    detenu.niveau_dangerosite = request.POST.get('niveau_dangerosite') or 'faible'
    detenu.motif_inculpation = motif
    cellule_id = request.POST.get('cellule_id') or ''
    detenu.cellule_id = int(cellule_id) if cellule_id else None

    if is_new:
        date_ecrou = request.POST.get('date_ecrou') or ''
        if date_ecrou:
            dt = parse_datetime(date_ecrou.replace('T', ' '))
            if dt:
                if timezone.is_naive(dt):
                    dt = timezone.make_aware(dt)
                detenu.date_ecrou = dt

    photo = request.FILES.get('photo')
    if photo:
        name = save_upload(photo, 'photos', PHOTO_EXTS, MAX_PHOTO, 'detenu')
        if name:
            detenu.photo = name

    detenu.save()

    if is_new:
        doc = request.FILES.get('document_initial')
        if doc:
            fname = save_upload(doc, 'documents', DOC_EXTS, MAX_DOC, 'doc')
            DocumentJudiciaire.objects.create(
                detenu=detenu,
                titre=(request.POST.get('document_titre') or 'Mandat de Dépôt').strip(),
                type_doc=request.POST.get('document_type') or TypeDocument.MANDAT,
                fichier_path=fname,
                taille_ko=max(1, doc.size // 1024),
                uploade_par=request.user,
            )
    return detenu


# ─── CELLULES ───────────────────────────────────────────────────────────────

@login_required
def cellules_list(request):
    cellules = Cellule.objects.all()
    return render(request, 'prison/cellules_index.html', {'cellules': cellules})


@role_required(Role.ADMIN, Role.DIRECTEUR, Role.GREFFIER)
@require_http_methods(['GET', 'POST'])
def cellules_create(request):
    if request.method == 'POST':
        code = (request.POST.get('code_cellule') or '').strip().upper()
        pavillon = (request.POST.get('pavillon') or '').strip()
        bloc = (request.POST.get('bloc') or '').strip()
        capacite = int(request.POST.get('capacite_max') or 10)
        statut = request.POST.get('statut') or 'disponible'
        description = (request.POST.get('description') or '').strip() or None
        if not all([code, pavillon, bloc]):
            messages.error(request, 'Code, pavillon et bloc sont obligatoires.')
        elif Cellule.objects.filter(code_cellule=code).exists():
            messages.error(request, 'Ce code cellule existe déjà.')
        else:
            c = Cellule.objects.create(
                code_cellule=code, pavillon=pavillon, bloc=bloc,
                capacite_max=capacite, statut=statut, description=description,
            )
            log_audit(request, 'CREATION_CELLULE', 'CELLULES', f'Cellule {c.code_cellule}')
            messages.success(request, f'Cellule {c.code_cellule} créée.')
            return redirect('prison:cellules')
    return render(request, 'prison/cellules_create.html')


@login_required
def cellules_show(request, pk):
    cellule = get_object_or_404(Cellule, pk=pk)
    occupants = cellule.detenus.filter(
        statut_judiciaire__in=[StatutJudiciaire.PREVENU, StatutJudiciaire.CONDAMNE]
    )
    return render(request, 'prison/cellules_show.html', {
        'cellule': cellule, 'occupants': occupants,
    })


# ─── JUGEMENTS ──────────────────────────────────────────────────────────────

@login_required
def jugements_list(request):
    jugements = Jugement.objects.select_related('detenu', 'created_by').all()[:200]
    return render(request, 'prison/jugements_index.html', {'jugements': jugements})


@role_required(Role.ADMIN, Role.DIRECTEUR, Role.GREFFIER)
@require_http_methods(['GET', 'POST'])
def jugements_create(request):
    detenu_id = request.GET.get('detenu_id') or request.POST.get('detenu_id')
    if request.method == 'POST':
        detenu = Detenu.objects.filter(pk=detenu_id).first()
        tribunal = (request.POST.get('tribunal') or '').strip()
        numero = (request.POST.get('numero_dossier') or '').strip()
        date_j = request.POST.get('date_jugement') or ''
        resume = (request.POST.get('resume_verdict') or '').strip()
        if not detenu or not all([tribunal, numero, date_j, resume]):
            messages.error(request, 'Veuillez remplir tous les champs obligatoires.')
        else:
            j = Jugement.objects.create(
                detenu=detenu, tribunal=tribunal, numero_dossier=numero,
                date_jugement=date_j,
                type_decision=request.POST.get('type_decision') or 'condamnation',
                peine_ans=int(request.POST.get('peine_ans') or 0),
                peine_mois=int(request.POST.get('peine_mois') or 0),
                peine_amende=request.POST.get('peine_amende') or 0,
                resume_verdict=resume,
                juge_nom=(request.POST.get('juge_nom') or '').strip() or None,
                created_by=request.user,
            )
            j.apply_side_effects()
            log_audit(
                request, 'ENREGISTREMENT_JUGEMENT', 'JUGEMENTS',
                f'Jugement {numero} pour {detenu.matricule}',
            )
            messages.success(request, f'Jugement {numero} enregistré.')
            return redirect('prison:detenus_show', pk=detenu.pk)
    return render(request, 'prison/jugements_create.html', {
        'detenus': Detenu.objects.exclude(
            statut_judiciaire__in=[StatutJudiciaire.ARCHIVE, StatutJudiciaire.LIBERE]
        ),
        'selected_detenu': Detenu.objects.filter(pk=detenu_id).first() if detenu_id else None,
    })


# ─── TRANSFERTS ─────────────────────────────────────────────────────────────

@login_required
def transferts_list(request):
    transferts = Transfert.objects.select_related('detenu', 'autorise_par').all()[:200]
    return render(request, 'prison/transferts_index.html', {'transferts': transferts})


@role_required(Role.ADMIN, Role.DIRECTEUR)
@require_http_methods(['GET', 'POST'])
def transferts_create(request):
    if request.method == 'POST':
        detenu = Detenu.objects.filter(pk=request.POST.get('detenu_id')).first()
        dest = (request.POST.get('etablissement_destination') or '').strip()
        motif = (request.POST.get('motif_transfert') or '').strip()
        date_t = request.POST.get('date_transfert') or ''
        if not detenu or not all([dest, motif, date_t]):
            messages.error(request, 'Champs obligatoires manquants.')
        else:
            t = Transfert.objects.create(
                detenu=detenu,
                etablissement_provenance=(
                    request.POST.get('etablissement_provenance') or 'Prison Centrale de Makala'
                ).strip(),
                etablissement_destination=dest,
                motif_transfert=motif,
                date_transfert=date_t,
                escorte_agents=(request.POST.get('escorte_agents') or '').strip() or None,
                notes=(request.POST.get('notes') or '').strip() or None,
                autorise_par=request.user,
            )
            log_audit(request, 'CREATION_TRANSFERT', 'TRANSFERTS', f'Transfert {detenu.matricule}')
            messages.success(request, 'Transfert planifié.')
            return redirect('prison:transferts')
    return render(request, 'prison/transferts_create.html', {
        'detenus': Detenu.objects.filter(
            statut_judiciaire__in=[StatutJudiciaire.PREVENU, StatutJudiciaire.CONDAMNE]
        ),
    })


@role_required(Role.ADMIN, Role.DIRECTEUR)
@require_POST
def transferts_status(request, pk):
    t = get_object_or_404(Transfert, pk=pk)
    new_status = request.POST.get('statut')
    if new_status in dict(StatutTransfert.choices):
        t.update_statut(new_status)
        log_audit(request, 'MAJ_TRANSFERT', 'TRANSFERTS', f'{t.detenu.matricule} → {new_status}')
        messages.success(request, 'Statut du transfert mis à jour.')
    return redirect('prison:transferts')


# ─── VISITES ────────────────────────────────────────────────────────────────

@login_required
def visites_list(request):
    qs = Visite.objects.select_related('detenu', 'enregistre_par').all()
    detenu_id = request.GET.get('detenu_id')
    if detenu_id:
        qs = qs.filter(detenu_id=detenu_id)
    return render(request, 'prison/visites_index.html', {
        'visites': qs[:200], 'filter_detenu_id': detenu_id,
    })


@role_required(
    Role.ADMIN, Role.DIRECTEUR, Role.GREFFIER, Role.AGENT, Role.VISITES
)
@require_http_methods(['GET', 'POST'])
def visites_create(request):
    detenu_id = request.GET.get('detenu_id') or request.POST.get('detenu_id')
    if request.method == 'POST':
        detenu = Detenu.objects.filter(pk=detenu_id).first()
        nom = (request.POST.get('nom_visiteur') or '').strip().upper()
        prenom = (request.POST.get('prenom_visiteur') or '').strip().capitalize()
        lien = (request.POST.get('lien_parente') or '').strip()
        piece = (request.POST.get('numero_piece') or '').strip()
        date_v = request.POST.get('date_visite') or ''
        heure = request.POST.get('heure_debut') or ''
        if not detenu or not all([nom, prenom, lien, piece, date_v, heure]):
            messages.error(request, 'Champs obligatoires manquants.')
        else:
            Visite.objects.create(
                detenu=detenu, nom_visiteur=nom, prenom_visiteur=prenom,
                lien_parente=lien,
                type_piece_identite=(request.POST.get('type_piece_identite') or "Carte d'Électeur").strip(),
                numero_piece=piece,
                telephone=(request.POST.get('telephone') or '').strip() or None,
                date_visite=date_v, heure_debut=heure,
                statut=StatutVisite.AUTORISEE,
                objet_visite=(request.POST.get('objet_visite') or '').strip() or None,
                effets_apportes=(request.POST.get('effets_apportes') or '').strip() or None,
                enregistre_par=request.user,
            )
            log_audit(request, 'CREATION_VISITE', 'VISITES', f'Visite pour {detenu.matricule}')
            messages.success(request, 'Visite enregistrée.')
            return redirect('prison:visites')
    return render(request, 'prison/visites_create.html', {
        'detenus': Detenu.objects.filter(
            statut_judiciaire__in=[StatutJudiciaire.PREVENU, StatutJudiciaire.CONDAMNE]
        ),
        'selected_detenu': Detenu.objects.filter(pk=detenu_id).first() if detenu_id else None,
    })


@role_required(
    Role.ADMIN, Role.DIRECTEUR, Role.GREFFIER, Role.AGENT, Role.VISITES
)
@require_POST
def visites_end(request, pk):
    v = get_object_or_404(Visite, pk=pk)
    v.terminer()
    log_audit(request, 'FIN_VISITE', 'VISITES', f'Fin visite {v.visiteur_full_name}')
    messages.success(request, 'Visite terminée.')
    return redirect('prison:visites')


# ─── DOCUMENTS ──────────────────────────────────────────────────────────────

@login_required
def documents_list(request):
    docs = DocumentJudiciaire.objects.select_related('detenu', 'uploade_par').all()[:200]
    return render(request, 'prison/documents_index.html', {
        'documents': docs,
        'detenus': Detenu.objects.exclude(statut_judiciaire=StatutJudiciaire.ARCHIVE),
        'doc_types': TypeDocument.choices,
    })


@role_required(Role.ADMIN, Role.DIRECTEUR, Role.GREFFIER)
@require_POST
def documents_store(request):
    detenu = Detenu.objects.filter(pk=request.POST.get('detenu_id')).first()
    titre = (request.POST.get('titre') or '').strip()
    fichier = request.FILES.get('fichier')
    if not detenu or not titre or not fichier:
        messages.error(request, 'Détenu, titre et fichier sont obligatoires.')
        return redirect('prison:documents')
    try:
        fname = save_upload(fichier, 'documents', DOC_EXTS, MAX_DOC, 'doc')
        DocumentJudiciaire.objects.create(
            detenu=detenu, titre=titre,
            type_doc=request.POST.get('type_doc') or TypeDocument.AUTRE,
            fichier_path=fname,
            taille_ko=max(1, fichier.size // 1024),
            description=(request.POST.get('description') or '').strip() or None,
            uploade_par=request.user,
        )
        log_audit(request, 'UPLOAD_DOC', 'DOCUMENTS', f'{titre} pour {detenu.matricule}')
        messages.success(request, 'Document enregistré.')
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('prison:documents')
