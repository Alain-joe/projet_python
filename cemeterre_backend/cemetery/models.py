"""
projet_cimetiere/cemeterre_backend/cemetery/models.py
Modèles du module Cimetière avec gestion complète des concessions et signalements.
"""

from django.db import models
from django.contrib.gis.db import models as gis_models
from users.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError


class Cemetery(models.Model):
    """Modèle singleton pour gérer UN SEUL cimetière."""
    name = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    address = models.CharField(max_length=300)
    
    latitude = models.FloatField(
        help_text="Latitude du centre du cimetière",
        null=True, blank=True
    )
    longitude = models.FloatField(
        help_text="Longitude du centre du cimetière",
        null=True, blank=True
    )
    
    total_area = models.FloatField(help_text="Superficie totale en m²")
    non_exploitable_area = models.FloatField(
        default=0,
        help_text="Zones non exploitables en m²"
    )
    longueur_totale = models.FloatField(default=100, help_text="Longueur totale (m)")
    largeur_totale = models.FloatField(default=100, help_text="Largeur totale (m)")
    
    grave_length = models.FloatField(default=2.5, help_text="Longueur standard caveau (m)")
    grave_width = models.FloatField(default=1.2, help_text="Largeur standard caveau (m)")
    
    espacement_caveaux = models.FloatField(
        default=0.5,
        help_text="Espacement entre les caveaux en mètres (pour circulation et entretien)"
    )
    
    calculated_capacity = models.IntegerField(
        null=True, blank=True,
        help_text="Nombre théorique de places"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cimetière"
        verbose_name_plural = "Cimetières"

    def __str__(self):
        return f"{self.name} - {self.city}"

    def clean(self):
        super().clean()
        if self.pk is None and Cemetery.objects.exists():
            raise ValidationError("Un seul cimetière peut être créé.")
        if self.latitude is not None and not (-90 <= self.latitude <= 90):
            raise ValidationError("Latitude invalide.")
        if self.longitude is not None and not (-180 <= self.longitude <= 180):
            raise ValidationError("Longitude invalide.")
        if self.total_area <= 0:
            raise ValidationError("Superficie invalide.")

    def save(self, *args, **kwargs):
        self.full_clean()
        if self.total_area and self.grave_length and self.grave_width:
            usable_area = self.total_area - self.non_exploitable_area
            grave_area = (self.grave_length + self.espacement_caveaux) * (self.grave_width + self.espacement_caveaux)
            if grave_area > 0:
                self.calculated_capacity = int(usable_area / grave_area)
        super().save(*args, **kwargs)


class Section(models.Model):
    """Section du cimetière (zone exploitable délimitée par les allées)."""
    cemetery = models.ForeignKey(Cemetery, on_delete=models.CASCADE, related_name='sections')
    name = models.CharField(max_length=100)
    is_exploitable = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    
    longueur = models.FloatField(default=50, help_text="Longueur (m)")
    largeur = models.FloatField(default=20, help_text="Largeur (m)")
    zone_non_exploitable = models.FloatField(default=0, help_text="Zone non exploitable (m²)")
    
    polygon_coords = models.JSONField(
        null=True, blank=True,
        help_text="Coordonnées GPS du polygone de la section : [[lat1, lon1], [lat2, lon2], ...]"
    )
    surface_calculee = models.FloatField(
        null=True, blank=True,
        help_text="Surface calculée automatiquement en m²"
    )
    capacite_caveaux = models.IntegerField(
        null=True, blank=True,
        help_text="Nombre de caveaux calculé automatiquement"
    )
    ordre = models.IntegerField(
        default=0,
        help_text="Ordre de la section pour le nommage automatique"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['cemetery', 'name']
        ordering = ['ordre', 'name']

    def __str__(self):
        return f"{self.name} ({self.cemetery.name})"

    def calculate_capacity(self):
        """Calcule la capacité de caveaux pour cette section."""
        if not self.surface_calculee or not self.cemetery:
            return 0
        
        cemetery = self.cemetery
        grave_area = (cemetery.grave_length + cemetery.espacement_caveaux) * (cemetery.grave_width + cemetery.espacement_caveaux)
        
        if grave_area > 0:
            return int(self.surface_calculee / grave_area)
        return 0


class Allee(models.Model):
    """Allée du cimetière (zone non exploitable qui découpe les sections)."""
    TYPE_CHOICES = [
        ('principale', 'Principale'),
        ('secondaire', 'Secondaire'),
        ('sentier', 'Sentier'),
    ]
    
    cemetery = models.ForeignKey(Cemetery, on_delete=models.CASCADE, related_name='allees')
    nom = models.CharField(max_length=100)
    type_allee = models.CharField(max_length=20, choices=TYPE_CHOICES, default='secondaire')
    largeur = models.FloatField(default=3.0, help_text="Largeur de l'allée en mètres")
    
    coordinates = models.JSONField(
        help_text="Coordonnées GPS du tracé : [[lat1, lon1], [lat2, lon2], ...]"
    )
    
    surface_calculee = models.FloatField(
        null=True, blank=True,
        help_text="Surface de l'allée en m² (calculée automatiquement)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Allée"
        verbose_name_plural = "Allées"
        ordering = ['type_allee', 'nom']

    def __str__(self):
        return f"{self.nom} ({self.get_type_allee_display()})"


class Grave(models.Model):
    STATUS_CHOICES = [
        ('available', 'Disponible'),
        ('reserved', 'Réservé'),
        ('occupied', 'Occupé'),
        ('non_exploitable', 'Non exploitable'),
    ]
    
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='graves')
    code = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    grave_type = models.CharField(max_length=50, blank=True)
    length = models.FloatField(default=2.5)
    width = models.FloatField(default=1.2)
    capacity = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True)
    
    location = gis_models.PointField(null=True, blank=True, srid=4326)
    
    # ✅ NOUVEAUX CHAMPS pour la gestion des caveaux non exploitables
    motif_non_exploitable = models.TextField(
        blank=True,
        help_text="Motif de la non-exploitabilité (ex: effondrement, fissures, etc.)"
    )
    date_non_exploitable = models.DateTimeField(
        null=True, blank=True,
        help_text="Date de passage au statut non exploitable"
    )
    non_exploitable_par = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='graves_declares_non_exploitables',
        help_text="Administrateur qui a déclaré le caveau non exploitable"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_status_change = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.get_status_display()}"


class CaveauSignalement(models.Model):
    """
    Signalement d'un problème sur un caveau par un agent de terrain.
    Workflow : Agent signale → Admin valide/rejette → Caveau devient non exploitable si validé.
    """
    STATUT_CHOICES = [
        ('en_attente', 'En attente de validation'),
        ('valide', 'Validé'),
        ('rejete', 'Rejeté'),
    ]
    
    grave = models.ForeignKey(Grave, on_delete=models.CASCADE, related_name='signalements')
    motif = models.TextField(help_text="Description du problème constaté")
    description = models.TextField(blank=True, help_text="Détails supplémentaires")
    
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')
    
    # Métadonnées de traçabilité
    signale_par = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='signalements_creees',
        help_text="Agent qui a signalé le problème"
    )
    valide_par = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='signalements_valides',
        help_text="Administrateur qui a validé/rejeté"
    )
    motif_rejet = models.TextField(blank=True, help_text="Motif du rejet si applicable")
    
    date_signalement = models.DateTimeField(auto_now_add=True)
    date_validation = models.DateTimeField(null=True, blank=True)
    
    photos = models.JSONField(
        null=True, blank=True,
        help_text="URLs des photos jointes au signalement"
    )

    class Meta:
        ordering = ['-date_signalement']
        verbose_name = "Signalement de caveau"
        verbose_name_plural = "Signalements de caveaux"

    def __str__(self):
        return f"Signalement {self.grave.code} - {self.get_statut_display()}"


class Concession(models.Model):
    """
    Concession funéraire - Contrat d'utilisation d'un caveau.
    Conforme CDC §2.5 : Attribution, renouvellement, résiliation.
    """
    TYPE_CHOICES = [
        ('temporaire', 'Temporaire'),
        ('trentenaire', 'Trentenaire (30 ans)'),
        ('cinquantenaire', 'Cinquantenaire (50 ans)'),
        ('perpetuelle', 'Perpétuelle'),
    ]
    STATUS_CHOICES = [
        ('en_attente_creation', 'En attente de création'),
        ('active', 'Active'),
        ('expired', 'Expirée'),
        ('resiliee', 'Résiliée'),
    ]
    
    grave = models.OneToOneField(Grave, on_delete=models.CASCADE, related_name='concession')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='concessions')
    type_concession = models.CharField(max_length=20, choices=TYPE_CHOICES, default='temporaire')
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    date_debut = models.DateField()
    
    duree_annees = models.IntegerField(
        null=True, blank=True,
        help_text="Durée en années (temporaire uniquement)"
    )
    
    date_fin = models.DateField(null=True, blank=True)
    is_paid = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='en_attente_creation')
    
    contrat_document = models.FileField(
        upload_to='concessions/contrats/',
        null=True, blank=True,
        help_text="PDF du contrat signé"
    )
    
    renewed_count = models.IntegerField(default=0, help_text="Nombre de renouvellements")
    last_renewal_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Concession"
        verbose_name_plural = "Concessions"

    def __str__(self):
        return f"Concession {self.grave.code} ({self.user.username})"

    def save(self, *args, **kwargs):
        """Calcul automatique de la date de fin selon le type de concession"""
        if self.type_concession == 'perpetuelle':
            self.date_fin = None
            self.duree_annees = None
        elif self.type_concession == 'trentenaire':
            from datetime import timedelta
            self.duree_annees = 30
            if not self.date_fin:
                self.date_fin = self.date_debut + timedelta(days=30 * 365)
        elif self.type_concession == 'cinquantenaire':
            from datetime import timedelta
            self.duree_annees = 50
            if not self.date_fin:
                self.date_fin = self.date_debut + timedelta(days=50 * 365)
        elif self.type_concession == 'temporaire':
            if self.duree_annees and not self.date_fin:
                from datetime import timedelta
                self.date_fin = self.date_debut + timedelta(days=self.duree_annees * 365)
        
        super().save(*args, **kwargs)

    @property
    def days_remaining(self):
        """Jours restants avant expiration (None si perpétuelle ou expirée)"""
        if self.type_concession == 'perpetuelle' or not self.date_fin:
            return None
        delta = self.date_fin - timezone.now().date()
        return delta.days

    @property
    def is_expiring_soon(self):
        """True si expiration dans <= 90 jours"""
        days = self.days_remaining
        return days is not None and 0 <= days <= 90

    @property
    def is_expired(self):
        """True si la date de fin est dépassée"""
        if not self.date_fin:
            return False
        return self.date_fin < timezone.now().date()


class ConcessionRenewal(models.Model):
    """
    Historique des renouvellements de concession.
    Conforme CDC §2.5 : Archivage et traçabilité.
    """
    concession = models.ForeignKey(
        Concession, 
        on_delete=models.CASCADE, 
        related_name='renewals'
    )
    ancienne_date_fin = models.DateField()
    nouvelle_date_fin = models.DateField()
    duree_extension_annees = models.IntegerField()
    montant_paye = models.DecimalField(max_digits=10, decimal_places=2)
    facture = models.ForeignKey(
        'finance.Facture',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='concession_renewals'
    )
    renewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='concession_renewals_done'
    )
    date_renouvellement = models.DateTimeField(auto_now_add=True)
    observations = models.TextField(blank=True)

    class Meta:
        ordering = ['-date_renouvellement']
        verbose_name = "Renouvellement de concession"

    def __str__(self):
        return f"Renouvellement {self.concession.grave.code} - {self.date_renouvellement.strftime('%d/%m/%Y')}"


class Inhumation(models.Model):
    """Acte physique et légal d'enterrement."""
    grave = models.ForeignKey(Grave, on_delete=models.PROTECT, related_name="inhumations")
    concession = models.ForeignKey(
        Concession, 
        on_delete=models.SET_NULL, 
        null=True, blank=True, 
        related_name="inhumations"
    )
    
    reservation = models.OneToOneField(
        'reservations.Reservation',
        on_delete=models.PROTECT,
        null=True, 
        blank=True,
        related_name="inhumation_record" 
    )
    
    defunt_prenom = models.CharField(max_length=100)
    defunt_nom = models.CharField(max_length=100)
    defunt_date_naissance = models.DateField(null=True, blank=True)
    defunt_date_deces = models.DateField()
    
    date_inhumation = models.DateTimeField(default=timezone.now)
    agent_inhumation = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name="inhumations_realisees"
    )
    observations = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Inhumation"
        ordering = ['-date_inhumation']

    def __str__(self):
        return f"Inhumation de {self.defunt_nom} {self.defunt_prenom} au caveau {self.grave.code}"


class Exhumation(models.Model):
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('approved', 'Approuvée'),
        ('rejected', 'Rejetée'),
        ('completed', 'Effectuée'),
    ]
    
    inhumation = models.ForeignKey(
        Inhumation, 
        on_delete=models.PROTECT, 
        null=True, blank=True, 
        related_name="exhumations"
    )
    grave = models.ForeignKey(Grave, on_delete=models.CASCADE, related_name="exhumations")
    demandeur = models.ForeignKey(User, on_delete=models.CASCADE, related_name="exhumations_demandees")
    
    motif = models.TextField()
    date_prevue = models.DateField()
    date_exhumation = models.DateField(null=True, blank=True)
    motif_rejet = models.TextField(blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    observations = models.TextField(blank=True)
    
    pv_document = models.FileField(upload_to='exhumations/pv/', null=True, blank=True)
    autorisation_document = models.FileField(upload_to='exhumations/autorisations/', null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    validated_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, blank=True, 
        related_name='exhumations_validees'
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        nom = self.inhumation.defunt_nom if self.inhumation else "Inconnu"
        return f"Exhumation {nom} - {self.grave.code}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_status = None
        if not is_new:
            old_instance = Exhumation.objects.filter(pk=self.pk).first()
            old_status = old_instance.status if old_instance else None
            
        if self.status == 'completed' and old_status != 'completed':
            self.grave.status = 'available'
            self.grave.last_status_change = timezone.now()
            self.grave.save()
            
            if self.inhumation and self.inhumation.concession:
                self.inhumation.concession.status = 'resiliee'
                self.inhumation.concession.save()
                
        super().save(*args, **kwargs)


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('create', 'Création'),
        ('update', 'Modification'),
        ('delete', 'Suppression'),
        ('status_change', 'Changement de statut'),
        ('login', 'Connexion'),
        ('payment', 'Paiement'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100)
    object_id = models.IntegerField(null=True, blank=True)
    details = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.timestamp} - {self.action} - {self.model_name}"