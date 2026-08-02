"""
views/map/view.py — Carte interactive du cimetière.
Compatible Flet 0.86.3
CORRECTION : Utilisation d'une fonction async pour appeler page.launch_url() correctement.
CORRECTION : Remplacement de 127.0.0.1 par le domaine public du backend Render
(127.0.0.1 ne fonctionne qu'en local — une fois hébergé, chaque navigateur
distant a son propre 127.0.0.1 qui ne pointe vers rien).
"""
from __future__ import annotations
import flet as ft
from core.auth import AuthState
from core.theme import Colors, get_device_type, heading_style

# ✅ URL publique du backend Django hébergé sur Render
BACKEND_URL = "https://cemetiere-backend-docker.onrender.com"


def build_map_view(page: ft.Page, auth: AuthState) -> ft.View:
    token = auth.access_token or ""
    map_url = f"{BACKEND_URL}/map/?token={token}"

    async def open_map_in_browser(e):
        await page.launch_url(map_url)

    device = get_device_type(page.width or 1200)

    return ft.View(
        route="/carte",
        controls=[
            ft.Row([
                ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: page.go("/dashboard/admin")),
                ft.Text("Carte interactive", style=heading_style(size=22)),
            ]),
            ft.Container(height=20),
            ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.MAP_OUTLINED, size=64, color=Colors.PRIMARY),
                    ft.Container(height=16),
                    ft.Text(
                        "La carte interactive utilise des bibliothèques web avancées (Leaflet.js).\n"
                        "Pour garantir un affichage parfait et l'accès à toutes les fonctionnalités,\n"
                        "veuillez l'ouvrir dans votre navigateur web.",
                        size=14,
                        color=Colors.NEUTRAL,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Container(height=30),
                    ft.ElevatedButton(
                        content=ft.Row([
                            ft.Icon(ft.Icons.OPEN_IN_NEW, color=Colors.TEXT_ON_DARK),
                            ft.Text("Ouvrir la carte dans le navigateur", color=Colors.TEXT_ON_DARK, weight=ft.FontWeight.BOLD)
                        ], spacing=8),
                        style=ft.ButtonStyle(bgcolor=Colors.PRIMARY),
                        width=320,
                        height=50,
                        on_click=open_map_in_browser,
                    ),
                    ft.Container(height=16),
                    ft.Text(
                        "Le lien contient votre jeton de session sécurisé.",
                        size=11,
                        color=Colors.NEUTRAL,
                        italic=True,
                    ),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=40,
                bgcolor="#FFFFFF",
                border_radius=16,
                width=600 if device != "mobile" else None,
                shadow=ft.BoxShadow(spread_radius=0, blur_radius=16, color="#0000000F"),
            ),
        ],
        bgcolor=Colors.BACKGROUND,
        padding=16 if device == "mobile" else 32,
        scroll=ft.ScrollMode.AUTO,
    )