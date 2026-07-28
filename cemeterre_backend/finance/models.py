# projet_cimetiere/cemeterre_backend/finance/models.py

from django.db import models
from users.models import User
from reservations.models import Reservation
from django.utils import timezone


class Facture(models.Model):
    STATUT_CHOICES = [
        ('en_attente', 'Non payée'),
        ('partielle', 'Partiellement payée'),
        ('payee', 'Payée'),
        ('annulee', 'Annulée'),
    ]

    reservation = models.OneToOneField(Reservation, on_delete=models.CASCADE, related_name='facture')
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='factures')
    numero = models.CharField(max_length=50, unique=True)
    montant_total = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    date_echeance = models.DateField()
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name="Date de paiement complet")

    class Meta:
        verbose_name = "Facture"
        verbose_name_plural = "Factures"
        ordering = ['-created_at']

    def __str__(self):
        return f"Facture {self.numero} - {self.client.username}"

    @property
    def montant_paye(self):
        # Ne somme que les paiements validés
        return sum(p.montant for p in self.paiements.filter(statut_validation='valide'))

    @property
    def montant_restant(self):
        return max(0, float(self.montant_total) - float(self.montant_paye))

    @property
    def is_paid(self):
        return self.montant_restant <= 0

    @property
    def progression(self):
        if float(self.montant_total) == 0:
            return 100
        return round((float(self.montant_paye) / float(self.montant_total)) * 100, 1)

    def update_statut(self):
        """Met à jour le statut de la facture selon les paiements validés."""
        if self.montant_restant <= 0:
            self.statut = 'payee'
            if not self.paid_at:
                self.paid_at = timezone.now()
        elif self.montant_paye > 0:
            self.statut = 'partielle'
        else:
            self.statut = 'en_attente'
        self.save()


class Paiement(models.Model):
    MODE_CHOICES = [
        ('especes', 'Espèces'),
        ('virement', 'Virement bancaire'),
        ('mtn_momo', 'MTN Mobile Money'),
        ('airtel_money', 'Airtel Money'),
    ]
    
    STATUT_VALIDATION_CHOICES = [
        ('en_attente', 'En attente de confirmation'),
        ('valide', 'Validé'),
        ('rejete', 'Rejeté'),
    ]

    facture = models.ForeignKey(Facture, on_delete=models.CASCADE, related_name='paiements')
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    mode_paiement = models.CharField(max_length=20, choices=MODE_CHOICES)
    reference = models.CharField(max_length=100, blank=True, help_text="Référence de transaction")
    date_paiement = models.DateTimeField(auto_now_add=True)
    statut_validation = models.CharField(max_length=20, choices=STATUT_VALIDATION_CHOICES, default='valide')
    traite_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='paiements_traites')

    class Meta:
        verbose_name = "Paiement"
        verbose_name_plural = "Paiements"
        ordering = ['-date_paiement']

    def __str__(self):
        return f"Paiement {self.montant} XAF ({self.mode_paiement}) - {self.facture.numero}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Met à jour le statut de la facture (sans notification, gérée dans api.py)
        self.facture.update_statut()