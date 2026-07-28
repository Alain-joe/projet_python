# projet_cimetiere/cemeterre_backend/cemetery/audit.py

from django.utils import timezone


def log_action(user, action, model_name, object_id, details=""):
    """Enregistre une action dans le journal d'audit (CDC : traçabilité immuable)"""
    from .models import AuditLog
    
    AuditLog.objects.create(
        user=user,
        action=action,
        model_name=model_name,
        object_id=object_id,
        details=details,
        timestamp=timezone.now()
    )