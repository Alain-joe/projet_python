"""
views/graves/signalements_list.py — Liste des signalements de caveaux.
Compatible Flet 0.86.0
"""
from __future__ import annotations
import flet as ft

from core.auth import AuthState
from core.api import ApiError
from core.theme import Colors, get_device_type, heading_style

STATUS_CONFIG = {
    "en_attente": {"label": "En attente", "color": "#F9A825", "icon": ft.Icons.PENDING},
    "valide": {"label": "Validé", "color": "#496042", "icon": ft.Icons.CHECK_CIRCLE},
    "rejete": {"label": "Rejeté", "color": "#C62828", "icon": ft.Icons.CANCEL},
}

FILTERS = [
    ("all", "Tous", ft.Icons.FILTER_LIST),
    ("en_attente", "En attente", ft.Icons.PENDING),
    ("valide", "Validés", ft.Icons.CHECK_CIRCLE),
    ("rejete", "Rejetés", ft.Icons.CANCEL),
]


def build_signalements_list_view(page: ft.Page, auth: AuthState) -> ft.View:
    signalements = []
    current_filter = "all"
    
    loading = ft.ProgressRing(visible=True)
    error_text = ft.Text("", color=Colors.ERROR, size=13, visible=False)
    list_container = ft.Column(spacing=10)

    def load_data():
        loading.visible, error_text.visible = True, False
        page.update()
        try:
            params = {"statut": current_filter} if current_filter != "all" else None
            data = auth.api.get_signalements(**params) if params else auth.api.get_signalements()
            signalements.clear()
            if isinstance(data, list):
                signalements.extend(data)
            elif isinstance(data, dict):
                signalements.extend(data.get("results", data.get("items", [])))
            render_list()
        except ApiError as exc:
            error_text.value = f"Erreur de chargement : {exc.message}"
            error_text.visible = True
        finally:
            loading.visible = False
            page.update()

    def render_list():
        list_container.controls.clear()
        if not signalements:
            list_container.controls.append(
                ft.Container(
                    content=ft.Text("Aucun signalement trouvé.", color=Colors.NEUTRAL, italic=True),
                    padding=40, alignment=ft.Alignment(0.5, 0.5)
                )
            )
        else:
            for sig in signalements:
                config = STATUS_CONFIG.get(sig.get("statut"), STATUS_CONFIG["en_attente"])
                list_container.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Column([
                                ft.Text(f"Caveau {sig.get('grave_code', '?')}", weight=ft.FontWeight.W_600, size=14),
                                ft.Text(sig.get("motif", "")[:60] + ("..." if len(sig.get("motif", "")) > 60 else ""), size=12, color=Colors.NEUTRAL),
                                ft.Text(f"Signalé par : {sig.get('signale_par', 'Inconnu')} • {str(sig.get('date_signalement', ''))[:10]}", size=11, color=Colors.NEUTRAL),
                            ], spacing=4, expand=True),
                            ft.Container(
                                content=ft.Row([
                                    ft.Icon(config["icon"], size=16, color=Colors.TEXT_ON_DARK),
                                    ft.Text(config["label"], size=12, color=Colors.TEXT_ON_DARK)
                                ], spacing=4),
                                bgcolor=config["color"],
                                padding=ft.Padding(left=8, top=4, right=8, bottom=4),
                                border_radius=12,
                            ),
                            ft.IconButton(
                                icon=ft.Icons.ARROW_FORWARD_IOS,
                                tooltip="Voir les détails",
                                on_click=lambda _, s=sig: page.go(f"/graves/signalements/detail?signalement_id={s['id']}")
                            )
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=14,
                        bgcolor="#FFFFFF",
                        border_radius=10,
                        border=ft.Border.all(1, Colors.BORDER),
                    )
                )
        page.update()

    def on_filter_click(filter_key: str, btn: ft.ElevatedButton):
        nonlocal current_filter
        current_filter = filter_key
        for b in filter_buttons:
            b.style = ft.ButtonStyle(
                bgcolor=Colors.PRIMARY if b == btn else "#FFFFFF",
                color=Colors.TEXT_ON_DARK if b == btn else Colors.TEXT,
                side=ft.BorderSide(1, Colors.PRIMARY if b == btn else Colors.BORDER),
            )
        page.update()
        load_data()

    filter_buttons = []
    for key, label, icon in FILTERS:
        btn = ft.ElevatedButton(
            content=ft.Row([ft.Icon(icon, size=14), ft.Text(label, size=12)], spacing=4),
            style=ft.ButtonStyle(
                bgcolor=Colors.PRIMARY if key == current_filter else "#FFFFFF",
                color=Colors.TEXT_ON_DARK if key == current_filter else Colors.TEXT,
                side=ft.BorderSide(1, Colors.PRIMARY if key == current_filter else Colors.BORDER),
            ),
        )
        btn.on_click = lambda _, k=key, b=btn: on_filter_click(k, b)
        filter_buttons.append(btn)

    load_data()
    device = get_device_type(page.width or 1200)

    return ft.View(
        route="/graves/signalements",
        controls=[
            ft.Text("Signalements de Caveaux", style=heading_style(size=22)),
            ft.Container(height=10),
            ft.Row(filter_buttons, wrap=True, spacing=8),
            ft.Container(height=15),
            error_text,
            loading,
            list_container,
        ],
        bgcolor=Colors.BACKGROUND,
        padding=24 if device == "desktop" else 16,
        scroll=ft.ScrollMode.AUTO,
    )