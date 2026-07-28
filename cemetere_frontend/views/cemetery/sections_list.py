"""
views/cemetery/sections_list.py — Liste des sections générées.
Compatible Flet 0.86.0
"""
from __future__ import annotations
import flet as ft
from core.auth import AuthState
from core.theme import Colors, get_device_type, heading_style

def build_sections_list_view(page: ft.Page, auth: AuthState) -> ft.View:
    sections = []
    loading = ft.ProgressRing(visible=True)
    error_text = ft.Text("", color=Colors.ERROR, size=13, visible=False)
    list_container = ft.Column(spacing=10)

    async def load_sections():
        loading.visible, error_text.visible = True, False
        page.update()
        try:
            # On utilise l'endpoint geojson car il contient toutes les infos nécessaires
            data = auth.api.get("/cemetery/sections/geojson/")
            sections.clear()
            if isinstance(data, dict) and "features" in data:
                for feature in data["features"]:
                    props = feature.get("properties", {})
                    sections.append(props)
            render_list()
        except Exception as exc:
            error_text.value = f"Erreur de chargement : {exc}"
            error_text.visible = True
        finally:
            loading.visible = False
            page.update()

    def render_list():
        list_container.controls.clear()
        if not sections:
            list_container.controls.append(ft.Text("Aucune section configurée.", color=Colors.NEUTRAL, italic=True))
        else:
            for sec in sections:
                list_container.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Column([
                                ft.Text(f"{sec.get('nom', 'Section')}", weight=ft.FontWeight.W_600, size=14),
                                ft.Text(f"Ordre : {sec.get('ordre', 'N/A')}", size=12, color=Colors.NEUTRAL),
                            ], spacing=4, expand=True),
                            ft.Column([
                                ft.Text(f"Surface : {sec.get('surface', 0):.2f} m²", size=13, weight=ft.FontWeight.W_600),
                                ft.Text(f"Capacité : {sec.get('capacite', 0)} caveaux", size=12, color=Colors.PRIMARY),
                            ], spacing=4, horizontal_alignment=ft.CrossAxisAlignment.END),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        padding=14, bgcolor="#FFFFFF", border_radius=10, border=ft.Border.all(1, Colors.BORDER),
                    )
                )
        page.update()

    page.run_task(load_sections)
    device = get_device_type(page.width or 1200)

    return ft.View(
        route="/cimetiere/sections",
        controls=[
            ft.Row([
                ft.Text("Sections du Cimetière", style=heading_style(size=22)),
                ft.Container(expand=True),
                ft.ElevatedButton("🔄 Actualiser", icon=ft.Icons.REFRESH, bgcolor=Colors.PRIMARY, color=Colors.TEXT_ON_DARK, on_click=lambda _: page.run_task(load_sections)),
                ft.ElevatedButton("🗺️ Voir sur la carte", icon=ft.Icons.MAP, on_click=lambda _: page.go("/carte")),
            ]),
            ft.Container(height=20),
            error_text, loading, list_container,
        ],
        bgcolor=Colors.BACKGROUND,
        padding=24 if device == "desktop" else 16,
        scroll=ft.ScrollMode.AUTO,
    )