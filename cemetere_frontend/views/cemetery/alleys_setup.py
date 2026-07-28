"""
views/cemetery/alleys_setup.py — Étape 2 : Dessin des allées sur carte interactive.
Compatible Flet 0.86.0
N'utilise PLUS ft.WebView (non supporté sur Windows/Linux desktop par Flutter).
La carte s'ouvre dans le navigateur système ; l'utilisateur revient dans Flet
et clique sur "J'ai terminé" pour vérifier que la configuration a bien été enregistrée.
"""
from __future__ import annotations
import flet as ft
from urllib.parse import urlencode
from core.auth import AuthState
from core.theme import Colors, get_device_type, heading_style


def build_alleys_setup_view(page: ft.Page, auth: AuthState) -> ft.View:
    setup_data = getattr(page, "setup_data", {})

    if not setup_data:
        return ft.View(
            route="/cimetiere/alleys",
            controls=[
                ft.Text("Erreur: Aucune donnée de configuration.", color=Colors.ERROR),
                ft.ElevatedButton("Retour", on_click=lambda _: page.go("/cimetiere/setup"))
            ]
        )

    params = {
        "lat": setup_data.get("latitude"),
        "lng": setup_data.get("longitude"),
        "longueur": setup_data.get("longueur_totale"),
        "largeur": setup_data.get("largeur_totale"),
        "grave_length": setup_data.get("grave_length"),
        "grave_width": setup_data.get("grave_width"),
        "espacement": setup_data.get("espacement_caveaux"),
        "name": setup_data.get("name"),
        "city": setup_data.get("city"),
        "address": setup_data.get("address"),
        "total_area": setup_data.get("total_area"),
        "token": auth.access_token,
    }

    map_url = f"http://127.0.0.1:8000/map/setup/?{urlencode(params)}"

    status_text = ft.Text("", size=13)

    async def open_map(e):
        await page.launch_url(map_url)

    def check_completion(e):
        status_text.value = "⏳ Vérification..."
        status_text.color = Colors.NEUTRAL
        page.update()
        try:
            config = auth.api.get("/cemetery/config/")
            if isinstance(config, dict) and config.get("id") and config.get("calculated_capacity"):
                status_text.value = f"✅ Configuration détectée — capacité calculée : {config['calculated_capacity']} caveaux."
                status_text.color = Colors.SUCCESS
                page.update()
                page.go("/dashboard/admin")
            else:
                status_text.value = "⚠️ Aucune configuration complète détectée pour le moment. Termine d'abord la configuration dans le navigateur."
                status_text.color = Colors.ERROR
                page.update()
        except Exception as ex:
            status_text.value = f"❌ Erreur lors de la vérification : {ex}"
            status_text.color = Colors.ERROR
            page.update()

    device = get_device_type(page.width or 1200)

    return ft.View(
        route="/cimetiere/alleys",
        controls=[
            ft.Row([
                ft.Text("Configuration des Allées", style=heading_style(size=24)),
                ft.Container(expand=True),
                ft.ElevatedButton("← Annuler", on_click=lambda _: page.go("/cimetiere/setup")),
            ]),
            ft.Container(height=10),
            ft.Text(
                "Étape 2/2 : Ouvre la carte dans ton navigateur, dessine les allées, "
                "clique sur 'Finaliser' dans la page, puis reviens ici et clique sur "
                "'J'ai terminé'.",
                size=14, color=Colors.NEUTRAL
            ),
            ft.Container(height=20),
            ft.Container(
                content=ft.Column([
                    ft.ElevatedButton(
                        content=ft.Row([ft.Text("Ouvrir la carte"), ft.Icon(ft.Icons.MAP)]),
                        bgcolor=Colors.PRIMARY, color=Colors.TEXT_ON_DARK,
                        width=300, on_click=open_map,
                    ),
                    ft.Container(height=10),
                    ft.OutlinedButton(
                        content=ft.Row([ft.Text("J'ai terminé"), ft.Icon(ft.Icons.CHECK)]),
                        width=300, on_click=check_completion,
                    ),
                    ft.Container(height=10),
                    status_text,
                ], spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=24, bgcolor=Colors.SURFACE, border_radius=12,
                width=400 if device == "desktop" else None,
            ),
        ],
        bgcolor=Colors.BACKGROUND,
        padding=24 if device == "desktop" else 16,
        scroll=ft.ScrollMode.AUTO,
    )