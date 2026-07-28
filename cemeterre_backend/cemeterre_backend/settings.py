import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

# Charger le fichier .env s'il existe
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

# Chemins vers les bibliothèques GDAL et GEOS pour Windows (PostGIS)
GDAL_LIBRARY_PATH = r'C:\Users\DELL\AppData\Local\Programs\OSGeo4W\bin\gdal313.dll'
GEOS_LIBRARY_PATH = r'C:\Users\DELL\AppData\Local\Programs\OSGeo4W\bin\geos_c.dll'

# Clé secrète Django (ne pas partager en production)
SECRET_KEY = 'django-insecure-+j+a_$p=lv=)_(g-gr)vzx#!s1phq#pjgweft&0aac50!7&4y2'

# Mode débogage (mettre à False en production)
DEBUG = True
ALLOWED_HOSTS = ['*']

# ==================== CONFIGURATION MOBILE MONEY ====================
MTN_API_USER = os.getenv('MTN_API_USER', '')
MTN_API_KEY = os.getenv('MTN_API_KEY', '')
MTN_SUBSCRIPTION_KEY = os.getenv('MTN_SUBSCRIPTION_KEY', '')
MTN_ENVIRONMENT = os.getenv('MTN_ENVIRONMENT', 'sandbox')

AIRTEL_CLIENT_ID = os.getenv('AIRTEL_CLIENT_ID', '')
AIRTEL_CLIENT_SECRET = os.getenv('AIRTEL_CLIENT_SECRET', '')
AIRTEL_ENVIRONMENT = os.getenv('AIRTEL_ENVIRONMENT', 'sandbox')

# ==================== APPLICATIONS INSTALLÉES ====================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',          # Pour PostGIS (géolocalisation)
    'corsheaders',                 # Pour les requêtes cross-origin
    'ninja',                       # Django Ninja (API REST)
    'ninja_jwt',                   # Authentification JWT pour Ninja
    'rest_framework',              # Django REST Framework (utilisé pour certains utils)
    'rest_framework_gis',          # Support GIS pour DRF
    
    # Applications du projet
    'users',
    'cemetery',
    'reservations',
    'finance',
    'notifications',
    'reports',
    'alarme',
]

# ==================== MIDDLEWARE ====================
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # Doit être en haut
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    
    # ✅ CORRECTION : Middleware personnalisé pour désactiver CSRF sur l'API (car on utilise JWT)
    # Ce fichier doit exister : cemeterre_backend/middleware.py
    'cemeterre_backend.middleware.DisableCSRFMiddleware',
    
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'cemeterre_backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'cemeterre_backend.wsgi.application'

# ==================== BASE DE DONNÉES (PostgreSQL + PostGIS) ====================
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'cimetiere_db',
        'USER': 'postgres',
        'PASSWORD': 'Cimetiere2026',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# ==================== VALIDATION DES MOTS DE PASSE ====================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ==================== INTERNATIONALISATION ====================
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Kinshasa'
USE_I18N = True
USE_TZ = True

# ==================== FICHIERS STATIQUES ====================
STATIC_URL = 'static/'

# ==================== MODÈLE UTILISATEUR PERSONNALISÉ ====================
AUTH_USER_MODEL = 'users.User'

# ==================== CONFIGURATION REST FRAMEWORK & JWT ====================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
}

# ==================== CORS (Pour autoriser le Frontend) ====================
CORS_ALLOW_ALL_ORIGINS = True

# ==================== CONFIGURATION EMAIL (SMTP) ====================
EMAIL_HOST_USER = 'joealain242@gmail.com'  
EMAIL_HOST_PASSWORD = 'qejhinzlcbmazrwx' 

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# ==================== SÉCURITÉ ====================
X_FRAME_OPTIONS = 'ALLOWALL'

# Tout en bas du fichier
APPEND_SLASH = True  # ✅ Force Django à ajouter les slashes finaux