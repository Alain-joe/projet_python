# projet_cimetiere/cemeterre_backend/cemetery/admin.py

from django.contrib import admin
from .models import Cemetery, Section, Grave, Concession, Exhumation, AuditLog


@admin.register(Cemetery)
class CemeteryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'city', 'total_area', 'calculated_capacity', 'created_at')
    list_filter = ('city',)
    search_fields = ('name', 'city', 'address')


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'cemetery', 'is_exploitable', 'created_at')
    list_filter = ('cemetery', 'is_exploitable')
    search_fields = ('name',)


@admin.register(Grave)
class SectionAdmin(admin.ModelAdmin):
    list_display = ('id', 'code', 'section', 'status', 'grave_type', 'price', 'last_status_change')
    list_filter = ('status', 'grave_type', 'section')
    search_fields = ('code',)


@admin.register(Concession)
class ConcessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'grave', 'user', 'type_concession', 'montant', 'status', 'date_debut')
    list_filter = ('status', 'type_concession')
    search_fields = ('grave__code', 'user__username')


@admin.register(Exhumation)
class ExhumationAdmin(admin.ModelAdmin):
    list_display = ('id', 'grave', 'demandeur', 'status', 'date_prevue', 'date_exhumation', 'created_at')
    list_filter = ('status',)
    search_fields = ('grave__code', 'demandeur__username')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'timestamp', 'user', 'action', 'model_name', 'object_id')
    list_filter = ('action', 'model_name')
    readonly_fields = ('user', 'action', 'model_name', 'object_id', 'details', 'timestamp')
    # AuditLog est immuable : pas de modification possible
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False