import requests
import uuid
import base64
from django.conf import settings


class MTNMoMoAPI:
    """
    Intégration MTN Mobile Money API (Collection)
    
    Mode SIMULATION par défaut (pour démo / IP locale)
    Mode RÉEL activable en production (IP publique autorisée par MTN)
    
    Authentification OAuth2 correcte :
    - Basic Auth = base64(API_USER : API_KEY)
    - Header Ocp-Apim-Subscription-Key = SUBSCRIPTION_KEY
    """

    def __init__(self):
        self.api_user = settings.MTN_API_USER
        self.api_key = settings.MTN_API_KEY
        self.subscription_key = settings.MTN_SUBSCRIPTION_KEY
        self.environment = settings.MTN_ENVIRONMENT
        
        # ✅ MODE SIMULATION par défaut (True = réel, False = simulation)
        # Changez à True quand déployé sur serveur avec IP publique
        self.use_real_api = False

        if self.environment == 'sandbox':
            self.base_url = "https://sandbox.momodeveloper.mtn.com"
        else:
            self.base_url = "https://api.momodeveloper.mtn.com"

    def get_access_token(self):
        """Obtenir le token OAuth2"""
        if not self.use_real_api:
            print("🟢 Mode SIMULATION activé")
            return f"SIM_TOKEN_{uuid.uuid4().hex[:16]}"

        url = f"{self.base_url}/collection/token/"
        credentials = f"{self.api_user}:{self.api_key}"
        encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
        
        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Ocp-Apim-Subscription-Key": self.subscription_key,
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        
        data = "grant_type=client_credentials"

        try:
            response = requests.post(url, headers=headers, data=data, timeout=30)
            response.raise_for_status()
            return response.json().get("access_token")
        except Exception as e:
            print(f"❌ Erreur MTN Token: {e}")
            return None

    def request_to_pay(self, amount: float, phone: str, reference: str):
        """Demander un paiement au client (USSD Push)"""
        reference_id = str(uuid.uuid4())

        if not self.use_real_api:
            # ✅ MODE SIMULATION
            return {
                "status": "success",
                "reference_id": reference_id,
                "message": f"[SIMULATION] Prompt USSD envoye au {phone}",
                "amount": amount,
                "phone": phone,
                "reference": reference,
                "mode": "simulation"
            }

        # Mode réel
        url = f"{self.base_url}/collection/v1_0/requesttopay"
        token = self.get_access_token()

        if not token:
            return {"status": "error", "message": "Impossible d'obtenir le token MTN"}

        headers = {
            "Authorization": f"Bearer {token}",
            "X-Reference-Id": reference_id,
            "X-Target-Environment": self.environment,
            "Ocp-Apim-Subscription-Key": self.subscription_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        data = {
            "amount": str(amount),
            "currency": "XAF",
            "externalId": reference,
            "payer": {
                "partyIdType": "MSISDN",
                "partyId": phone
            },
            "payerMessage": "Paiement Cimetiere",
            "payeeNote": ""
        }

        try:
            response = requests.post(url, json=data, headers=headers, timeout=30)
            
            if response.status_code in [200, 202]:
                return {
                    "status": "success",
                    "reference_id": reference_id,
                    "message": "Prompt USSD envoye au client",
                    "mode": "reel"
                }
            else:
                return {"status": "error", "message": f"HTTP {response.status_code}: {response.text}"}
                
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def check_status(self, reference_id: str):
        """Vérifier le statut du paiement"""
        if not self.use_real_api:
            return {
                "status": "SUCCESS",
                "reference_id": reference_id,
                "message": "[SIMULATION] Paiement reussi",
                "mode": "simulation"
            }

        url = f"{self.base_url}/collection/v1_0/requesttopay/{reference_id}"
        token = self.get_access_token()

        if not token:
            return {"status": "error", "message": "Impossible d'obtenir le token MTN"}

        headers = {
            "Authorization": f"Bearer {token}",
            "X-Target-Environment": self.environment,
            "Ocp-Apim-Subscription-Key": self.subscription_key,
            "Accept": "application/json"
        }

        try:
            response = requests.get(url, headers=headers, timeout=30)
            return response.json()
        except Exception as e:
            return {"status": "error", "message": str(e)}