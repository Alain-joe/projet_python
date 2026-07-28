# projet_cimetiere/cemeterre_backend/finance/admin.py

from django.contrib import admin
from .models import Facture, Paiement


@admin.register(Facture)
class FactureAdmin(admin.ModelAdmin):
    list_display = (
        'id', 
        'numero', 
        'client', 
        'montant_total', 
        'statut', 
        'created_at',  # ✅ CORRECTION ICI
        'is_paid_display'
    )
    
    list_filter = ('statut', 'created_at')  # ✅ CORRECTION ICI
    
    search_fields = ('numero', 'client__username', 'client__email')
    
    readonly_fields = (
        'numero', 
        'created_at',  # ✅ CORRECTION ICI
        'montant_paye_display', 
        'montant_restant_display', 
        'is_paid_display'
    )

    @admin.display(description='Entièrement Payée', boolean=True)
    def is_paid_display(self, obj):
        return obj.is_paid

    @admin.display(description='Montant Payé')
    def montant_paye_display(self, obj):
        return f"{obj.montant_paye} XAF"

    @admin.display(description='Reste à Payer')
    def montant_restant_display(self, obj):
        return f"{obj.montant_restant} XAF"


@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
    list_display = ('id', 'facture', 'montant', 'mode_paiement', 'date_paiement', 'traite_par')
    list_filter = ('mode_paiement', 'date_paiement')
    search_fields = ('facture__numero', 'reference')
    readonly_fields = ('date_paiement',)