"""
projet_cimetiere/cemeterre_backend/cemeterre_backend/urls.py
Configuration principale des URLs du projet.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from .api import api
from cemetery.views import map_view, map_setup_view, graves_geojson

urlpatterns = [
    # 1. Interface d'administration Django
    path('admin/', admin.site.urls),

    # 2. API Django Ninja (DOIT être déclaré avant les routes génériques ou statiques)
    path('api/', api.urls),

    # 3. Routes spécifiques de la carte (si elles ne sont pas incluses dans l'API Ninja)
    path('map/', map_view, name='carte'),
    path('map/setup/', map_setup_view, name='map_setup'),  # ✅ AJOUT
    path('api/cemetery/graves-geojson/', graves_geojson, name='graves_geojson'),

    # 4. Autres applications (décommenter si nécessaire)
    # path('api/cemetery/', include('cemetery.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)