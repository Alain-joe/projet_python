# projet_cimetiere/cemeterre_backend/core/permissions.py

from functools import wraps
from ninja.errors import HttpError

def require_role(*allowed_roles):
    """
    Décorateur pour restreindre l'accès à certaines routes selon le rôle de l'utilisateur.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            # 1. Vérifier si l'utilisateur est bien connecté (JWT valide)
            if not request.auth:
                raise HttpError(401, "Non authentifié. Veuillez vous connecter.")
            
            # 2. Vérifier si le rôle de l'utilisateur est dans la liste des rôles autorisés
            if request.auth.role not in allowed_roles:
                raise HttpError(
                    403, 
                    f"Accès refusé. Rôles autorisés : {', '.join(allowed_roles)}. Votre rôle : {request.auth.role}"
                )
            
            # 3. Si tout est OK, on laisse passer la requête
            return func(request, *args, **kwargs)
        return wrapper
    return decorator