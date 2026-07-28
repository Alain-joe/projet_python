"""
cemetery/management/commands/send_expiration_notifications.py
Commande Django pour envoyer automatiquement les notifications d'expiration.
À exécuter via Cron : python manage.py send_expiration_notifications
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from cemetery.models import Concession
# ✅ CORRECTION : notifier_concession_expiration (pas conscription)
from notifications.utils_extended import notifier_concession_expiration, notifier_concession_expiree


class Command(BaseCommand):
    help = "Envoie les notifications pour les concessions arrivant à expiration"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simule l\'envoi sans créer de notifications',
        )

    def handle(self, *args, **options):
        today = timezone.now().date()
        dry_run = options.get('dry_run', False)
        
        results = {
            "notified_90": 0,
            "notified_30": 0,
            "expired": 0,
            "errors": 0
        }

        self.stdout.write("🔍 Vérification des concessions à échéance...")
        if dry_run:
            self.stdout.write(self.style.WARNING("Mode simulation (dry-run) activé"))

        # 1. Notifications J-90
        concessions_90 = Concession.objects.filter(
            status="active",
            type_concession__in=['temporaire', 'trentenaire', 'cinquantenaire'],
            date_fin__lte=today + timedelta(days=90),
            date_fin__gt=today + timedelta(days=89)
        ).select_related("user", "grave")
        
        self.stdout.write(f"📅 {concessions_90.count()} concession(s) à J-90")
        
        for c in concessions_90:
            try:
                if not dry_run:
                    notifier_concession_expiration(c, days_before=90)
                results["notified_90"] += 1
                self.stdout.write(f"  ✓ J-90 : {c.grave.code} - {c.user.username}")
            except Exception as e:
                results["errors"] += 1
                self.stderr.write(f"  ✗ Erreur J-90 {c.id}: {e}")

        # 2. Notifications J-30 (urgence)
        concessions_30 = Concession.objects.filter(
            status="active",
            type_concession__in=['temporaire', 'trentenaire', 'cinquantenaire'],
            date_fin__lte=today + timedelta(days=30),
            date_fin__gt=today + timedelta(days=29)
        ).select_related("user", "grave")
        
        self.stdout.write(f"⚠️ {concessions_30.count()} concession(s) à J-30")
        
        for c in concessions_30:
            try:
                if not dry_run:
                    notifier_concession_expiration(c, days_before=30)
                results["notified_30"] += 1
                self.stdout.write(f"  ✓ J-30 : {c.grave.code} - {c.user.username}")
            except Exception as e:
                results["errors"] += 1
                self.stderr.write(f"  ✗ Erreur J-30 {c.id}: {e}")

        # 3. Expiration automatique (date_fin < aujourd'hui)
        expired_concessions = Concession.objects.filter(
            status="active",
            type_concession__in=['temporaire', 'trentenaire', 'cinquantenaire'],
            date_fin__lt=today
        ).select_related("user", "grave")
        
        self.stdout.write(f"🔴 {expired_concessions.count()} concession(s) à expirer")
        
        for c in expired_concessions:
            try:
                if not dry_run:
                    c.status = "expired"
                    c.save(update_fields=["status"])
                    notifier_concession_expiree(c)
                results["expired"] += 1
                self.stdout.write(f"  ✓ Expirée : {c.grave.code} - {c.user.username}")
            except Exception as e:
                results["errors"] += 1
                self.stderr.write(f"  ✗ Erreur expiration {c.id}: {e}")

        # Résumé
        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Vérification terminée :\n"
            f"  • Notifications J-90 : {results['notified_90']}\n"
            f"  • Notifications J-30 : {results['notified_30']}\n"
            f"  • Concessions expirées : {results['expired']}\n"
            f"  • Erreurs : {results['errors']}"
        ))