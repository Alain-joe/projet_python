"""
views/map/view.py — Carte interactive (SIG) ouvrant le navigateur par défaut.
Compatible Flet 0.86.0
"""
from __future__ import annotations
import flet as ft
from urllib.parse import quote

from core.auth import AuthState
from core.theme import Colors, get_device_type, heading_style


def build_map_view(page: ft.Page, auth: AuthState) -> ft.View:
    token = None
    
    if hasattr(auth, "access_token") and auth.access_token:
        token = auth.access_token
    elif hasattr(auth, "token") and auth.token:
        token = auth.token
    elif isinstance(auth, dict):
        token = auth.get("access_token") or auth.get("token")
        
    if not token and hasattr(page, 'client_storage'):
        try:
            token = page.client_storage.get("access_token")
        except Exception:
            pass

    if not token:
        print("⚠️ ERREUR CRITIQUE : Aucun token trouvé !")
    else:
        token = token.strip()

    map_url = f"http://127.0.0.1:8000/map/?token={quote(token)}" if token else ""

    async def open_map_in_browser(e: ft.ControlEvent) -> None:
        if token and map_url:
            await page.launch_url(map_url)
        else:
            page.go("/login")

    device = get_device_type(page.width or 1200)

    return ft.View(
        route="/carte",
        controls=[
            ft.Text("Carte Interactive (SIG)", style=heading_style(size=24)),
            ft.Container(height=20),
            ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(ft.Icons.MAP, size=80, color=Colors.PRIMARY),
                        ft.Container(height=20),
                        ft.Text(
                            "Pour une expérience optimale et fluide,\n"
                            "la carte interactive s'ouvrira dans votre navigateur.",
                            size=16,
                            color=Colors.NEUTRAL,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Container(height=10),
                        ft.Text(
                            "💡 Astuce : Cliquez sur un caveau VERT dans la carte pour lancer une réservation.",
                            size=13,
                            color=Colors.PRIMARY,
                            text_align=ft.TextAlign.CENTER,
                            weight=ft.FontWeight.W_600,
                        ),
                        ft.Container(height=40),
                        ft.ElevatedButton(
                            content=ft.Row(
                                [
                                    ft.Icon(ft.Icons.OPEN_IN_NEW, color=Colors.TEXT_ON_DARK),
                                    ft.Text("Ouvrir la carte interactive", color=Colors.TEXT_ON_DARK, weight=ft.FontWeight.BOLD)
                                ],
                                spacing=8,
                                alignment=ft.MainAxisAlignment.CENTER,
                            ),
                            style=ft.ButtonStyle(bgcolor=Colors.PRIMARY),
                            width=300,
                            height=55,
                            on_click=open_map_in_browser,
                        )
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=40,
                bgcolor="#FFFFFF",
                border_radius=16,
                width=500 if device == "desktop" else None,
            )
        ],
        bgcolor=Colors.BACKGROUND,
        padding=32,
        scroll=ft.ScrollMode.AUTO,
    )