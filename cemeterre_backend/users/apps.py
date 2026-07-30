"""
users/apps.py — Configuration de l'app users.
Ajout d'un signal post_migrate qui garantit qu'un compte admin par
défaut existe toujours, même après un `flush` de la base de données.
CORRECTION : Lecture des identifiants admin depuis les variables d'environnement.
"""
import os
from django.apps import AppConfig
from django.db.models.signals import post_migrate
from dotenv import load_dotenv

load_dotenv()


def create_default_admin(sender, **kwargs):
    """
    Crée automatiquement un compte admin par défaut s'il n'existe pas.
    Se déclenche après chaque migrate ou flush.
    """
    from .models import User
    from django.conf import settings

    # Récupération des identifiants depuis settings (qui lit depuis .env)
    username = getattr(settings, "DEFAULT_ADMIN_USERNAME", "admin")
    email = getattr(settings, "DEFAULT_ADMIN_EMAIL", "admin@cimetiere-connect.local")
    password = getattr(settings, "DEFAULT_ADMIN_PASSWORD", "Admin123!")

    # Vérifier si l'admin existe déjà
    if not User.objects.filter(username=username).exists():
        User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
            first_name="Admin",
            last_name="Système",
            role="admin",
            is_approved=True,
        )
        print("\n" + "="*60)
        print("✅ COMPTE ADMIN PAR DÉFAUT CRÉÉ AVEC SUCCÈS")
        print("="*60)
        print(f"👤 Username : {username}")
        print(f"🔑 Password : {password}")
        print(f"📧 Email    : {email}")
        print("="*60 + "\n")


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "users"

    def ready(self):
        """
        Connecte le signal post_migrate à la fonction create_default_admin.
        """
        post_migrate.connect(create_default_admin, sender=self)