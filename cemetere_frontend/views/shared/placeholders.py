"""
views/shared/placeholders.py — Vues temporaires "En construction".
Permet d'avoir une navigation fonctionnelle immédiatement.
Compatible Flet 0.86.0 - Contenu parfaitement centré
"""

from __future__ import annotations

import flet as ft

from core.auth import AuthState
from core.theme import Colors, heading_style, get_device_type


def build_placeholder_view(
    page: ft.Page, 
    auth: AuthState,
    title: str,
    icon: str,
    description: str = "Cette page est en cours de développement.",
    route: str = "",
) -> ft.View:
    """Génère une vue placeholder générique parfaitement centrée."""
    device = get_device_type(page.width or 1200)

    # 1. La carte blanche (le contenu)
    card = ft.Container(
        content=ft.Column([
            ft.Icon(icon, size=60, color=Colors.PRIMARY),
            ft.Container(height=20),
            ft.Text(title, style=heading_style(size=24)),
            ft.Container(height=10),
            ft.Text(
                description,
                size=14,
                color=Colors.NEUTRAL,
                text_align=ft.TextAlign.CENTER,
            ),
            ft.Container(height=30),
            ft.ElevatedButton(
                content=ft.Row([
                    ft.Icon(ft.Icons.ARROW_BACK, color=Colors.TEXT_ON_DARK),
                    ft.Text("Retour au tableau de bord", color=Colors.TEXT_ON_DARK)
                ], spacing=5),
                style=ft.ButtonStyle(bgcolor=Colors.PRIMARY),
                on_click=lambda _: page.go("/dashboard/admin"),
            ),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        padding=40,
        bgcolor="#FFFFFF",
        border_radius=16,
        width=500 if device == "desktop" else None,
        shadow=ft.BoxShadow(spread_radius=0, blur_radius=15, color="#0000001A"), # ✅ Jolie ombre
    )

    # 2. Le conteneur parent qui prend TOUT l'espace et centre la carte
    centered_layout = ft.Column(
        [card],
        expand=True,  # ✅ Prend toute la hauteur de l'écran
        alignment=ft.MainAxisAlignment.CENTER,  # ✅ Centre verticalement
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,  # ✅ Centre horizontalement
    )

    return ft.View(
        route=route,
        controls=[centered_layout],
        bgcolor=Colors.BACKGROUND,
        # ✅ Pas de padding sur la View pour éviter de décaler le centrage
        scroll=ft.ScrollMode.AUTO,
    )


# --- Vues placeholders spécifiques ---

def build_cemeteries_view(page: ft.Page, auth: AuthState) -> ft.View:
    return build_placeholder_view(
        page, auth, title="Cimetières", icon=ft.Icons.PARK,
        description="Configuration du cimetière unique (singleton).", route="/cemeteries",
    )

def build_sections_view(page: ft.Page, auth: AuthState) -> ft.View:
    return build_placeholder_view(
        page, auth, title="Sections", icon=ft.Icons.GRID_VIEW,
        description="Gestion des zones et blocs du cimetière.", route="/sections",
    )

def build_graves_view(page: ft.Page, auth: AuthState) -> ft.View:
    return build_placeholder_view(
        page, auth, title="Sépultures", icon=ft.Icons.LOCATION_ON,
        description="Liste administrative de tous les caveaux.", route="/graves",
    )

def build_exhumations_view(page: ft.Page, auth: AuthState) -> ft.View:
    return build_placeholder_view(
        page, auth, title="Exhumations", icon=ft.Icons.ARROW_UPWARD,
        description="Gestion des demandes d'exhumation.", route="/exhumations",
    )

def build_finance_view(page: ft.Page, auth: AuthState) -> ft.View:
    return build_placeholder_view(
        page, auth, title="Finance", icon=ft.Icons.ACCOUNT_BALANCE,
        description="Liste des factures et historique des paiements.", route="/finance",
    )

def build_alerts_view(page: ft.Page, auth: AuthState) -> ft.View:
    return build_placeholder_view(
        page, auth, title="Alertes", icon=ft.Icons.NOTIFICATIONS_ACTIVE,
        description="Échéances de concessions et seuils critiques.", route="/alerts",
    )

def build_reports_view(page: ft.Page, auth: AuthState) -> ft.View:
    return build_placeholder_view(
        page, auth, title="Rapports", icon=ft.Icons.ASSESSMENT,
        description="Téléchargement des exports CSV et Excel.", route="/reports",
    )

def build_users_view(page: ft.Page, auth: AuthState) -> ft.View:
    return build_placeholder_view(
        page, auth, title="Utilisateurs", icon=ft.Icons.PEOPLE,
        description="Gestion des comptes et des rôles (RBAC).", route="/users",
    )

def build_settings_view(page: ft.Page, auth: AuthState) -> ft.View:
    return build_placeholder_view(
        page, auth, title="Paramètres", icon=ft.Icons.SETTINGS,
        description="Configuration générale de l'application.", route="/settings",
    )