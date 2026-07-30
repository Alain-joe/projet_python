"""
views/auth/welcome.py — Page d'accueil publique.
Compatible Flet 0.86.3
Affiche 2 options : Se connecter ou Créer un compte.
"""
from __future__ import annotations
import flet as ft
from core.theme import Colors, get_device_type, heading_style


def build_welcome_view(page: ft.Page, auth) -> ft.View:
    """Page d'accueil publique - accessible sans authentification."""
    
    width = getattr(page, 'window', page).width if hasattr(page, 'window') else (getattr(page, 'width', 1200) or 1200)
    device = get_device_type(width)
    is_mobile = device == "mobile"

    # Logo et titre
    header = ft.Column([
        ft.Icon(ft.Icons.PARK, size=80 if not is_mobile else 60, color=Colors.PRIMARY),
        ft.Container(height=16),
        ft.Text("Cimetière Connect", style=heading_style(size=32 if not is_mobile else 24)),
        ft.Text("Gestion moderne et numérique de votre cimetière", 
                size=14, color=Colors.NEUTRAL, text_align=ft.TextAlign.CENTER),
    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    # Bouton Se connecter
    btn_login = ft.ElevatedButton(
        content=ft.Row([
            ft.Icon(ft.Icons.LOGIN, color=Colors.TEXT_ON_DARK, size=20),
            ft.Text("Se connecter", color=Colors.TEXT_ON_DARK, weight=ft.FontWeight.BOLD, size=15),
        ], spacing=8),
        style=ft.ButtonStyle(
            bgcolor=Colors.PRIMARY,
            padding=ft.Padding(left=20, top=14, right=20, bottom=14),
            shape=ft.RoundedRectangleBorder(radius=12),
        ),
        width=280 if not is_mobile else float("inf"),
        height=52,
        on_click=lambda _: page.go("/login"),
    )

    # Bouton Créer un compte
    btn_register = ft.OutlinedButton(
        content=ft.Row([
            ft.Icon(ft.Icons.PERSON_ADD, color=Colors.PRIMARY, size=20),
            ft.Text("Créer un compte", color=Colors.PRIMARY, weight=ft.FontWeight.BOLD, size=15),
        ], spacing=8),
        style=ft.ButtonStyle(
            side=ft.BorderSide(2, Colors.PRIMARY),
            padding=ft.Padding(left=20, top=14, right=20, bottom=14),
            shape=ft.RoundedRectangleBorder(radius=12),
        ),
        width=280 if not is_mobile else float("inf"),
        height=52,
        on_click=lambda _: page.go("/register"),
    )

    # Section fonctionnalités
    features = ft.ResponsiveRow([
        ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.MAP, size=32, color=Colors.PRIMARY),
                ft.Text("Carte interactive", size=13, weight=ft.FontWeight.BOLD),
                ft.Text("Visualisez les caveaux disponibles en temps réel", size=11, color=Colors.NEUTRAL, text_align=ft.TextAlign.CENTER),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
            padding=16, bgcolor="#FFFFFF", border_radius=12,
            col={"xs": 12, "sm": 6, "md": 3},
        ),
        ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.EVENT_NOTE, size=32, color=Colors.PRIMARY),
                ft.Text("Réservation en ligne", size=13, weight=ft.FontWeight.BOLD),
                ft.Text("Réservez votre caveau en quelques clics", size=11, color=Colors.NEUTRAL, text_align=ft.TextAlign.CENTER),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
            padding=16, bgcolor="#FFFFFF", border_radius=12,
            col={"xs": 12, "sm": 6, "md": 3},
        ),
        ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.PAYMENTS, size=32, color=Colors.PRIMARY),
                ft.Text("Paiement sécurisé", size=13, weight=ft.FontWeight.BOLD),
                ft.Text("MTN, Airtel, Virement bancaire", size=11, color=Colors.NEUTRAL, text_align=ft.TextAlign.CENTER),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
            padding=16, bgcolor="#FFFFFF", border_radius=12,
            col={"xs": 12, "sm": 6, "md": 3},
        ),
        ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.SECURITY, size=32, color=Colors.PRIMARY),
                ft.Text("Authentification MFA", size=13, weight=ft.FontWeight.BOLD),
                ft.Text("Vos données sont protégées par code email", size=11, color=Colors.NEUTRAL, text_align=ft.TextAlign.CENTER),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
            padding=16, bgcolor="#FFFFFF", border_radius=12,
            col={"xs": 12, "sm": 6, "md": 3},
        ),
    ], spacing=16, run_spacing=16)

    # Footer
    footer = ft.Text(
        "© 2026 Cimetière Connect - Projet GI2",
        size=11, color=Colors.NEUTRAL, italic=True
    )

    return ft.View(
        route="/welcome",
        controls=[
            ft.Container(
                content=ft.Column([
                    ft.Container(height=40 if not is_mobile else 20),
                    header,
                    ft.Container(height=40),
                    ft.Column([btn_login, btn_register], spacing=16, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Container(height=60 if not is_mobile else 40),
                    ft.Text("Pourquoi choisir Cimetière Connect ?", size=16, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                    ft.Container(height=20),
                    features,
                    ft.Container(height=40),
                    footer,
                    ft.Container(height=20),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
                expand=True,
                padding=24 if not is_mobile else 16,
            ),
        ],
        bgcolor=Colors.BACKGROUND,
        padding=0,
        scroll=ft.ScrollMode.AUTO,
    )