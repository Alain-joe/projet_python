"""
projet_cimetiere/cemeterre_backend/cemeterre_backend/api.py
Configuration centrale de l'API Ninja.
CORRECTION : Suppression du slash final dans le préfixe du routeur finance_reports 
pour éviter les doubles slashes dans les URLs (ex: /cemetery//finance/...).
"""
from ninja import NinjaAPI
from ninja_jwt.authentication import JWTAuth

# ==============================================================================
# 1. IMPORTATION DES MODULES STANDARDS
# ==============================================================================
from users.api import router as users_router
from reservations.api import router as reservations_router
from finance.api import router as finance_router
from reports.api import router as reports_router

# ✅ Import du routeur des rapports financiers
from finance.api_reports import router as finance_reports_router

# Modules optionnels (protégés pour éviter les erreurs s'ils n'existent pas encore)
try:
    from notifications.api import router as notifications_router
except ImportError:
    notifications_router = None

try:
    from alarme.api import router as alarme_router
except ImportError:
    alarme_router = None


# ==============================================================================
# 2. IMPORTATION DES MODULES CEMETERY (Structure éclatée et validée)
# ==============================================================================
from cemetery.api_cemetery import router as cemetery_router_1
from cemetery.api_sections import router as cemetery_router_2
from cemetery.api_graves import router as cemetery_router_3
from cemetery.api_concessions import router as cemetery_router_4
from cemetery.api_exhumations import router as cemetery_router_5
from cemetery.api_inhumations import router as cemetery_router_6
from cemetery.api_graves_signalements import router as graves_signalements_router



# ✅ Import du routeur d'audit (journal des logs)
from cemetery.api_audit import router as audit_router


# ==============================================================================
# 3. CONFIGURATION DE L'API PRINCIPALE
# ==============================================================================
api = NinjaAPI(
    title="API Gestion de Cimetière",
    version="1.0.0",
    description="API REST du système de gestion de cimetière - GI2 2026",
    auth=JWTAuth(),
    docs_url="docs",              # Chemin relatif (sera /api/docs)
    openapi_url="openapi.json",   # Chemin relatif (sera /api/openapi.json)
)


# ==============================================================================
# 4. ENREGISTREMENT DES ROUTEURS
# ==============================================================================
api.add_router("/users", users_router)

# Enregistrement de tous les routeurs Cemetery sous le même préfixe "/cemetery"
api.add_router("/cemetery", cemetery_router_1)
api.add_router("/cemetery", cemetery_router_2)
api.add_router("/cemetery", cemetery_router_3)
api.add_router("/cemetery", cemetery_router_4)
api.add_router("/cemetery", cemetery_router_5)
api.add_router("/cemetery", cemetery_router_6)
api.add_router("/cemetery", graves_signalements_router)

# ✅ CORRECTION : Suppression du slash final pour éviter "/cemetery//finance/..."
api.add_router("/cemetery", finance_reports_router)

api.add_router("/reservations", reservations_router)
api.add_router("/finance", finance_router)
api.add_router("/reports", reports_router)

# Enregistrement du routeur d'audit (créera l'URL /api/audit/...)
api.add_router("/audit", audit_router)

# Enregistrement conditionnel des modules optionnels
if notifications_router:
    api.add_router("/notifications", notifications_router)

if alarme_router:
    api.add_router("/alarme", alarme_router)