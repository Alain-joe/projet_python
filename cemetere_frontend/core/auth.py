"""
core/auth.py — État d'authentification (JWT + MFA).

CORRECTION APPLIQUÉE :
- restore_session et verify_mfa ne recopiaient que id/username/email/
  first_name/last_name/role dans self._user, alors que le backend
  (UserOut) renvoie aussi phone, sex, birth_date, is_active,
  is_approved, created_at, date_joined -> ces champs étaient
  silencieusement perdus et jamais affichés sur la page profil.
- verify_mfa : la réponse de /users/login/verify/ ne contient pas
  forcément tous les champs du profil complet (elle sert surtout à
  livrer les tokens) -> après connexion réussie, un appel
  GET /users/{id}/ est fait pour récupérer le profil complet et fiable,
  au lieu de compter uniquement sur la réponse de login.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from core.api import ApiClient, ApiError, TokenProvider

class Role(str, Enum):
    ADMIN = "admin"
    AGENT = "agent"
    SECRETARIAT = "secretariat"
    CLIENT = "client"

@dataclass
class AuthResult:
    success: bool
    message: str = ""
    requires_mfa: bool = False

class AuthState(TokenProvider):
    def __init__(self):
        super().__init__()
        self.api: ApiClient = ApiClient(token_provider=self)
        self._pending_user_id: int | None = None
        self._user: dict = {}

    @property
    def is_authenticated(self) -> bool:
        return self.access_token is not None

    @property
    def role(self) -> Role | None:
        if not self._user: return None
        try: return Role(self._user.get("role"))
        except ValueError: return None

    @property
    def user(self) -> dict: return self._user

    @property
    def username(self) -> str: return self._user.get("username", "")

    def _map_user_data(self, user_data: dict, fallback_id: int | None = None) -> dict:
        """Construit self._user avec TOUS les champs renvoyés par UserOut."""
        return {
            "id": user_data.get("id", fallback_id),
            "username": user_data.get("username", ""),
            "email": user_data.get("email", ""),
            "first_name": user_data.get("first_name", ""),
            "last_name": user_data.get("last_name", ""),
            "role": user_data.get("role", "client"),
            "phone": user_data.get("phone", ""),
            "sex": user_data.get("sex", ""),
            "birth_date": user_data.get("birth_date", ""),
            "is_active": user_data.get("is_active", True),
            "is_approved": user_data.get("is_approved", True),
            "created_at": user_data.get("created_at", ""),
            "date_joined": user_data.get("date_joined", ""),
        }

    def restore_session(self, token: str) -> bool:
        import jwt as jwt_lib
        if not token: return False
        
        try:
            self.access_token = token
            payload = jwt_lib.decode(token, options={"verify_signature": False})
            user_id = payload.get("user_id")
            if not user_id: return False
            
            try:
                # ✅ CORRECTION : Ajout du slash final à la fin de l'URL
                user_data = self.api.get(f"/users/{user_id}/")
                if isinstance(user_data, dict) and "error" not in user_data:
                    self._user = self._map_user_data(user_data, fallback_id=user_id)
                    return True
            except Exception:
                pass
            
            # Fallback
            self._user = {"id": user_id, "username": f"user_{user_id}", "role": "client"}
            return True
        except Exception:
            return False

    def login(self, username: str, password: str) -> AuthResult:
        try:
            data = self.api.post("/users/login/", json={"username": username, "password": password})
        except ApiError as exc:
            return AuthResult(success=False, message=exc.message)
        if "error" in data or "detail" in data:
            return AuthResult(success=False, message=data.get("error") or data.get("detail"))
        if user_id := data.get("user_id"):
            self._pending_user_id = user_id
            return AuthResult(success=True, requires_mfa=True, message=data.get("message", "Code envoyé"))
        return AuthResult(success=False, message="Réponse inattendue.")

    def verify_mfa(self, code: str) -> AuthResult:
        if not self._pending_user_id:
            return AuthResult(success=False, message="Aucune session en cours.")
        try:
            data = self.api.post("/users/login/verify/", json={"user_id": self._pending_user_id, "code": code})
        except ApiError as exc:
            return AuthResult(success=False, message=exc.message)
        if "access" not in data or "refresh" not in data:
            return AuthResult(success=False, message=data.get("detail") or data.get("error") or "Code invalide")
        
        self.on_tokens_refreshed(data["access"], data["refresh"])
        user_id = data.get("user_id", self._pending_user_id)
        self._pending_user_id = None

        # ✅ CORRECTION : Profil complet via GET /users/{id}/ plutôt que
        # de dépendre des champs (partiels) renvoyés par login/verify/.
        try:
            user_data = self.api.get(f"/users/{user_id}/")
            if isinstance(user_data, dict) and "error" not in user_data:
                self._user = self._map_user_data(user_data, fallback_id=user_id)
                return AuthResult(success=True)
        except Exception:
            pass

        # Fallback : on garde au moins ce que login/verify/ a renvoyé
        self._user = {
            "id": user_id,
            "role": data.get("role"),
            "username": data.get("username", ""),
            "first_name": data.get("first_name", ""),
            "last_name": data.get("last_name", ""),
            "email": data.get("email", ""),
        }
        return AuthResult(success=True)

    def logout(self) -> None:
        self.access_token = None
        self.refresh_token = None
        self._pending_user_id = None
        self._user = {}

    def has_role(self, *roles: Role) -> bool: return self.role in roles
    def can_access_finances(self) -> bool: return self.has_role(Role.ADMIN, Role.SECRETARIAT)
    def can_edit_map(self) -> bool: return self.has_role(Role.ADMIN, Role.AGENT)
    def can_validate_reservations(self) -> bool: return self.has_role(Role.ADMIN, Role.SECRETARIAT)