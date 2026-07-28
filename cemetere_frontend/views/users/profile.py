"""
views/users/profile.py — Page de profil utilisateur.
Compatible Flet 0.86.0

CORRECTIONS APPLIQUÉES :
- page.window.width -> page.width (même bug corrigé ailleurs dans le
  projet : page.window.width provoque un plantage silencieux sous
  Flet 0.86, causant potentiellement un mauvais rendu de la page).
- Ajout des champs Téléphone, Sexe, Date de naissance et Date
  d'inscription (déjà présents dans la réponse UserOut du backend,
  mais absents jusqu'ici de self._user côté frontend -> corrigés
  dans core/auth.py, maintenant affichés ici).
"""
from __future__ import annotations
import flet as ft
from core.auth import AuthState
from core.theme import Colors, get_device_type, heading_style

SEX_LABELS = {"M": "Masculin", "F": "Féminin", "O": "Autre", "N": "Non renseigné"}

def build_profile_view(page: ft.Page, auth: AuthState) -> ft.View:
    user = auth.user or {}
    
    # Récupération des initiales pour l'avatar
    first_name = user.get("first_name", user.get("username", "U"))
    last_name = user.get("last_name", "")
    initials = f"{first_name[0]}{last_name[0]}".upper() if last_name else first_name[:2].upper()

    device = get_device_type(page.width or 1200)

    sex_display = SEX_LABELS.get(user.get("sex", ""), "Non renseigné")
    birth_date_display = user.get("birth_date") or "Non renseignée"
    date_joined_raw = user.get("date_joined") or user.get("created_at")
    date_joined_display = date_joined_raw[:10] if date_joined_raw else "Inconnue"

    return ft.View(
        route="/profil",
        controls=[
            ft.Text("Mon Profil", style=heading_style(size=22)),
            ft.Container(height=20),
            ft.Container(
                content=ft.Column([
                    # En-tête avec Avatar
                    ft.Row([
                        ft.Container(
                            content=ft.Text(initials, size=24, color=Colors.TEXT_ON_DARK, weight=ft.FontWeight.BOLD),
                            bgcolor=Colors.PRIMARY,
                            width=80, height=80,
                            border_radius=40,
                            alignment=ft.Alignment(0.5, 0.5),
                        ),
                        ft.Column([
                            ft.Text(f"{first_name} {last_name}", size=20, weight=ft.FontWeight.BOLD),
                            ft.Text(f"Rôle : {user.get('role', 'Utilisateur').capitalize()}", size=14, color=Colors.NEUTRAL),
                        ], spacing=4),
                    ], alignment=ft.MainAxisAlignment.START),
                    
                    ft.Divider(height=20, color=Colors.BORDER),
                    
                    # Informations détaillées
                    ft.Text("Informations personnelles", style=heading_style(size=16)),
                    ft.Container(height=10),
                    
                    ft.TextField(
                        label="Nom d'utilisateur", value=user.get("username", ""), 
                        read_only=True, border_radius=12, filled=True, bgcolor=Colors.BACKGROUND
                    ),
                    ft.TextField(
                        label="Email", value=user.get("email", "Non renseigné"), 
                        read_only=True, border_radius=12, filled=True, bgcolor=Colors.BACKGROUND
                    ),
                    ft.TextField(
                        label="Téléphone", value=user.get("phone") or "Non renseigné",
                        read_only=True, border_radius=12, filled=True, bgcolor=Colors.BACKGROUND
                    ),
                    ft.TextField(
                        label="Sexe", value=sex_display,
                        read_only=True, border_radius=12, filled=True, bgcolor=Colors.BACKGROUND
                    ),
                    ft.TextField(
                        label="Date de naissance", value=birth_date_display,
                        read_only=True, border_radius=12, filled=True, bgcolor=Colors.BACKGROUND
                    ),
                    ft.TextField(
                        label="Date d'inscription", value=date_joined_display,
                        read_only=True, border_radius=12, filled=True, bgcolor=Colors.BACKGROUND
                    ),
                    
                    ft.Container(height=20),
                    ft.Text("Note : Pour modifier votre mot de passe ou vos informations, contactez l'administrateur.", size=12, color=Colors.NEUTRAL, italic=True),
                ], spacing=10),
                padding=24,
                bgcolor="#FFFFFF",
                border_radius=12,
                expand=True,
            ),
        ],
        bgcolor=Colors.BACKGROUND,
        padding=16 if device == "mobile" else 32,
        scroll=ft.ScrollMode.AUTO,
    )