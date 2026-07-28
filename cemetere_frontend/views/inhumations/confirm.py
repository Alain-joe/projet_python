"""
views/inhumations/confirm.py — Formulaire de confirmation d'inhumation pour l'Agent.
Compatible Flet 0.86.3. Utilise DatePicker et TimePicker natifs.
"""
from __future__ import annotations
import flet as ft
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta

from core.auth import AuthState, Role
from core.api import ApiError, Endpoints
from core.theme import Colors, get_device_type, heading_style


def build_inhumation_confirm_view(page: ft.Page, auth: AuthState) -> ft.View:
    query = parse_qs(urlparse(page.route).query)
    reservation_id = query.get("reservation_id", [None])[0]

    if not reservation_id:
        page.go("/inhumations")
        return ft.View(route="/inhumations/confirm", controls=[])

    loading = ft.ProgressRing(visible=True, width=40, height=40)
    error_text = ft.Text("", color=Colors.ERROR, size=13, visible=False)
    
    reservation_data = {}

    # --- PICKERS ---
    date_reelle_picker = ft.DatePicker(
        first_date=datetime.now() - timedelta(days=3650), # 10 ans en arrière
        last_date=datetime.now(), # ✅ Pas dans le futur
        on_change=lambda e: setattr(date_reelle_field, 'value', e.control.value.strftime("%Y-%m-%d") if e.control.value else ""),
    )
    page.overlay.append(date_reelle_picker)

    time_picker = ft.TimePicker(
        on_change=lambda e: setattr(heure_field, 'value', e.control.value.strftime("%H:%M") if e.control.value else ""),
    )
    page.overlay.append(time_picker)

    # --- CHAMPS ---
    date_reelle_field = ft.TextField(
        label="Date réelle d'inhumation (AAAA-MM-JJ) *", 
        read_only=True, 
        border_radius=8, 
        suffix=ft.Icon(ft.Icons.CALENDAR_TODAY, color=Colors.PRIMARY),
        on_click=lambda _: date_reelle_picker.pick_date()
    )
    
    heure_field = ft.TextField(
        label="Heure d'inhumation (HH:MM) *", 
        read_only=True, 
        border_radius=8, 
        suffix=ft.Icon(ft.Icons.ACCESS_TIME, color=Colors.PRIMARY),
        on_click=lambda _: time_picker.pick_time()
    )
    
    observations_field = ft.TextField(
        label="Observations (optionnel)", 
        multiline=True, 
        min_lines=3, 
        border_radius=8
    )

    info_container = ft.Container(visible=False)

    def load_reservation():
        loading.visible, error_text.visible = True, False
        page.update()
        try:
            data = auth.api.get(f"/reservations/{reservation_id}/")
            reservation_data.update(data)
            
            # Mise à jour de la date min du picker en fonction de la date de réservation
            res_date_str = data.get("reservation_date", "")[:10]
            if res_date_str:
                try:
                    res_date = datetime.strptime(res_date_str, "%Y-%m-%d").date()
                    date_reelle_picker.first_date = datetime(res_date.year, res_date.month, res_date.day)
                except ValueError:
                    pass

            info_container.content = ft.Column([
                ft.Text(f"Caveau : {data.get('grave_code', 'N/A')}", weight=ft.FontWeight.W_600, size=16),
                ft.Text(f"Défunt : {data.get('deceased_last_name', '')} {data.get('deceased_first_name', '')}", size=14, color=Colors.NEUTRAL),
                ft.Text(f"Date prévue : {data.get('date_prevue_inhumation', 'N/A')}", size=13, color=Colors.NEUTRAL),
            ], spacing=8)
            info_container.visible = True
            
        except ApiError as exc:
            error_text.value = f"Erreur : {exc.message}"
            error_text.visible = True
        finally:
            loading.visible = False
            page.update()

    def on_confirm_click(_: ft.ControlEvent):
        if not date_reelle_field.value or not heure_field.value:
            error_text.value = "❌ La date et l'heure réelles sont obligatoires."
            error_text.visible = True
            page.update()
            return

        error_text.visible = False
        loading.visible = True
        page.update()

        try:
            payload = {
                "date_inhumation": f"{date_reelle_field.value}T{heure_field.value}:00",
                "observations": observations_field.value.strip()
            }
            auth.api.put(f"/reservations/{reservation_id}/confirmer-inhumation", json=payload)
            
            sb = ft.SnackBar(
                content=ft.Text("✅ Inhumation confirmée avec succès. Caveau marqué comme occupé.", color=Colors.TEXT_ON_DARK),
                bgcolor="#496042"
            )
            page.snack_bar = sb
            sb.open = True
            page.update()
            
            import asyncio
            async def redirect():
                await asyncio.sleep(1.5)
                page.go("/inhumations")
            page.run_task(redirect)
            
        except ApiError as exc:
            loading.visible = False
            error_text.value = f"❌ Échec : {exc.message}"
            error_text.visible = True
            page.update()

    load_reservation()

    width = getattr(page, 'window', page).width if hasattr(page, 'window') else (getattr(page, 'width', 1200) or 1200)
    device = get_device_type(width)

    return ft.View(
        route="/inhumations/confirm",
        controls=[
            ft.Row([
                ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: page.go("/inhumations")),
                ft.Text("Confirmer l'inhumation", style=heading_style(size=22)),
            ]),
            ft.Container(height=10),
            loading,
            error_text,
            ft.Container(
                content=ft.Column([
                    info_container,
                    ft.Divider(height=20, color=Colors.BORDER),
                    ft.Text("Détails de l'opération", style=heading_style(size=16)),
                    ft.Container(height=10),
                    date_reelle_field,
                    ft.Container(height=10),
                    heure_field,
                    ft.Container(height=10),
                    observations_field,
                    ft.Container(height=20),
                    ft.ElevatedButton(
                        content=ft.Row([ft.Icon(ft.Icons.CHECK_CIRCLE, color=Colors.TEXT_ON_DARK), ft.Text("Confirmer l'inhumation", color=Colors.TEXT_ON_DARK, weight=ft.FontWeight.BOLD)], spacing=8),
                        style=ft.ButtonStyle(bgcolor="#496042"),
                        width=float("inf"),
                        height=50,
                        on_click=on_confirm_click,
                    )
                ], spacing=0),
                padding=24, bgcolor="#FFFFFF", border_radius=12, width=600 if device != "mobile" else None,
            ),
        ],
        bgcolor=Colors.BACKGROUND,
        padding=16 if device == "mobile" else 32,
    )