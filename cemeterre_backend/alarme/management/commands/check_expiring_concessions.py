# projet_cimetiere/cemeterre_backend/alarme/management/commands/check_expiring_concessions.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from cemetery.models import Concession
from alarme.models import Alarm
from users.models import User

class Command(BaseCommand):
    help = 'Vérifie automatiquement les concessions expirant dans les 90 prochains jours et crée des alarmes'

    def handle(self, *args, **kwargs):
        today = timezone.now().date()
        warning_date = today + timedelta(days=90) # Alerte 3 mois avant
        
        # Trouver les concessions actives qui expirent bientôt
        expiring_concessions = Concession.objects.filter(
            status='active',
            date_fin__lte=warning_date,
            date_fin__gte=today
        )

        count = 0
        for concession in expiring_concessions:
            # Vérifier si une alarme existe déjà pour éviter les doublons
            if not Alarm.objects.filter(
                type_alarm='concession_expiration',
                concession=concession,
                status='active'
            ).exists():
                
                Alarm.objects.create(
                    type_alarm='concession_expiration',
                    message=f"La concession du caveau {concession.grave.code} expire le {concession.date_fin}. Pensez à contacter le client.",
                    user=concession.user, # Alerte pour le client (ou change pour un admin)
                    concession=concession,
                    status='active'
                )
                count += 1

        self.stdout.write(self.style.SUCCESS(f'✅ {count} nouvelles alarmes de concession expirante créées.'))