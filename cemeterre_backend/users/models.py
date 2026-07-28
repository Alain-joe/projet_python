"""
users/models.py — Modèle User étendu avec RBAC, MFA et Audit Trail.
Compatible Django 6.0.5
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
import random
import string


class User(AbstractUser):
    """
    Modèle utilisateur personnalisé avec RBAC et MFA.
    """

    ROLE_CHOICES = (
        ('admin', 'Administrateur'),
        ('agent', 'Agent de terrain'),
        ('secretariat', 'Secrétariat'),
        ('client', 'Client'),
    )

    SEX_CHOICES = (
        ('M', 'Masculin'),
        ('F', 'Féminin'),
        ('O', 'Autre'),
        ('N', 'Non renseigné'),
    )

    # --- Champs d'identité ---
    first_name = models.CharField(max_length=100, blank=False, null=False, verbose_name="Prénom")
    last_name = models.CharField(max_length=100, blank=False, null=False, verbose_name="Nom")
    email = models.EmailField(unique=True, blank=False, null=False, verbose_name="Email")

    # --- Champs personnels ---
    sex = models.CharField(max_length=1, choices=SEX_CHOICES, default='N', verbose_name="Sexe")
    birth_date = models.DateField(null=True, blank=True, verbose_name="Date de naissance")

    # --- Téléphone (format international +242XXXXXXXX) ---
    phone = models.CharField(max_length=13, blank=True, default='', verbose_name="Téléphone")

    # --- Rôle et approbation ---
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='client', verbose_name="Rôle")
    is_approved = models.BooleanField(default=False, verbose_name="Approuvé par l'admin")

    # --- Champs MFA ---
    mfa_code = models.CharField(max_length=6, blank=True, null=True)
    mfa_code_expires_at = models.DateTimeField(blank=True, null=True)
    mfa_verified = models.BooleanField(default=False)

    # --- Audit Trail et Sécurité ---
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Dernière modification")
    last_password_change = models.DateTimeField(null=True, blank=True, verbose_name="Dernier changement de mot de passe")
    must_change_password = models.BooleanField(default=False, verbose_name="Doit changer le mot de passe")

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"
        ordering = ['-date_joined']

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.username})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def age(self):
        """Calcule l'âge à partir de la date de naissance."""
        if not self.birth_date:
            return None
        today = timezone.now().date()
        age = today.year - self.birth_date.year - (
            (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
        )
        return age

    # --- MFA ---
    def generate_mfa_code(self):
        """Génère un code OTP à 6 chiffres valable 10 minutes."""
        self.mfa_code = ''.join(random.choices(string.digits, k=6))
        self.mfa_code_expires_at = timezone.now() + timezone.timedelta(minutes=10)
        self.mfa_verified = False
        self.save(update_fields=['mfa_code', 'mfa_code_expires_at', 'mfa_verified'])
        return self.mfa_code

    def verify_mfa_code(self, code):
        """Vérifie que le code est correct et non expiré."""
        if self.mfa_code == code and timezone.now() < self.mfa_code_expires_at:
            self.mfa_verified = True
            self.mfa_code = None
            self.mfa_code_expires_at = None
            self.save(update_fields=['mfa_verified', 'mfa_code', 'mfa_code_expires_at'])
            return True
        return False