# projet_cimetiere/cemeterre_backend/alarme/models.py

from django.db import models
from users.models import User
from reservations.models import Reservation
from finance.models import Facture
from cemetery.models import Concession, Exhumation


class Alarm(models.Model):
    TYPE_CHOICES = [
        ("concession_expiration", "Concession expirante"),
        ("payment_delay", "Retard de paiement"),
        ("reservation_pending", "Réservation en attente de validation"),
        ("exhumation_pending", "Exhumation en attente de validation"),
        ("system_critical", "Alerte système critique"),
    ]

    STATUS_CHOICES = [
        ("active", "Active"),
        ("resolved", "Résolue"),
        ("ignored", "Ignorée"),
    ]

    type_alarm = models.CharField(max_length=50, choices=TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    message = models.TextField()

    # L'utilisateur concerné par l'alarme
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="alarms")

    # Liens vers les objets métier (Optionnels mais cruciaux pour le CDC)
    reservation = models.ForeignKey(Reservation, null=True, blank=True, on_delete=models.SET_NULL)
    facture = models.ForeignKey(Facture, null=True, blank=True, on_delete=models.SET_NULL)
    concession = models.ForeignKey(Concession, null=True, blank=True, on_delete=models.SET_NULL)
    exhumation = models.ForeignKey(Exhumation, null=True, blank=True, on_delete=models.SET_NULL)

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Alarme"
        verbose_name_plural = "Alarmes"

    def __str__(self):
        return f"[{self.get_type_alarm_display()}] - {self.user.username} - {self.status}"