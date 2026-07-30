"""
views/reservations/client_list.py — Liste des réservations pour le Client.
Compatible Flet 0.86.3. Lecture seule, sans boutons de validation admin.
"""
from __future__ import annotations
from datetime import date, datetime
import flet as ft
from core.auth import AuthState
from core.api import Endpoints
from core.theme import Colors, get_device_type, heading_style, status_color

STATUS_FILTERS = [("all", "Toutes"), ("attente", "En attente"), ("validees", "Validées"), ("terminees", "Terminées")]
RESERVATION_STATUS_LABEL = {"pending": "En attente", "confirmed": "Validée", "cancelled": "Annulée", "inhumee": "Inhumée"}

def _is_inhumed(r: dict) -> bool:
    return r.get("status") == "inhumee" or bool(r.get("inhumation")) or bool(r.get("is_inhumed"))

def build_client_reservations_list_view(page: ft.Page, auth: AuthState) -> ft.View:
    reservations: list[dict] = []
    current_filter = "all"
    error_text = ft.Text("", color=Colors.ERROR, size=13, visible=False)
    loading = ft.ProgressRing(visible=True)
    list_container = ft.Column(spacing=10)
    filter_buttons = []

    def _filter_style(active: bool) -> ft.ButtonStyle:
        return ft.ButtonStyle(
            bgcolor=Colors.PRIMARY if active else "#FFFFFF",
            color=Colors.TEXT_ON_DARK if active else Colors.TEXT,
            side=ft.BorderSide(1, Colors.PRIMARY if active else Colors.BORDER),
        )

    def on_filter_click(filter_key: str, btn: ft.ElevatedButton):
        nonlocal current_filter
        current_filter = filter_key
        for b in filter_buttons:
            b.style = _filter_style(b == btn)
        page.update()
        render_list()

    for key, label in STATUS_FILTERS:
        btn = ft.ElevatedButton(content=ft.Text(label, size=12), style=_filter_style(key == current_filter))
        btn.on_click = lambda _, k=key, b=btn: on_filter_click(k, b)
        filter_buttons.append(btn)

    def get_filtered() -> list[dict]:
        if current_filter == "all": return reservations
        if current_filter == "attente": return [r for r in reservations if r.get("status") == "pending"]
        if current_filter == "validees": return [r for r in reservations if r.get("status") == "confirmed" and not _is_inhumed(r)]
        if current_filter == "terminees": return [r for r in reservations if _is_inhumed(r)]
        return reservations

    def load_reservations() -> None:
        loading.visible, error_text.visible = True, False
        page.update()
        try:
            # ✅ CORRECTION : Appel de l'endpoint spécifique au client
            data = auth.api.get_reservations_mine()
            reservations.clear()
            if isinstance(data, list): 
                reservations.extend(data)
            elif isinstance(data, dict): 
                reservations.extend(data.get("items", data.get("results", data.get("data", []))))
            render_list()
        except Exception as exc:
            error_text.value, error_text.visible = f"Erreur : {exc}", True
        finally:
            loading.visible = False
            page.update()

    def build_row(res: dict) -> ft.Control:
        status = res.get("status", "pending")
        inhumed = _is_inhumed(res)

        if inhumed: 
            label, color = "Inhumée", "#496042"
        else:
            label = RESERVATION_STATUS_LABEL.get(status, status)
            color = status_color({"pending": "reserved", "confirmed": "occupied", "cancelled": "non_exploitable"}.get(status, "non_exploitable"))

        badge = ft.Container(content=ft.Text(label, size=12, color=Colors.TEXT_ON_DARK), bgcolor=color, padding=8, border_radius=12)
        
        # ✅ Pour le client, pas de bouton d'action, juste un affichage
        action = ft.Text("—", color=Colors.NEUTRAL, size=14)

        date_str = res.get("reservation_date", "")[:10] if res.get("reservation_date") else "Date inconnue"
        date_prevue = res.get("date_prevue_inhumation") or "—"
        grave_display = res.get("grave_code") or f"ID: {res.get('grave_id', '?')}"

        return ft.Container(
            content=ft.Row([
                ft.Column([
                    ft.Text(f"Caveau {grave_display}", weight=ft.FontWeight.W_600, size=14),
                    ft.Text(f"Réservée le : {date_str} • Inhumation prévue : {date_prevue}", size=11, color=Colors.NEUTRAL, italic=True),
                ], spacing=4, expand=True),
                badge, 
                action,
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=14, bgcolor="#FFFFFF", border_radius=10, border=ft.Border.all(1, Colors.BORDER),
        )

    def render_list() -> None:
        list_container.controls.clear()
        filtered = get_filtered()
        if not filtered:
            list_container.controls.append(
                ft.Container(
                    content=ft.Text("Aucune réservation.", color=Colors.NEUTRAL, italic=True), 
                    padding=40, 
                    alignment=ft.Alignment(0.5, 0.5)
                )
            )
        else:
            for res in filtered: 
                list_container.controls.append(build_row(res))
        page.update()

    device = get_device_type(page.width or 1200)
    load_reservations()

    return ft.View(
        route="/reservations/mine",
        controls=[
            ft.Row([
                ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: page.go("/dashboard/client")),
                ft.Text("Mes Réservations", style=heading_style(size=22)),
            ]),
            ft.Container(height=10),
            ft.Row(filter_buttons, wrap=True, spacing=8),
            ft.Container(height=15),
            error_text,
            loading,
            list_container,
        ],
        bgcolor=Colors.BACKGROUND,
        padding=16 if device == "mobile" else 32,
    )