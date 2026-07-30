"""
views/reservations/list_secretaire.py — Gestion des réservations (Secrétariat).
Compatible Flet 0.86.3. Le secrétariat peut valider, mais pas confirmer l'inhumation.
"""
from __future__ import annotations
from datetime import date, datetime
import flet as ft
from core.auth import AuthState
from core.api import Endpoints
from core.theme import Colors, get_device_type, heading_style, status_color
from core.ui_utils import show_overlay

STATUS_FILTERS = [("all", "Toutes"), ("attente", "En attente"), ("validees", "Validées"), ("a_inhumer", "À inhumer"), ("terminees", "Terminées")]
RESERVATION_STATUS_LABEL = {"pending": "En attente", "confirmed": "Validée", "cancelled": "Annulée", "inhumee": "Inhumée"}

def _is_inhumed(r: dict) -> bool: 
    return r.get("status") == "inhumee" or bool(r.get("inhumation")) or bool(r.get("is_inhumed"))

def _is_due_today_or_past(r: dict) -> bool:
    date_str = r.get("date_prevue_inhumation") or r.get("date_prevue", "") or ""
    if not date_str: 
        return False
    try:
        d = datetime.fromisoformat(date_str.replace("Z", "+00:00")).date() if "T" in date_str else datetime.strptime(date_str[:10], "%Y-%m-%d").date()
        return d <= date.today()
    except Exception: 
        return False

def build_reservations_list_secretaire_view(page: ft.Page, auth: AuthState) -> ft.View:
    reservations: list[dict] = []
    current_filter = "all"
    error_text = ft.Text("", color=Colors.ERROR, size=13, visible=False)
    loading = ft.ProgressRing(visible=True)
    list_container = ft.Column(spacing=10)
    stats_row = ft.Row(spacing=12, wrap=True)
    filter_buttons = []

    def _filter_style(active: bool) -> ft.ButtonStyle:
        return ft.ButtonStyle(
            bgcolor=Colors.PRIMARY if active else "#FFFFFF", 
            color=Colors.TEXT_ON_DARK if active else Colors.TEXT, 
            side=ft.BorderSide(1, Colors.PRIMARY if active else Colors.BORDER)
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

    def _snack(message: str, bgcolor: str) -> None: 
        show_overlay(page, ft.SnackBar(content=ft.Text(message), bgcolor=bgcolor))

    def get_filtered() -> list[dict]:
        if current_filter == "all": return reservations
        if current_filter == "attente": return [r for r in reservations if r.get("status") == "pending"]
        if current_filter == "validees": return [r for r in reservations if r.get("status") == "confirmed" and not _is_inhumed(r)]
        if current_filter == "a_inhumer": return [r for r in reservations if r.get("status") == "confirmed" and not _is_inhumed(r) and _is_due_today_or_past(r)]
        if current_filter == "terminees": return [r for r in reservations if _is_inhumed(r)]
        return reservations

    def render_stats() -> None:
        def chip(label, value, color): 
            return ft.Container(
                content=ft.Column([
                    ft.Text(str(value), size=18, weight=ft.FontWeight.BOLD, color=color), 
                    ft.Text(label, size=11, color=Colors.NEUTRAL)
                ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER), 
                padding=14, bgcolor="#FFFFFF", border_radius=10, border=ft.Border(top=ft.BorderSide(3, color))
            )
        a_inhumer = len([r for r in reservations if r.get("status") == "confirmed" and not _is_inhumed(r) and _is_due_today_or_past(r)])
        stats_row.controls = [
            chip("Total", len(reservations), Colors.PRIMARY), 
            chip("En attente", len([r for r in reservations if r.get("status") == "pending"]), "#8B6B3F"), 
            chip("À inhumer", a_inhumer, "#8A4343"), 
            chip("Terminées", len([r for r in reservations if _is_inhumed(r)]), "#496042")
        ]

    def load_reservations() -> None:
        loading.visible, error_text.visible = True, False
        page.update()
        try:
            data = auth.api.get(Endpoints.RESERVATIONS_LIST)
            reservations.clear()
            if isinstance(data, list): 
                reservations.extend(data)
            elif isinstance(data, dict): 
                reservations.extend(data.get("items", data.get("results", data.get("data", []))))
            render_stats()
            render_list()
        except Exception as exc: 
            error_text.value, error_text.visible = f"Erreur : {exc}", True
        finally: 
            loading.visible = False
            page.update()

    def build_row(res: dict) -> ft.Control:
        status = res.get("status", "pending")
        inhumed = _is_inhumed(res)
        due = status == "confirmed" and not inhumed and _is_due_today_or_past(res)
        
        label = "Inhumée" if inhumed else ("À inhumer" if due else RESERVATION_STATUS_LABEL.get(status, status))
        color = "#496042" if inhumed else ("#8A4343" if due else status_color({"pending": "reserved", "confirmed": "occupied", "cancelled": "non_exploitable"}.get(status, "non_exploitable")))
        
        badge = ft.Container(content=ft.Text(label, size=12, color=Colors.TEXT_ON_DARK), bgcolor=color, padding=8, border_radius=12)
        action = ft.Text("—", color=Colors.NEUTRAL, size=14)

        if status == "pending":
            def on_validate(e, r=res):
                try:
                    auth.api.put(Endpoints.reservation_update(r["id"]), json={"status": "confirmed", "note_validation": "Validée"})
                    _snack("✅ Réservation validée.", Colors.PRIMARY)
                    load_reservations()
                except Exception as exc: 
                    error_text.value, error_text.visible = f"Échec : {exc}", True
                    page.update()
            action = ft.ElevatedButton(
                content=ft.Text("Valider", color=Colors.TEXT_ON_DARK, size=13), 
                style=ft.ButtonStyle(bgcolor=Colors.PRIMARY), 
                on_click=on_validate
            )

        # ✅ CORRECTION : Extraction des variables pour éviter les f-strings imbriquées
        grave_display = res.get("grave_code") or f"ID: {res.get('grave_id', '?')}"
        client_display = res.get("client_username") or "Client"
        defunt_display = f"{res.get('deceased_last_name', '?')} {res.get('deceased_first_name', '')}".strip() or "?"
        date_prevue = res.get("date_prevue_inhumation") or "—"
        date_str = res.get("reservation_date", "")[:10] if res.get("reservation_date") else "Date inconnue"

        return ft.Container(
            content=ft.Row([
                ft.Column([
                    ft.Text(f"Caveau {grave_display}", weight=ft.FontWeight.W_600, size=14), 
                    ft.Text(f"{client_display} — Défunt : {defunt_display}", size=12, color=Colors.NEUTRAL), 
                    ft.Text(f"Réservée le : {date_str} • Inhumation prévue : {date_prevue}", size=11, color=Colors.NEUTRAL, italic=True)
                ], spacing=4, expand=True), 
                badge, 
                action
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER), 
            padding=14, 
            bgcolor="#FFFFFF", 
            border_radius=10, 
            border=ft.Border.all(1, Colors.BORDER)
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
        route="/reservations", 
        controls=[
            ft.Text("Gestion des Réservations", style=heading_style(size=22)), 
            ft.Container(height=10), 
            stats_row, 
            ft.Container(height=15), 
            ft.Row(filter_buttons, wrap=True, spacing=8), 
            ft.Container(height=15), 
            error_text, 
            loading, 
            list_container
        ], 
        bgcolor=Colors.BACKGROUND, 
        padding=16 if device == "mobile" else 32
    )