"""
core/api.py — Client API centralisé (httpx synchrone) vers le backend Django Ninja.
Compatible Flet 0.86.0
"""
from __future__ import annotations
import httpx
from dataclasses import dataclass
from typing import Any, Optional

BASE_URL = "http://127.0.0.1:8000/api"
TIMEOUT_SECONDS = 15.0

class ApiError(Exception):
    def __init__(self, message: str, status_code: int | None = None, payload: Any = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.payload = payload

    @property
    def is_auth_error(self) -> bool:
        return self.status_code in (401, 403)

    @property
    def is_network_error(self) -> bool:
        return self.status_code is None

@dataclass
class TokenProvider:
    access_token: str | None = None
    refresh_token: str | None = None

    def on_tokens_refreshed(self, access: str, refresh: str) -> None:
        self.access_token = access
        self.refresh_token = refresh

    def on_auth_expired(self) -> None:
        self.access_token = None
        self.refresh_token = None

class ApiClient:
    def __init__(self, token_provider: TokenProvider, base_url: str = BASE_URL):
        self.token_provider = token_provider
        self.base_url = base_url
        self._client = httpx.Client(base_url=base_url, timeout=TIMEOUT_SECONDS)

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.token_provider.access_token:
            headers["Authorization"] = f"Bearer {self.token_provider.access_token}"
        return headers

    def _refresh_token(self) -> bool:
        if not self.token_provider.refresh_token:
            return False
        try:
            resp = self._client.post(
                "/users/token/refresh/",
                json={"refresh": self.token_provider.refresh_token},
            )
            if resp.status_code == 200:
                data = resp.json()
                self.token_provider.on_tokens_refreshed(
                    data["access"], data.get("refresh", self.token_provider.refresh_token)
                )
                return True
        except httpx.RequestError:
            pass
        return False

    def _request(self, method: str, path: str, retry_on_401: bool = True, **kwargs) -> Any:
        try:
            resp = self._client.request(method, path, headers=self._headers(), **kwargs)
        except httpx.RequestError as exc:
            raise ApiError(f"Erreur réseau : impossible de contacter le serveur ({exc})") from exc

        if resp.status_code == 401 and retry_on_401:
            if self._refresh_token():
                return self._request(method, path, retry_on_401=False, **kwargs)
            self.token_provider.on_auth_expired()
            raise ApiError("Session expirée, veuillez vous reconnecter.", status_code=401)

        if resp.status_code >= 400:
            detail = self._extract_error_detail(resp)
            raise ApiError(detail, status_code=resp.status_code, payload=self._safe_json(resp))

        return self._safe_json(resp)

    @staticmethod
    def _safe_json(resp: httpx.Response) -> Any:
        try:
            return resp.json()
        except ValueError:
            return {"detail": resp.text}

    @staticmethod
    def _extract_error_detail(resp: httpx.Response) -> str:
        data = ApiClient._safe_json(resp)
        if isinstance(data, dict):
            return data.get("detail") or data.get("error") or data.get("message") or f"Erreur {resp.status_code}"
        return f"Erreur {resp.status_code}"

    def get(self, path: str, params: dict | None = None) -> Any:
        return self._request("GET", path, params=params)

    def post(self, path: str, json: dict | None = None) -> Any:
        return self._request("POST", path, json=json)

    def put(self, path: str, json: dict | None = None) -> Any:
        return self._request("PUT", path, json=json)

    def patch(self, path: str, json: dict | None = None) -> Any:
        return self._request("PATCH", path, json=json)

    def delete(self, path: str) -> Any:
        return self._request("DELETE", path)

    def close(self) -> None:
        self._client.close()

    # ==============================================================================
    # Méthodes de paiement
    # ==============================================================================
    def payer_especes(self, facture_id: int, montant: float, reference: str = ""):
        return self.post(f"/finance/factures/{facture_id}/paiement/especes/", json={"montant": montant, "reference": reference})

    def payer_mtn(self, facture_id: int, phone: str, montant: float):
        return self.post(f"/finance/factures/{facture_id}/paiement/mtn/", json={"phone": phone, "montant": montant})

    def payer_airtel(self, facture_id: int, phone: str, montant: float):
        return self.post(f"/finance/factures/{facture_id}/paiement/airtel/", json={"phone": phone, "montant": montant})

    def payer_virement(self, facture_id: int, montant: float, reference_virement: str):
        return self.post(f"/finance/factures/{facture_id}/paiement/virement/", json={"montant": montant, "reference_virement": reference_virement})

    def confirmer_virement(self, paiement_id: int):
        return self.post(f"/finance/paiements/{paiement_id}/confirmer/", json={})

    def get_virements_en_attente(self):
        """Récupère la liste des virements bancaires en attente de confirmation"""
        return self.get("/finance/paiements/virements-en-attente")

    def get_historique_facture(self, facture_id: int):
        return self.get(f"/finance/factures/{facture_id}/historique/")

    # ==============================================================================
    # NOUVEAUX : Méthodes pour la gestion des signalements de caveaux
    # ==============================================================================
    def signaler_probleme_caveau(self, grave_id: int, motif: str, description: str = "", photos: list = None):
        return self.post(f"/cemetery/graves/{grave_id}/signaler-probleme/", json={
            "motif": motif,
            "description": description,
            "photos": photos or []
        })

    def get_signalements(self, statut: str = None, grave_id: int = None):
        params = {}
        if statut: params["statut"] = statut
        if grave_id: params["grave_id"] = grave_id
        return self.get("/cemetery/graves/signalements/", params=params)

    def get_signalement(self, signalement_id: int):
        return self.get(f"/cemetery/graves/signalements/{signalement_id}")

    def valider_signalement(self, signalement_id: int):
        return self.post(f"/cemetery/graves/signalements/{signalement_id}/valider/", json={})

    def rejeter_signalement(self, signalement_id: int, motif_rejet: str):
        return self.post(f"/cemetery/graves/signalements/{signalement_id}/rejeter/", json={"motif_rejet": motif_rejet})

    def declarer_non_exploitable_direct(self, grave_id: int, motif: str):
        return self.post(f"/cemetery/graves/{grave_id}/declarer-non-exploitable/", json={"motif": motif})

    def remettre_en_exploitation(self, grave_id: int, nouveau_statut: str = "available"):
        return self.post(f"/cemetery/graves/{grave_id}/remettre-en-exploitation/", json={"nouveau_statut": nouveau_statut})


class Endpoints:
    LOGIN = "/users/login/"
    MFA_VERIFY = "/users/login/verify/"
    USERS_LIST = "/users/list"
    USER_DETAIL = "/users/{user_id}/"
    CREATE_INTERNAL_USER = "/users/create-internal/"
    USER_APPROVE = "/users/{user_id}/approve/"
    USER_REJECT = "/users/{user_id}/reject/"

    CEMETERY_CONFIG = "/cemetery/config/"
    CEMETERY_INITIALIZE_COMPLETE = "/cemetery/cemeteries/initialize-complete/"
    GRAVES_MAP = "/cemetery/graves-map/"
    GRAVES = "/cemetery/graves"
    SECTIONS_GEOJSON = "/cemetery/sections/geojson/"
    ALLEES_GEOJSON = "/cemetery/allees/geojson/"

    RESERVATIONS_LIST = "/reservations/"
    RESERVATION_MANUAL = "/reservations/manual/"

    @staticmethod
    def reservation_details(reservation_id: int) -> str:
        return f"/reservations/{reservation_id}/"
        
    @staticmethod
    def reservation_update(reservation_id: int) -> str:
        return f"/reservations/{reservation_id}/"

    FACTURES = "/finance/factures"
    FINANCE_STATS = "/finance/stats/"
    DASHBOARD_STATS = "/reports/dashboard/"
    
    CONCESSIONS = "/cemetery/concessions"
    CONCESSIONS_READY = "/cemetery/concessions/ready-for-creation"
    CONCESSIONS_FROM_RESERVATION = "/cemetery/concessions/from-reservation"
    
    @staticmethod
    def concession_renew(concession_id: int) -> str:
        return f"/cemetery/concessions/{concession_id}/renew"
        
    @staticmethod
    def concession_resilier(concession_id: int) -> str:
        return f"/cemetery/concessions/{concession_id}/resilier"

    EXHUMATIONS = "/cemetery/exhumations"
    AUDIT_LOGS = "/audit/logs"

    NOTIFICATIONS_LIST = "/notifications/notifications"
    NOTIFICATIONS_UNREAD_COUNT = "/notifications/notifications/unread-count"
    NOTIFICATIONS_READ_ALL = "/notifications/notifications/read-all"

    @staticmethod
    def notification_read(notification_id: int) -> str:
        return f"/notifications/notifications/{notification_id}/read"


class ApiService:
    def __init__(self, client: ApiClient):
        self.client = client

    def login_step1(self, username: str, password: str):
        return self.client.post(Endpoints.LOGIN, json={"username": username, "password": password})

    def login_step2(self, user_id: int, code: str):
        return self.client.post(Endpoints.MFA_VERIFY, json={"user_id": user_id, "code": code})

    def get_users_list(self):
        return self.client.get(Endpoints.USERS_LIST)

    def create_internal_user(self, data: dict):
        return self.client.post(Endpoints.CREATE_INTERNAL_USER, json=data)

    def update_user(self, user_id: int, data: dict):
        return self.client.put(Endpoints.USER_DETAIL.format(user_id=user_id), json=data)

    def delete_user(self, user_id: int):
        return self.client.delete(Endpoints.USER_DETAIL.format(user_id=user_id))

    def approve_user(self, user_id: int):
        return self.client.patch(Endpoints.USER_APPROVE.format(user_id=user_id))

    def reject_user(self, user_id: int):
        return self.client.patch(Endpoints.USER_REJECT.format(user_id=user_id))

    def get_reservations(self, status: str | None = None):
        params = {"status": status} if status else None
        return self.client.get(Endpoints.RESERVATIONS_LIST, params=params)

    def create_reservation_manual(self, data: dict):
        return self.client.post(Endpoints.RESERVATION_MANUAL, json=data)

    def update_reservation_status(self, reservation_id: int, status: str, note: str | None = None):
        payload = {"status": status}
        if note:
            payload["note"] = note
        return self.client.put(Endpoints.reservation_update(reservation_id), json=payload)

    def get_reservation_details(self, reservation_id: int):
        return self.client.get(Endpoints.reservation_details(reservation_id))

    def get_factures(self, statut: str | None = None):
        params = {"statut": statut} if statut else None
        return self.client.get(Endpoints.FACTURES, params=params)

    def payer_especes(self, facture_id: int, montant: float, reference: str = ""):
        return self.client.payer_especes(facture_id, montant, reference)

    def payer_mtn(self, facture_id: int, phone: str, montant: float):
        return self.client.payer_mtn(facture_id, phone, montant)

    def payer_airtel(self, facture_id: int, phone: str, montant: float):
        return self.client.payer_airtel(facture_id, phone, montant)

    def payer_virement(self, facture_id: int, montant: float, reference_virement: str):
        return self.client.payer_virement(facture_id, montant, reference_virement)

    def confirmer_virement(self, paiement_id: int):
        return self.client.confirmer_virement(paiement_id)

    def get_virements_en_attente(self):
        return self.client.get_virements_en_attente()

    def get_historique_facture(self, facture_id: int):
        return self.client.get_historique_facture(facture_id)

    def get_finance_stats(self):
        return self.client.get(Endpoints.FINANCE_STATS)

    def get_dashboard_stats(self, cemetery_id: int | None = None):
        params = {"cemetery_id": cemetery_id} if cemetery_id else None
        return self.client.get(Endpoints.DASHBOARD_STATS, params=params)

    def get_audit_logs(self, params: dict | None = None):
        return self.client.get(Endpoints.AUDIT_LOGS, params=params)

    def get_notifications(self):
        return self.client.get(Endpoints.NOTIFICATIONS_LIST)

    def get_unread_count(self):
        return self.client.get(Endpoints.NOTIFICATIONS_UNREAD_COUNT)

    def mark_notification_read(self, notification_id: int):
        return self.client.put(Endpoints.notification_read(notification_id))

    def mark_all_notifications_read(self):
        return self.client.put(Endpoints.NOTIFICATIONS_READ_ALL)

    def initialize_cemetery_complete(self, data: dict):
        return self.client.post(Endpoints.CEMETERY_INITIALIZE_COMPLETE, json=data)

    def get_sections_geojson(self):
        return self.client.get(Endpoints.SECTIONS_GEOJSON)

    def get_allees_geojson(self):
        return self.client.get(Endpoints.ALLEES_GEOJSON)

    def get_concessions_ready(self):
        return self.client.get(Endpoints.CONCESSIONS_READY)

    def create_concession_from_reservation(self, data: dict):
        return self.client.post(Endpoints.CONCESSIONS_FROM_RESERVATION, json=data)

    def renew_concession(self, concession_id: int, data: dict):
        return self.client.put(Endpoints.concession_renew(concession_id), json=data)

    def resiliate_concession(self, concession_id: int, motif: str):
        return self.client.put(Endpoints.concession_resilier(concession_id), json={"motif": motif})

    # ==============================================================================
    # Délégation des méthodes de signalement vers ApiClient
    # ==============================================================================
    def signaler_probleme_caveau(self, grave_id: int, motif: str, description: str = "", photos: list = None):
        return self.client.signaler_probleme_caveau(grave_id, motif, description, photos)

    def get_signalements(self, statut: str = None, grave_id: int = None):
        return self.client.get_signalements(statut, grave_id)

    def get_signalement(self, signalement_id: int):
        return self.client.get_signalement(signalement_id)

    def valider_signalement(self, signalement_id: int):
        return self.client.valider_signalement(signalement_id)

    def rejeter_signalement(self, signalement_id: int, motif_rejet: str):
        return self.client.rejeter_signalement(signalement_id, motif_rejet)

    def declarer_non_exploitable_direct(self, grave_id: int, motif: str):
        return self.client.declarer_non_exploitable_direct(grave_id, motif)

    def remettre_en_exploitation(self, grave_id: int, nouveau_statut: str = "available"):
        return self.client.remettre_en_exploitation(grave_id, nouveau_statut)