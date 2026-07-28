"""
views/cemetery/alleys_list.py — Liste des allées configurées.
Compatible Flet 0.86.0
"""
from __future__ import annotations
import flet as ft
from core.auth import AuthState
from core.theme import Colors, get_device_type, heading_style

def build_alleys_list_view(page: ft.Page, auth: AuthState) -> ft.View:
    allees = []
    loading = ft.ProgressRing(visible=True)
    error_text = ft.Text("", color=Colors.ERROR, size=13, visible=False)
    list_container = ft.Column(spacing=10)

    async def load_allees():
        loading.visible, error_text.visible = True, False
        page.update()
        try:
            data = auth.api.get("/cemetery/allees/")
            allees.clear()
            if isinstance(data, list):
                allees.extend(data)
            elif isinstance(data, dict):
                allees.extend(data.get("results", [])) 
            render_list()
        except Exception as exc:
            error_text.value = f"Erreur de chargement : {exc}"
            error_text.visible = True
        finally:
            loading.visible = False
            page.update()

    def render_list():
        list_container.controls.clear()
        if not allees:
            list_container.controls.append(ft.Text("Aucune allée configurée.", color=Colors.NEUTRAL, italic=True))
        else:
            for allee in allees:
                list_container.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Column([
                                ft.Text(f"{allee.get('nom', 'Allée')}", weight=ft.FontWeight.W_600, size=14),
                                ft.Text(f"Type : {allee.get('type_allee', 'N/A').capitalize()}", size=12, color=Colors.NEUTRAL),
                            ], spacing=4, expand=True),
                            ft.Column([
                                ft.Text(f"Largeur : {allee.get('largeur', 0)} m", size=13, weight=ft.FontWeight.W_600),
                                ft.Text(f"Surface : {allee.get('surface_calculee', 0):.2f} m²", size=12, color=Colors.PRIMARY),
                            ], spacing=4, horizontal_alignment=ft.CrossAxisAlignment.END),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        padding=14, bgcolor="#FFFFFF", border_radius=10, border=ft.Border.all(1, Colors.BORDER),
                    )
                )
        page.update()

    page.run_task(load_allees)
    device = get_device_type(page.width or 1200)

    return ft.View(
        route="/cimetiere/alleys-list",
        controls=[
            ft.Row([
                ft.Text("Allées du Cimetière", style=heading_style(size=22)),
                ft.Container(expand=True),
                ft.ElevatedButton("🔄 Actualiser", icon=ft.Icons.REFRESH, bgcolor=Colors.PRIMARY, color=Colors.TEXT_ON_DARK, on_click=lambda _: page.run_task(load_allees)),
                ft.ElevatedButton("🗺️ Voir sur la carte", icon=ft.Icons.MAP, on_click=lambda _: page.go("/carte")),
            ]),
            ft.Container(height=20),
            error_text, loading, list_container,
        ],
        bgcolor=Colors.BACKGROUND,
        padding=24 if device == "desktop" else 16,
        scroll=ft.ScrollMode.AUTO,
    )