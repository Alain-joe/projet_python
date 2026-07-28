"""
views/notifications/list.py — Historique complet des notifications.
Compatible Flet 0.86.0

CORRECTIONS APPLIQUÉES :
- mark_all_read() utilise désormais show_overlay() au lieu de
  page.snack_bar / .open=True (pattern obsolète, source d'échecs
  silencieux sous Flet 0.86 -> même correction que list.py
  (réservations) et logs.py).
- Ajout du type 'nouvel_utilisateur' dans NOTIF_TYPE_LABELS/ICONS/
  COLORS (créé côté backend dans notifications/utils.py pour
  prévenir admin/secrétariat lors de la création d'un compte).
"""
from __future__ import annotations
import asyncio
import flet as ft
from datetime import datetime
from core.auth import AuthState
from core.theme import Colors, get_device_type, heading_style
from core.ui_utils import show_overlay

NOTIF_TYPE_LABELS = {
    "nouvelle_reservation": "Nouvelle réservation",
    "retard_paiement": "Retard de paiement",
    "concession_expirante": "Concession expirante",
    "reservation_validee": "Réservation validée",
    "reservation_annulee": "Réservation annulée",
    "facture_payee": "Facture payée",
    "exhumation_validee": "Exhumation validée",
    "nouvel_utilisateur": "Nouvel utilisateur",
}

NOTIF_TYPE_ICONS = {
    "nouvelle_reservation": ft.Icons.EVENT_NOTE,
    "retard_paiement": ft.Icons.WARNING,
    "concession_expirante": ft.Icons.HOURGLASS_TOP,
    "reservation_validee": ft.Icons.CHECK_CIRCLE,
    "reservation_annulee": ft.Icons.CANCEL,
    "facture_payee": ft.Icons.PAYMENTS,
    "exhumation_validee": ft.Icons.UNARCHIVE,
    "nouvel_utilisateur": ft.Icons.PERSON_ADD,
}

NOTIF_TYPE_COLORS = {
    "nouvelle_reservation": "#2E7D9A",
    "retard_paiement": "#8A4343",
    "concession_expirante": "#8B6B3F",
    "reservation_validee": "#496042",
    "reservation_annulee": "#8A4343",
    "facture_payee": "#496042",
    "exhumation_validee": "#2E7D9A",
    "nouvel_utilisateur": "#2E7D9A",
}


def build_notifications_list_view(page: ft.Page, auth: AuthState) -> ft.View:
    notifications = []
    current_filter = "all"  # all, unread, read
    loading = ft.ProgressRing(visible=True)
    error_text = ft.Text("", color=Colors.ERROR, size=13, visible=False)
    empty_text = ft.Text("Aucune notification.", color=Colors.NEUTRAL, italic=True, visible=False)
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
        page.run_task(load_notifications)

    for key, label in [("all", "Toutes"), ("unread", "Non lues"), ("read", "Lues")]:
        btn = ft.ElevatedButton(content=ft.Text(label, size=12), style=_filter_style(key == current_filter))
        btn.on_click = lambda _, k=key, b=btn: on_filter_click(k, b)
        filter_buttons.append(btn)

    async def load_notifications() -> None:
        loading.visible = True
        error_text.visible = False
        empty_text.visible = False
        page.update()

        try:
            data = auth.api.get("/notifications/notifications")
            notifications.clear()

            if isinstance(data, list):
                # Applique le filtre côté client (simple et efficace)
                if current_filter == "unread":
                    notifications.extend([n for n in data if not n.get("lu", False)])
                elif current_filter == "read":
                    notifications.extend([n for n in data if n.get("lu", False)])
                else:
                    notifications.extend(data)

            render_list()
        except Exception as exc:
            error_text.value = f"Erreur de chargement : {exc}"
            error_text.visible = True
        finally:
            loading.visible = False
            page.update()

    def render_list():
        list_container.controls.clear()

        if not notifications:
            empty_text.visible = True
        else:
            empty_text.visible = False
            for notif in notifications:
                list_container.controls.append(build_notification_card(notif))
        page.update()

    def build_notification_card(notif: dict) -> ft.Control:
        type_raw = str(notif.get("type_notification") or "info")
        type_lbl = NOTIF_TYPE_LABELS.get(type_raw, type_raw)
        icon = NOTIF_TYPE_ICONS.get(type_raw, ft.Icons.NOTIFICATIONS)
        color = NOTIF_TYPE_COLORS.get(type_raw, Colors.NEUTRAL)

        titre = str(notif.get("titre") or "Notification")
        message = str(notif.get("message") or "")
        is_read = notif.get("lu", False)
        notif_id = notif.get("id")

        ts_str = str(notif.get("created_at") or "")
        try:
            dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            date_fmt = dt.strftime("%d/%m/%Y %H:%M")
        except Exception:
            date_fmt = ts_str[:16] if ts_str else "N/A"

        def mark_read(e):
            try:
                auth.api.put(f"/notifications/notifications/{notif_id}/read")
                notif["lu"] = True
                render_list()
                # Met à jour le badge global
                page.go(page.route)
            except Exception:
                pass

        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(icon, color=color, size=24),
                    ft.Column([
                        ft.Text(titre, weight=ft.FontWeight.BOLD if not is_read else ft.FontWeight.NORMAL, size=14),
                        ft.Text(f"{type_lbl} • {date_fmt}", size=11, color=Colors.NEUTRAL),
                    ], spacing=2, expand=True),
                    ft.TextButton(
                        content=ft.Row([ft.Icon(ft.Icons.DONE, size=16), ft.Text("Marquer lu", size=12)]),
                        on_click=mark_read,
                        visible=not is_read,
                    ),
                ]),
                ft.Container(height=8),
                ft.Text(message, size=13, color=Colors.NEUTRAL),
            ], spacing=6),
            padding=16,
            bgcolor="#F5F3EE" if not is_read else "#FFFFFF",
            border_radius=10,
            border=ft.Border(
                left=ft.BorderSide(4, color if not is_read else Colors.BORDER),
                right=ft.BorderSide(1, Colors.BORDER),
                top=ft.BorderSide(1, Colors.BORDER),
                bottom=ft.BorderSide(1, Colors.BORDER),
            ),
        )

    def mark_all_read(e):
        try:
            auth.api.put("/notifications/notifications/read-all")
            show_overlay(page, ft.SnackBar(content=ft.Text("✅ Toutes les notifications marquées comme lues."), bgcolor=Colors.PRIMARY))
            page.go(page.route)
        except Exception as exc:
            error_text.value = f"Erreur : {exc}"
            error_text.visible = True
            page.update()

    device = get_device_type(page.width or 1200)
    page.run_task(load_notifications)

    return ft.View(
        route="/notifications",
        controls=[
            ft.Row([
                ft.Text("Mes Notifications", style=heading_style(size=22)),
                ft.Container(expand=True),
                ft.ElevatedButton(
                    "Tout marquer comme lu",
                    icon=ft.Icons.DONE_ALL,
                    bgcolor=Colors.PRIMARY,
                    color=Colors.TEXT_ON_DARK,
                    on_click=mark_all_read,
                ),
            ]),
            ft.Container(height=10),
            ft.Row(filter_buttons, wrap=True, spacing=8),
            ft.Container(height=15),
            error_text,
            loading,
            empty_text,
            list_container,
        ],
        bgcolor=Colors.BACKGROUND,
        padding=16 if device == "mobile" else 32,
        scroll=ft.ScrollMode.AUTO,
    )