# projet_cimetiere/cemeterre_backend/core/audit.py

from cemetery.models import AuditLog

def log_action(user, action, model_name, object_id=None, details=""):
    """Enregistre une action dans le journal immuable (Audit Trail)"""
    AuditLog.objects.create(
        user=user,
        action=action,
        model_name=model_name,
        object_id=object_id,
        details=details
    )