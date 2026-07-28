# projet_cimetiere/cemeterre_backend/finance/airtel_money.py

import requests
import uuid
from django.conf import settings


class AirtelMoneyAPI:
    """
    Intégration Airtel Money API (Collections/Payments)
    
    Mode SIMULATION par défaut (pour démo / IP locale)
    Mode RÉEL activable en production (IP publique autorisée par Airtel)
    """

    def __init__(self):
        self.client_id = settings.AIRTEL_CLIENT_ID
        self.client_secret = settings.AIRTEL_CLIENT_SECRET
        self.environment = settings.AIRTEL_ENVIRONMENT
        
        # ✅ MODE SIMULATION par défaut (True = réel, False = simulation)
        self.use_real_api = False

        if self.environment == 'sandbox':
            self.base_url = "https://openapiuat.airtel.africa"
        else:
            self.base_url = "https://openapi.airtel.africa"

    def get_access_token(self):
        """Obtenir le token OAuth2"""
        if not self.use_real_api:
            print(" Mode SIMULATION Airtel activé")
            return f"AIRTEL_SIM_TOKEN_{uuid.uuid4().hex[:16]}"

        url = f"{self.base_url}/oauth/token"
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {
            "grant_type": "client_credentials"
        }

        try:
            response = requests.post(
                url, 
                headers=headers, 
                data=data, 
                auth=(self.client_id, self.client_secret),
                timeout=30
            )
            response.raise_for_status()
            return response.json().get("access_token")
        except Exception as e:
            print(f"❌ Erreur Airtel Token: {e}")
            return None

    def make_payment(self, amount: float, phone: str, reference: str):
        """Demander un paiement au client"""
        reference_id = str(uuid.uuid4())

        if not self.use_real_api:
            # ✅ MODE SIMULATION
            return {
                "status": "success",
                "transaction_id": reference_id,
                "message": f"[SIMULATION] Paiement Airtel initié pour le {phone}",
                "amount": amount,
                "phone": phone,
                "reference": reference,
                "mode": "simulation"
            }

        # Mode réel
        url = f"{self.base_url}/merchant/v1/payments/"
        token = self.get_access_token()

        if not token:
            return {"status": "error", "message": "Impossible d'obtenir le token Airtel"}

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Country": "CG",
            "X-Currency": "XAF"
        }

        data = {
            "reference": reference,
            "subscriber": {
                "msisdn": phone,
                "country": "CG"
            },
            "transaction": {
                "id": reference,
                "amount": str(amount),
                "currency": "XAF",
                "narration": "Paiement Cimetiere"
            }
        }

        try:
            response = requests.post(url, json=data, headers=headers, timeout=30)
            
            if response.status_code in [200, 202]:
                return {
                    "status": "success",
                    "transaction_id": response.json().get("transaction", {}).get("id", reference_id),
                    "message": "Paiement Airtel initié",
                    "mode": "reel"
                }
            else:
                return {"status": "error", "message": f"HTTP {response.status_code}: {response.text}"}
                
        except Exception as e:
            return {"status": "error", "message": str(e)}