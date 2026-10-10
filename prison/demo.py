"""Preview and confirm one fictional enrollment from a small JSON file."""
import json
import re
import shutil
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import FileResponse, Http404
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from accounts.models import Role
from core.decorators import role_required
from core.utils import log_audit
from prison.models import Cellule, Detenu, StatutJudiciaire

MAX_JSON = 64 * 1024
FIELDS = {'nom', 'postnom', 'prenom', 'date_naissance', 'lieu_naissance',
          'genre', 'nationalite', 'etat_civil', 'adresse', 'statut_judiciaire',
          'niveau_dangerosite', 'motif_inculpation', 'cellule_code', 'portrait'}


def build_enrollment(payload, user, matricule=None):
    if not isinstance(payload, dict) or payload.get('version') != 1 or payload.get('fictional') is not True:
        raise ValueError('Le JSON doit contenir version: 1 et fictional: true.')
    data = payload.get('detenu')
    if not isinstance(data, dict) or not data or set(data) - FIELDS:
        raise ValueError('Le bloc detenu contient des champs inconnus ou est absent.')
    if any(not isinstance(value, str) for value in data.values()):
        raise ValueError('Chaque champ du détenu doit être une chaîne de caractères.')
    fields = {key: value.strip() for key, value in data.items() if key not in {'cellule_code', 'portrait'}}
    if fields.get('statut_judiciaire', 'prevenu') != StatutJudiciaire.PREVENU:
        raise ValueError('Un nouvel écrou JSON doit avoir le statut prévenu.')
    fields['nom'] = fields.get('nom', '').upper()
    fields['postnom'] = fields.get('postnom', '').upper()
    detenu = Detenu(matricule=matricule or Detenu.generate_matricule(), created_by=user, **fields)
    if not fields.get('lieu_naissance') or not fields.get('motif_inculpation'):
        raise ValueError('Le lieu de naissance et le motif sont obligatoires.')
    code = data.get('cellule_code', '').strip()
    if code:
        cellule = Cellule.objects.filter(code_cellule=code).first()
        if not cellule or not cellule.is_disponible:
            raise ValueError('La cellule choisie est introuvable, pleine ou en maintenance.')
        detenu.cellule = cellule
    portrait = data.get('portrait', '')
    if portrait:
        if not re.fullmatch(r'demo/portraits/portrait_[mf]_0[1-8]\.jpg', portrait):
            raise ValueError('Choisissez un des portraits fictifs fournis avec la démo.')
        source = Path(settings.BASE_DIR) / 'static' / portrait
        if not source.is_file():
            raise ValueError('Ce portrait fictif est indisponible.')
        detenu.photo = 'demo_' + source.name
    detenu.full_clean()
    if detenu.date_naissance > timezone.localdate():
        raise ValueError('La date de naissance ne peut pas être dans le futur.')
    return detenu


def demo_only():
    if not settings.DEMO_MODE:
        raise Http404


@role_required(Role.ADMIN, Role.DIRECTEUR, Role.GREFFIER)
def enrollment_sample(request):
    demo_only()
    path = Path(settings.BASE_DIR) / 'demo' / 'enrollment_day_j.json'
    return FileResponse(path.open('rb'), as_attachment=True, filename='enrolement_jour_j.json', content_type='application/json')


@role_required(Role.ADMIN, Role.DIRECTEUR, Role.GREFFIER)
@require_http_methods(['GET', 'POST'])
def enrollment_import(request):
    demo_only()
    context = {}
    if request.method == 'POST':
        try:
            if request.POST.get('action') == 'confirm':
                token = request.POST.get('token', '')
                if not token or request.session.get('pending_demo_enrollment') != token:
                    raise ValueError('Cet aperçu a expiré ou a déjà été enregistré. Chargez à nouveau le JSON.')
                pending = signing.loads(token, salt='demo-enrollment', max_age=900)
                if pending['user_id'] != request.user.pk:
                    raise ValueError('Aperçu invalide.')
                with transaction.atomic():
                    detenu = build_enrollment(pending['payload'], request.user, pending['matricule'])
                    portrait = pending['payload']['detenu'].get('portrait')
                    if portrait:
                        destination = Path(settings.MEDIA_ROOT) / 'photos'
                        destination.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(Path(settings.BASE_DIR) / 'static' / portrait, destination / detenu.photo)
                    detenu.save()
                    log_audit(request, 'IMPORT_DEMO_JSON', 'DETENUS', f'Écrou fictif {detenu.matricule} depuis JSON')
                request.session.pop('pending_demo_enrollment', None)
                messages.success(request, f'Écrou fictif enregistré : {detenu.full_name} ({detenu.matricule}).')
                return redirect('prison:detenus_show', pk=detenu.pk)
            if request.POST.get('action') == 'sample':
                raw = (Path(settings.BASE_DIR) / 'demo' / 'enrollment_day_j.json').read_bytes()
            else:
                uploaded = request.FILES.get('json_file')
                if not uploaded or not uploaded.name.lower().endswith('.json'):
                    raise ValueError('Sélectionnez un fichier JSON.')
                if uploaded.size > MAX_JSON:
                    raise ValueError('Le fichier JSON ne peut pas dépasser 64 Ko.')
                raw = uploaded.read(MAX_JSON + 1)
            if len(raw) > MAX_JSON:
                raise ValueError('Le fichier JSON ne peut pas dépasser 64 Ko.')
            payload = json.loads(raw.decode('utf-8-sig'))
            detenu = build_enrollment(payload, request.user)
            token = signing.dumps({'payload': payload, 'user_id': request.user.pk, 'matricule': detenu.matricule}, salt='demo-enrollment', compress=True)
            request.session['pending_demo_enrollment'] = token
            context = {'preview': detenu, 'token': token, 'portrait': payload['detenu'].get('portrait', '')}
        except (ValueError, ValidationError, signing.BadSignature, IntegrityError, UnicodeError, RecursionError) as exc:
            error = ' '.join(exc.messages) if isinstance(exc, ValidationError) else str(exc)
            if isinstance(exc, IntegrityError):
                error = 'Ce matricule vient d’être attribué. Rechargez l’aperçu.'
            messages.error(request, error)
    return render(request, 'prison/detenus_import.html', context)
