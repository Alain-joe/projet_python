"""
cemeterre_backend/middleware.py
Désactive la vérification CSRF uniquement pour les requêtes API (JWT)
"""

class DisableCSRFMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Désactive CSRF pour toutes les routes commençant par /api/
        if request.path.startswith('/api/'):
            request._dont_enforce_csrf_checks = True
        return self.get_response(request)