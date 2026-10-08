import json
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import Role
from core.decorators import role_required
from core.models import AuditLog
from core.pdf import rapport_global_pdf
from core.utils import log_audit
from prison.models import Cellule, Detenu, StatutJudiciaire, Visite


@login_required
def dashboard(request):
    actifs = Detenu.objects.exclude(
        statut_judiciaire__in=[StatutJudiciaire.ARCHIVE, StatutJudiciaire.DECEDE]
    )
    total = actifs.count()
    prevenus = actifs.filter(statut_judiciaire=StatutJudiciaire.PREVENU).count()
    condamnes = actifs.filter(statut_judiciaire=StatutJudiciaire.CONDAMNE).count()

    cellules = Cellule.objects.all()
    capacite = sum(c.capacite_max for c in cellules) or 1
    occupation_count = Detenu.objects.filter(
        statut_judiciaire__in=[StatutJudiciaire.PREVENU, StatutJudiciaire.CONDAMNE]
    ).count()
    taux = round(100 * occupation_count / capacite, 1)

    by_statut = list(
        Detenu.objects.values('statut_judiciaire')
        .annotate(total=Count('id'))
        .order_by('statut_judiciaire')
    )
    by_danger = list(
        Detenu.objects.exclude(statut_judiciaire=StatutJudiciaire.ARCHIVE)
        .values('niveau_dangerosite')
        .annotate(total=Count('id'))
    )
    recent_detenus = Detenu.objects.select_related('cellule').order_by('-date_ecrou')[:8]
    recent_logs = AuditLog.objects.all()[:8]
    visites_today = Visite.objects.filter(date_visite=timezone.localdate()).count()

    context = {
        'totalDetenus': total,
        'totalPrevenus': prevenus,
        'totalCondamnes': condamnes,
        'tauxOccupation': taux,
        'visitesToday': visites_today,
        'recent_detenus': recent_detenus,
        'recent_logs': recent_logs,
        'chart_statut_labels': json.dumps([s['statut_judiciaire'] for s in by_statut]),
        'chart_statut_values': json.dumps([s['total'] for s in by_statut]),
        'chart_danger_labels': json.dumps([d['niveau_dangerosite'] for d in by_danger]),
        'chart_danger_values': json.dumps([d['total'] for d in by_danger]),
    }
    return render(request, 'core/dashboard.html', context)


@login_required
def reports(request):
    total = Detenu.objects.exclude(statut_judiciaire=StatutJudiciaire.ARCHIVE).count()
    prevenus = Detenu.objects.filter(statut_judiciaire=StatutJudiciaire.PREVENU).count()
    condamnes = Detenu.objects.filter(statut_judiciaire=StatutJudiciaire.CONDAMNE).count()
    liberes = Detenu.objects.filter(statut_judiciaire=StatutJudiciaire.LIBERE).count()
    cellules = Cellule.objects.count()
    by_statut = Detenu.objects.values('statut_judiciaire').annotate(total=Count('id'))
    return render(request, 'core/reports.html', {
        'total': total, 'prevenus': prevenus, 'condamnes': condamnes,
        'liberes': liberes, 'cellules': cellules, 'by_statut': by_statut,
    })


@login_required
def reports_pdf(request):
    detenus = Detenu.objects.select_related('cellule').exclude(
        statut_judiciaire=StatutJudiciaire.ARCHIVE
    ).order_by('nom')[:500]
    rows = [
        [
            d.matricule, d.full_name, d.get_statut_judiciaire_display(),
            d.get_niveau_dangerosite_display(),
            d.cellule.code_cellule if d.cellule else '—',
            timezone.localtime(d.date_ecrou).strftime('%d/%m/%Y'),
        ]
        for d in detenus
    ]
    actifs = Detenu.objects.filter(
        statut_judiciaire__in=[StatutJudiciaire.PREVENU, StatutJudiciaire.CONDAMNE]
    )
    capacite = sum(c.capacite_max for c in Cellule.objects.all()) or 1
    kpis = {
        'total': Detenu.objects.exclude(statut_judiciaire=StatutJudiciaire.ARCHIVE).count(),
        'prevenus': Detenu.objects.filter(statut_judiciaire=StatutJudiciaire.PREVENU).count(),
        'condamnes': Detenu.objects.filter(statut_judiciaire=StatutJudiciaire.CONDAMNE).count(),
        'occupation': round(100 * actifs.count() / capacite, 1),
    }
    log_audit(request, 'EXPORT_PDF', 'REPORTS', 'Export PDF rapport global')
    return rapport_global_pdf(rows, kpis)


@role_required(Role.ADMIN, Role.DIRECTEUR)
def audit_list(request):
    qs = AuditLog.objects.select_related('user').all()
    module = request.GET.get('module', '').strip()
    search = request.GET.get('search', '').strip()
    if module:
        qs = qs.filter(module=module)
    if search:
        qs = qs.filter(
            Q(description__icontains=search) | Q(action__icontains=search) | Q(user_nom__icontains=search)
        )
    modules = AuditLog.objects.values_list('module', flat=True).distinct().order_by('module')
    return render(request, 'core/audit.html', {
        'logs': qs[:200], 'modules': modules,
        'filter_module': module, 'filter_search': search,
    })


@role_required(Role.ADMIN)
def backup_page(request):
    return render(request, 'core/backup.html')


@role_required(Role.ADMIN)
@require_POST
def backup_export(request):
    db_path = Path(settings.DATABASES['default']['NAME'])
    if not db_path.exists():
        messages.error(request, 'Base SQLite introuvable.')
        return redirect('core:backup')
    log_audit(request, 'BACKUP_EXPORT', 'BACKUP', 'Export SQLite')
    return FileResponse(
        open(db_path, 'rb'),
        as_attachment=True,
        filename=f'sgp_makala_backup_{timezone.localdate()}.sqlite3',
    )


@login_required
def media_photo(request, filename):
    path = Path(settings.MEDIA_ROOT) / 'photos' / filename
    if filename == 'default_detenu.png' and not path.exists():
        raise Http404
    if not path.exists() or not path.is_file():
        raise Http404
    return FileResponse(open(path, 'rb'))


@login_required
def media_document(request, filename):
    path = Path(settings.MEDIA_ROOT) / 'documents' / filename
    if not path.exists() or not path.is_file():
        raise Http404
    return FileResponse(open(path, 'rb'), as_attachment=True, filename=filename)


def forbidden(request):
    return render(request, 'core/403.html', status=403)


def not_found(request, exception=None):
    return render(request, 'core/404.html', status=404)
