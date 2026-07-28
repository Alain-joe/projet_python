"""
users/api.py — Endpoints pour la gestion des utilisateurs.
Compatible Django Ninja + JWT.
CORRECTIONS : Normalisation stricte des données, validation CDC.
"""

from ninja import Router
from ninja.errors import HttpError
from ninja_jwt.authentication import JWTAuth
from ninja_jwt.tokens import RefreshToken
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import get_object_or_404
import threading
import unicodedata
import re
import random
import string

from .models import User
from .schemas import (
    LoginStep1Schema,
    LoginStep2Schema,
    RegisterSchema,
    CreateInternalUserSchema,
    UserOut,
    UserUpdateSchema,
    GenerateUsernameSchema,
)
from core.permissions import require_role
from notifications.utils import notifier_nouvel_utilisateur

router = Router(auth=JWTAuth(), tags=["Users"])


# ==============================================================================
# UTILITAIRES
# ==============================================================================

def generate_unique_username(first_name: str, last_name: str) -> str:
    def normalize(text):
        text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII')
        text = re.sub(r'[^a-z0-9]', '', text.lower())
        return text

    base = f"{normalize(first_name)}.{normalize(last_name)}"
    username = base
    counter = 2

    while User.objects.filter(username=username).exists():
        username = f"{base}{counter}"
        counter += 1

    return username


def generate_temporary_password(length=10):
    chars = string.ascii_letters + string.digits + "!@#$%"
    return ''.join(random.choice(chars) for _ in range(length))


def send_credentials_email(user: User, password: str):
    def _send():
        try:
            send_mail(
                subject="Vos identifiants Cimetière Connect",
                message=(
                    f"Bonjour {user.first_name},\n\n"
                    f"Votre compte a été créé par l'administrateur.\n\n"
                    f"Identifiants de connexion :\n"
                    f"- Nom d'utilisateur : {user.username}\n"
                    f"- Mot de passe : {password}\n\n"
                    f"Vous devrez changer votre mot de passe lors de votre première connexion.\n\n"
                    f"Cordialement,\nL'équipe Cimetière Connect"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
        except Exception:
            pass
    threading.Thread(target=_send, daemon=True).start()


# ==============================================================================
# AUTHENTIFICATION
# ==============================================================================

@router.post("/login/", auth=None)
def login_step1(request, data: LoginStep1Schema):
    try:
        user = User.objects.get(username=data.username.lower())
    except User.DoesNotExist:
        return {"error": "Utilisateur introuvable"}

    if not user.check_password(data.password):
        return {"error": "Mot de passe incorrect"}

    if not user.is_approved:
        return {"error": "Votre compte est en attente d'approbation par l'administrateur"}

    if not user.is_active:
        return {"error": "Votre compte a été désactivé"}

    code = user.generate_mfa_code()

    def send_email_async():
        try:
            send_mail(
                subject="Votre code de connexion",
                message=f"Votre code MFA est : {code}\nIl expire dans 10 minutes.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
        except Exception:
            pass

    threading.Thread(target=send_email_async, daemon=True).start()

    return {"message": "Code MFA envoyé par email", "user_id": user.id}


@router.post("/login/verify/", auth=None)
def login_step2(request, data: LoginStep2Schema):
    try:
        user = User.objects.get(id=data.user_id)
    except User.DoesNotExist:
        return {"error": "Utilisateur introuvable"}

    if not user.verify_mfa_code(data.code):
        return {"error": "Code invalide ou expiré"}

    refresh = RefreshToken.for_user(user)

    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
        "role": user.role,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
    }


@router.post("/register/", auth=None)
def register(request, data: RegisterSchema):
    if User.objects.filter(username=data.username).exists():
        return {"error": "Nom d'utilisateur déjà pris"}

    if User.objects.filter(email=data.email).exists():
        return {"error": "Email déjà utilisé"}

    user = User.objects.create_user(
        username=data.username,
        email=data.email,
        password=data.password,
        phone=data.phone,
        first_name=data.first_name,
        last_name=data.last_name,
        role="client",
        is_approved=True,
    )

    return {"message": "Compte créé avec succès", "user_id": user.id, "username": user.username}


# ==============================================================================
# GESTION DES UTILISATEURS (Admin/Secrétariat)
# ==============================================================================

@router.post("/generate-username/")
@require_role("admin", "secretariat")
def generate_username_endpoint(request, data: GenerateUsernameSchema):
    username = generate_unique_username(data.first_name, data.last_name)
    return {"username": username}


@router.post("/create-internal/")
@require_role("admin", "secretariat")
def create_internal_user(request, data: CreateInternalUserSchema):
    # ✅ VÉRIFICATIONS D'UNICITÉ
    if User.objects.filter(email=data.email).exists():
        raise HttpError(400, "Cet email est déjà utilisé par un autre compte.")
    
    if data.username and User.objects.filter(username=data.username).exists():
        raise HttpError(400, f"Le nom d'utilisateur '{data.username}' est déjà pris.")
    
    if data.phone and User.objects.filter(phone=data.phone).exists():
        raise HttpError(400, "Ce numéro de téléphone est déjà enregistré.")

    # ✅ GÉNÉRATION DU USERNAME SI NON FOURNI
    if data.username:
        username = data.username
    else:
        username = generate_unique_username(data.first_name, data.last_name)

    # ✅ GÉNÉRATION DU MOT DE PASSE TEMPORAIRE SI NON FOURNI
    password = data.password
    must_change_pwd = True

    if not password:
        password = generate_temporary_password()
    else:
        must_change_pwd = False

    # ✅ CRÉATION DE L'UTILISATEUR
    user = User.objects.create_user(
        username=username,
        email=data.email,
        password=password,
        phone=data.phone or "",
        first_name=data.first_name,
        last_name=data.last_name,
        sex=data.sex,
        birth_date=data.birth_date,
        role=data.role,
        address=data.address or "",
        city=data.city or "",
        is_approved=True,
        must_change_password=must_change_pwd,
    )

    # ✅ ENVOI DES IDENTIFIANTS PAR EMAIL
    send_credentials_email(user, password)

    # ✅ NOTIFICATION AUX ADMINS/SECRÉTARIAT
    try:
        notifier_nouvel_utilisateur(user, cree_par=request.auth)
    except Exception as e:
        print(f"️ Erreur notification nouvel utilisateur : {e}")

    return {
        "message": f"Compte {data.role} créé avec succès",
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
        "temporary_password": password if must_change_pwd else None,
    }


@router.get("/list", response=list[UserOut])
@require_role("admin", "secretariat")
def list_users(request):
    users = User.objects.all().order_by("-created_at")
    result = []
    for u in users:
        result.append({
            "id": u.id,
            "username": u.username,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "email": u.email,
            "phone": u.phone,
            "sex": u.sex,
            "birth_date": u.birth_date.isoformat() if u.birth_date else None,
            "role": u.role,
            "is_active": u.is_active,
            "is_approved": u.is_approved,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "date_joined": u.date_joined.isoformat() if u.date_joined else None,
            "address": u.address,
            "city": u.city,
        })
    return result


@router.get("/{user_id}/", response=UserOut)
def get_user(request, user_id: int):
    # ✅ Un utilisateur peut toujours consulter son propre profil.
    if request.auth.id != user_id and request.auth.role not in ("admin", "secretariat"):
        raise HttpError(403, "Accès refusé.")

    user = get_object_or_404(User, id=user_id)
    return {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "phone": user.phone,
        "sex": user.sex,
        "birth_date": user.birth_date.isoformat() if user.birth_date else None,
        "role": user.role,
        "is_active": user.is_active,
        "is_approved": user.is_approved,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "date_joined": user.date_joined.isoformat() if user.date_joined else None,
        "address": user.address,
        "city": user.city,
    }


@router.put("/{user_id}/")
@require_role("admin")
def update_user(request, user_id: int, data: UserUpdateSchema):
    user = get_object_or_404(User, id=user_id)

    if user.id == request.auth.id and data.is_active is False:
        raise HttpError(400, "Vous ne pouvez pas désactiver votre propre compte.")

    # ✅ VÉRIFICATIONS D'UNICITÉ POUR LES CHAMPS MODIFIÉS
    if data.email and User.objects.filter(email=data.email).exclude(id=user_id).exists():
        raise HttpError(400, "Cet email est déjà utilisé par un autre compte.")
    
    if data.phone and User.objects.filter(phone=data.phone).exclude(id=user_id).exists():
        raise HttpError(400, "Ce numéro de téléphone est déjà enregistré.")

    # ✅ MISE À JOUR DES CHAMPS
    if data.first_name is not None:
        user.first_name = data.first_name
    if data.last_name is not None:
        user.last_name = data.last_name
    if data.email is not None:
        user.email = data.email
    if data.phone is not None:
        user.phone = data.phone
    if data.sex is not None:
        user.sex = data.sex
    if data.birth_date is not None:
        user.birth_date = data.birth_date
    if data.role is not None:
        user.role = data.role
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.is_approved is not None:
        user.is_approved = data.is_approved
    if data.address is not None:
        user.address = data.address
    if data.city is not None:
        user.city = data.city

    user.save()

    return {
        "message": "Utilisateur mis à jour",
        "user_id": user.id,
        "role": user.role,
        "is_active": user.is_active,
        "is_approved": user.is_approved,
    }


@router.delete("/{user_id}/")
@require_role("admin")
def delete_user(request, user_id: int):
    user = get_object_or_404(User, id=user_id)

    if user.id == request.auth.id:
        raise HttpError(400, "Vous ne pouvez pas supprimer votre propre compte.")

    user.delete()
    return {"message": "Utilisateur supprimé"}


@router.patch("/{user_id}/approve/")
@require_role("admin")
def approve_user(request, user_id: int):
    user = get_object_or_404(User, id=user_id)
    user.is_approved = True
    user.save(update_fields=['is_approved', 'updated_at'])
    return {"message": f"Utilisateur {user.username} approuvé"}


@router.patch("/{user_id}/reject/")
@require_role("admin")
def reject_user(request, user_id: int):
    user = get_object_or_404(User, id=user_id)
    user.is_approved = False
    user.save(update_fields=['is_approved', 'updated_at'])
    return {"message": f"Utilisateur {user.username} rejeté"}