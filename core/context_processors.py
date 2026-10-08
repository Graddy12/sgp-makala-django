from django.conf import settings

from accounts.models import Role, ROLE_BADGES
from prison.models import (
    STATUT_DETENU_BADGES, DANGER_BADGES, CELLULE_BADGES,
    StatutJudiciaire, NiveauDangerosite, StatutCellule,
    TypeDecision, StatutTransfert, StatutVisite, TypeDocument,
)


def sgp_globals(request):
    notifications = []
    unread = 0
    if getattr(request, 'user', None) and request.user.is_authenticated:
        from core.models import Notification
        notifications = list(
            Notification.objects.filter(user=request.user, is_read=False)[:8]
        )
        unread = Notification.objects.filter(user=request.user, is_read=False).count()

    return {
        'APP_NAME': settings.APP_NAME,
        'PRISON_NAME': settings.PRISON_NAME,
        'Role': Role,
        'ROLE_BADGES': ROLE_BADGES,
        'STATUT_DETENU_BADGES': STATUT_DETENU_BADGES,
        'DANGER_BADGES': DANGER_BADGES,
        'CELLULE_BADGES': CELLULE_BADGES,
        'StatutJudiciaire': StatutJudiciaire,
        'NiveauDangerosite': NiveauDangerosite,
        'StatutCellule': StatutCellule,
        'TypeDecision': TypeDecision,
        'StatutTransfert': StatutTransfert,
        'StatutVisite': StatutVisite,
        'TypeDocument': TypeDocument,
        'sgp_notifications': notifications,
        'sgp_unread_count': unread,
    }
