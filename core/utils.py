"""Helpers: audit, upload validation, client IP."""
from pathlib import Path

from django.conf import settings

from .models import AuditLog, Notification


def client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '0.0.0.0')


def log_audit(request, action, module, description):
    user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
    AuditLog.objects.create(
        user=user if user else None,
        user_nom=user.full_name if user else None,
        role=user.role if user else None,
        action=action,
        module=module,
        description=description,
        ip_address=client_ip(request),
        user_agent=(request.META.get('HTTP_USER_AGENT') or '')[:255],
    )


def create_notification(titre, message, type_='info', user=None):
    return Notification.objects.create(
        user=user, titre=titre, message=message, type=type_
    )


PHOTO_EXTS = {'.jpg', '.jpeg', '.png', '.webp'}
DOC_EXTS = {'.pdf', '.jpg', '.jpeg', '.png', '.webp', '.doc', '.docx'}
MAX_PHOTO = 5 * 1024 * 1024
MAX_DOC = 10 * 1024 * 1024


def save_upload(uploaded, subdir, allowed_exts, max_size, prefix='file'):
    """Save UploadedFile under MEDIA_ROOT/subdir. Returns filename or None."""
    if not uploaded:
        return None
    if uploaded.size > max_size:
        raise ValueError('Fichier trop volumineux.')
    ext = Path(uploaded.name).suffix.lower()
    if ext not in allowed_exts:
        raise ValueError('Format de fichier non autorisé.')
    from django.utils import timezone
    import random
    name = f'{prefix}_{int(timezone.now().timestamp())}_{random.randint(100, 999)}{ext}'
    dest_dir = Path(settings.MEDIA_ROOT) / subdir
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / name
    with open(dest, 'wb+') as out:
        for chunk in uploaded.chunks():
            out.write(chunk)
    return name
