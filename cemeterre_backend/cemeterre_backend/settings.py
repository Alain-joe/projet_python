"""
Django settings for cemeterre_backend project.
Compatible Django 6.0.x + PostGIS + Sécurisation par .env + Optimisé pour Render
"""
import os
import platform
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')


if platform.system() == "Windows":
    GDAL_LIBRARY_PATH = os.getenv("GDAL_LIBRARY_PATH")
    GEOS_LIBRARY_PATH = os.getenv("GEOS_LIBRARY_PATH")
# Sur Linux (Docker/Render), Django lit GDAL_LIBRARY_PATH depuis
# la variable d'environnement du conteneur (définie dans le Dockerfile)

# ==============================================================================
# SÉCURITÉ
# ==============================================================================
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-fallback-key-change-me-immediately')
DEBUG = os.getenv('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# ==============================================================================
# APPLICATIONS
# ==============================================================================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',  # PostGIS
    
    # Tierces parties
    'corsheaders',
    'ninja',
    'ninja_jwt',
    'whitenoise.runserver_nostatic',  # ✅ Optimisation WhiteNoise pour le dev
    
    # Apps du projet
    'users',
    'cemetery',
    'reservations',
    'finance',
    'reports',
    'notifications',
    'alarme',  # ✅ Ajouté de retour
]

# ==============================================================================
# MIDDLEWARE
# ==============================================================================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # ✅ Ajouté juste après SecurityMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'cemeterre_backend.middleware.DisableCSRFMiddleware',  # ✅ Conservé pour Flet + JWT
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'cemeterre_backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'cemeterre_backend.wsgi.application'

# ==============================================================================
# BASE DE DONNÉES (PostGIS)
# ==============================================================================
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': os.getenv('DB_NAME', 'cimetiere_db'),
        'USER': os.getenv('DB_USER', 'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'postgres'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

# ==============================================================================
# VALIDATION DES MOTS DE PASSE
# ==============================================================================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# =============================================================================
# MODÈLE UTILISATEUR PERSONNALISÉ
# ==============================================================================
AUTH_USER_MODEL = 'users.User'

# ==============================================================================
# INTERNATIONALISATION
# ==============================================================================
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Brazzaville'
USE_I18N = True
USE_TZ = True

# ==============================================================================
# FICHIERS STATIQUES ET MÉDIAS (Optimisé pour Render avec WhiteNoise)
# ==============================================================================
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"  # ✅ Ajouté

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ==============================================================================
# CORS (Cross-Origin Resource Sharing)
# ==============================================================================
CORS_ALLOWED_ORIGINS = os.getenv('CORS_ALLOWED_ORIGINS', 'http://localhost:8550,http://127.0.0.1:8550').split(',')
CORS_ALLOW_CREDENTIALS = True

# ==============================================================================
# CONFIGURATION EMAIL
# ==============================================================================
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('EMAIL_HOST_USER', 'noreply@cimetiere.local')

# ==============================================================================
# CONFIGURATION DES API DE PAIEMENT
# ==============================================================================
MTN_API_USER = os.getenv('MTN_API_USER', '')
MTN_API_KEY = os.getenv('MTN_API_KEY', '')
MTN_SUBSCRIPTION_KEY = os.getenv('MTN_SUBSCRIPTION_KEY', '')
MTN_ENVIRONMENT = os.getenv('MTN_ENVIRONMENT', 'sandbox')

AIRTEL_CLIENT_ID = os.getenv('AIRTEL_CLIENT_ID', '')
AIRTEL_CLIENT_SECRET = os.getenv('AIRTEL_CLIENT_SECRET', '')
AIRTEL_ENVIRONMENT = os.getenv('AIRTEL_ENVIRONMENT', 'sandbox')

# ==============================================================================
# RENDER DEPLOYMENT (HTTPS PROXY)
# ==============================================================================
# Permet à Django de reconnaître les connexions HTTPS derrière le proxy de Render
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
