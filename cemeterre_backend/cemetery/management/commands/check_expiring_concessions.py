"""
cemetery/management/commands/check_expiring_concessions.py
Commande Django pour vérifier automatiquement les concessions arrivant à échéance.
À exécuter via Cron ou Celery (ex: python manage.py check_expiring_concessions)
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from cemetery.models import Concession
from cemetery.emails import send_expiration_alert_email


class Command(BaseCommand):
    help = "Vérifie les concessions arrivant à échéance et envoie des alertes"

    def handle(self, *args, **options):
        today = timezone.now().date()
        results = {"emails_sent_90": 0, "emails_sent_30": 0, "expired": 0}

        self.stdout.write("🔍 Vérification des concessions à échéance...")

        # 1. Notifications J-90
        concessions_90 = Concession.objects.filter(
            status="active",
            type_concession__in=['temporaire', 'trentenaire', 'cinquantenaire'],
            date_fin__lte=today + timedelta(days=90),
            date_fin__gt=today + timedelta(days=89)
        ).select_related("user", "grave")
        
        for c in concessions_90:
            if c.user.email:
                try:
                    send_expiration_alert_email(c, days=90)
                    results["emails_sent_90"] += 1
                except Exception as e:
                    self.stderr.write(f"⚠️ Erreur email J-90 pour {c.id}: {e}")

        # 2. Notifications J-30
        concessions_30 = Concession.objects.filter(
            status="active",
            type_concession__in=['temporaire', 'trentenaire', 'cinquantenaire'],
            date_fin__lte=today + timedelta(days=30),
            date_fin__gt=today + timedelta(days=29)
        ).select_related("user", "grave")
        
        for c in concessions_30:
            if c.user.email:
                try:
                    send_expiration_alert_email(c, days=30)
                    results["emails_sent_30"] += 1
                except Exception as e:
                    self.stderr.write(f"⚠️ Erreur email J-30 pour {c.id}: {e}")

        # 3. Expiration automatique (date_fin < aujourd'hui)
        expired_concessions = Concession.objects.filter(
            status="active",
            type_concession__in=['temporaire', 'trentenaire', 'cinquantenaire'],
            date_fin__lt=today
        )
        
        count_expired = expired_concessions.update(status="expired")
        results["expired"] = count_expired

        self.stdout.write(self.style.SUCCESS(
            f"✅ Vérification terminée : {results['emails_sent_90']} alertes J-90, "
            f"{results['emails_sent_30']} alertes J-30, {results['expired']} concessions expirées."
        ))