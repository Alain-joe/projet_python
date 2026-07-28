"""
projet_cimetiere/cemeterre_backend/reservations/models.py
Modèle de réservation conforme au cahier des charges.
Gère automatiquement les transitions de statut et le verrouillage des caveaux.
"""
from django.db import models
from users.models import User
from cemetery.models import Grave
from django.utils import timezone
from django.core.exceptions import ValidationError


class Reservation(models.Model):
    """
    Modèle de réservation de caveau.
    Workflow : pending → confirmed → (paiement) → occupied
              pending → cancelled → available
    """
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('confirmed', 'Confirmée'),
        ('cancelled', 'Annulée'),
        ('inhumee', 'Inhumée'), 
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reservations")
    grave = models.ForeignKey(Grave, on_delete=models.CASCADE, related_name="reservations")
    # Ajoute ce champ dans la classe :
    date_prevue_inhumation = models.DateField(
    null=True, 
    blank=True, 
    verbose_name="Date prévue d'inhumation"
)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reservation_date = models.DateTimeField(auto_now_add=True)

    note = models.TextField(blank=True, null=True)

    # Informations sur le défunt
    deceased_first_name = models.CharField(max_length=100, blank=True, null=True)
    deceased_last_name = models.CharField(max_length=100, blank=True, null=True)
    deceased_birth_date = models.DateField(blank=True, null=True)
    deceased_death_date = models.DateField(blank=True, null=True)

    # Dates de suivi
    confirmed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-reservation_date']
        verbose_name = "Réservation"
        verbose_name_plural = "Réservations"

    def clean(self):
        """Validation métier avant sauvegarde"""
        if self.status == 'pending' and self.grave.status != 'available':
            raise ValidationError("Ce caveau n'est pas disponible pour réservation.")

    def save(self, *args, **kwargs):
        """
        Logique de sauvegarde avec gestion automatique des statuts et du caveau.
        """
        is_new = self.pk is None
        old_instance = Reservation.objects.filter(pk=self.pk).first() if not is_new else None
        old_status = old_instance.status if old_instance else None

        # 1. À la création : verrouiller le caveau en 'reserved'
        if is_new and self.status == 'pending':
            if self.grave.status != 'available':
                raise ValidationError("Ce caveau n'est pas disponible.")
            self.grave.status = 'reserved'
            self.grave.save(update_fields=['status', 'last_status_change'])

        # 2. Transition pending → confirmed : le caveau reste 'reserved' en attendant le paiement
        if old_status == 'pending' and self.status == 'confirmed':
            self.confirmed_at = timezone.now()
            self.grave.status = 'reserved'
            self.grave.save(update_fields=['status', 'last_status_change'])

        # 3. Transition vers inhumee : le caveau devient définitivement 'occupied'
        if self.status == 'inhumee' and old_status != 'inhumee':
            self.grave.status = 'occupied'
            self.grave.save(update_fields=['status', 'last_status_change'])

        # 4. Transition vers cancelled : libérer le caveau
        if self.status == 'cancelled' and old_status != 'cancelled':
            self.grave.status = 'available'
            self.grave.save(update_fields=['status', 'last_status_change'])
            self.cancelled_at = timezone.now()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Réservation {self.id} - {self.user.username} - Caveau {self.grave.code}"

    @property
    def is_pending(self):
        return self.status == 'pending'

    @property
    def is_confirmed(self):
        return self.status == 'confirmed'

    @property
    def is_cancelled(self):
        return self.status == 'cancelled'