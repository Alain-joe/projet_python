"""
views/concessions/ready_list.py — Liste des dossiers prêts pour création de concession.
Compatible Flet 0.86.0
"""
from __future__ import annotations
import flet as ft
from core.auth import AuthState
from core.api import Endpoints
from core.theme import Colors, get_device_type, heading_style


def build_concessions_ready_view(page: ft.Page, auth: AuthState) -> ft.View:
    ready_dossiers = []
    loading = ft.ProgressRing(visible=True)
    error_text = ft.Text("", color=Colors.ERROR, size=13, visible=False)
    list_container = ft.Column(spacing=10)

    def load_data():
        loading.visible, error_text.visible = True, False
        page.update()
        try:
            data = auth.api.get(Endpoints.CONCESSIONS_READY)
            ready_dossiers.clear()
            if isinstance(data, list):
                ready_dossiers.extend(data)
            render_list()
        except Exception as exc:
            error_text.value = f"Erreur de chargement : {exc}"
            error_text.visible = True
        finally:
            loading.visible = False
            page.update()

    def render_list():
        list_container.controls.clear()
        if not ready_dossiers:
            list_container.controls.append(
                ft.Container(
                    content=ft.Text("Aucun dossier en attente de création de concession.", color=Colors.NEUTRAL, italic=True),
                    padding=40, alignment=ft.Alignment(0.5, 0.5)
                )
            )
        else:
            for dossier in ready_dossiers:
                list_container.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Column([
                                ft.Text(f"Caveau {dossier.get('grave_code', '?')}", weight=ft.FontWeight.W_600, size=14),
                                ft.Text(f"Client : {dossier.get('client_username', 'N/A')}", size=12, color=Colors.NEUTRAL),
                                ft.Text(f"Montant payé : {dossier.get('montant', 0):,.0f} FCFA".replace(",", " "), size=12, color="#496042"),
                            ], spacing=4, expand=True),
                            ft.ElevatedButton(
                                "Créer la concession",
                                icon=ft.Icons.DESCRIPTION,
                                bgcolor=Colors.PRIMARY,
                                color=Colors.TEXT_ON_DARK,
                                on_click=lambda _, rid=dossier.get('reservation_id'): page.go(f"/concessions/nouvelle?reservation_id={rid}"),
                            ),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=14, bgcolor="#FFFFFF", border_radius=10, border=ft.Border(left=ft.BorderSide(4, "#496042")),
                    )
                )
        page.update()

    load_data()
    device = get_device_type(page.width or 1200)

    return ft.View(
        route="/concessions/ready",
        controls=[
            ft.Row([
                ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: page.go("/concessions")),
                ft.Text("Concessions à créer", style=heading_style(size=22)),
            ]),
            ft.Container(height=10),
            ft.Text("Dossiers dont la réservation est validée et la facture entièrement payée.", size=14, color=Colors.NEUTRAL),
            ft.Container(height=20),
            loading, error_text, list_container,
        ],
        bgcolor=Colors.BACKGROUND,
        padding=24 if device == "desktop" else 16,
        scroll=ft.ScrollMode.AUTO,
    )