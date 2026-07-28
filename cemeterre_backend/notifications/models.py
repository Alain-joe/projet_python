from django.db import models
from users.models import User


class Notification(models.Model):

    TYPE_CHOICES = [
        ('nouvelle_reservation', 'Nouvelle réservation'),
        ('retard_paiement', 'Retard de paiement'),
        ('concession_expirante', 'Concession expirante'),
        ('reservation_validee', 'Réservation validée'),
        ('reservation_annulee', 'Réservation annulée'),
        ('facture_payee', 'Facture payée'),
        ('exhumation_validee', 'Exhumation validée'),
        ('concession_creee', 'Concession créée'),
        ('concession_expiree', 'Concession expirée'),
        ('inhumation_confirmee', 'Inhumation confirmée'),
        # ✅ NOUVEAU : Pour le workflow de signalement de caveaux non exploitables
        ('signalement_caveau', 'Signalement de caveau'),
    ]

    destinataire = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')

    type_notification = models.CharField(max_length=50, choices=TYPE_CHOICES)

    titre = models.CharField(max_length=200)
    message = models.TextField()

    lu = models.BooleanField(default=False)

    is_system = models.BooleanField(default=True)
    reference_id = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.type_notification} → {self.destinataire.username}"