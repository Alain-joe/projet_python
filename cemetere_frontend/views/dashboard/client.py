"""
views/dashboard/client.py — Espace personnel du client.
Compatible Flet 0.86.0

CORRECTION APPLIQUÉE :
- Détection de largeur de fenêtre sécurisée (page.width seul pouvait
  être None/obsolète) -> même pattern robuste que les autres vues.
"""
from __future__ import annotations
import flet as ft
from core.auth import AuthState
from core.api import ApiError, Endpoints
from core.theme import Colors, get_device_type, heading_style
from core.ui_utils import show_overlay, close_overlay

STATUS_LABELS = {"pending": "En attente", "confirmed": "Validée", "cancelled": "Annulée", "inhumee": "Inhumée"}
STATUS_COLORS = {"pending": "#F9A825", "confirmed": "#496042", "cancelled": "#C62828", "inhumee": "#8B8B8B"}


def build_client_dashboard_view(page: ft.Page, auth: AuthState) -> ft.View:
    error_text = ft.Text("", color=Colors.ERROR, size=13, visible=False)
    loading = ft.ProgressRing(visible=True, width=40, height=40)

    summary_row = ft.ResponsiveRow(spacing=12, run_spacing=12)
    reservations_list = ft.Column(spacing=8)
    invoices_list = ft.Column(spacing=8)
    concessions_list = ft.Column(spacing=8)
    notifications_list = ft.Column(spacing=8)
    notif_badge = ft.Container(
        content=ft.Text("0", size=10, color=Colors.TEXT_ON_DARK, weight=ft.FontWeight.BOLD),
        bgcolor="#C62828", border_radius=20, padding=ft.Padding(left=6, right=6, top=2, bottom=2), visible=False,
    )

    def show_reservation_details(res: dict) -> None:
        status = res.get("status", "pending")
        def close_dlg(_=None):
            close_overlay(page, dlg)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Réservation — Caveau {res.get('grave_code', '?')}"),
            content=ft.Column([
                ft.Text(f"Statut : {STATUS_LABELS.get(status, status)}"),
                ft.Text(f"Défunt : {res.get('deceased_last_name', '')} {res.get('deceased_first_name', '')}".strip()),
                ft.Text(f"Réservée le : {(res.get('reservation_date') or '')[:10] or 'N/A'}"),
                ft.Text(f"Note : {res.get('note') or '—'}"),
            ], tight=True, spacing=8),
            actions=[ft.TextButton("Fermer", on_click=close_dlg)],
        )
        show_overlay(page, dlg)

    def load_data() -> None:
        loading.visible, error_text.visible = True, False
        page.update()
        try:
            my_res = auth.api.get("/reservations/mine/")
            my_inv = auth.api.get("/finance/factures/mine")

            reservations = my_res if isinstance(my_res, list) else my_res.get("results", [])
            invoices = my_inv if isinstance(my_inv, list) else my_inv.get("results", [])

            def get_solde(inv):
                val = inv.get("montant_restant", inv.get("solde_restant", 0))
                try: return float(val) if val is not None else 0.0
                except (ValueError, TypeError): return 0.0

            solde_du = sum(get_solde(inv) for inv in invoices)
            actives = [r for r in reservations if r.get("status") != "cancelled"]
            unpaid_count = sum(1 for i in invoices if get_solde(i) > 0)

            try:
                notifs = auth.api.get(Endpoints.NOTIFICATIONS_LIST)
                notifs_list = notifs if isinstance(notifs, list) else notifs.get("results", [])
                unread = [n for n in notifs_list if not n.get("lu")]
                notif_badge.visible = len(unread) > 0
                if unread:
                    notif_badge.content.value = str(len(unread))
                render_notifications(notifs_list[:5])
            except Exception:
                render_notifications([])

            try:
                all_concessions = auth.api.get("/cemetery/concessions")
                concessions_data = all_concessions if isinstance(all_concessions, list) else all_concessions.get("results", [])
                my_concessions = [c for c in concessions_data if c.get("client_username") == auth.username and c.get("status") == "active"]
                render_concessions(my_concessions)
            except Exception:
                render_concessions([])

            kpis = [
                {"label": "Concessions/Réservations actives", "value": str(len(actives)), "icon": ft.Icons.DESCRIPTION, "color": "#496042"},
                {"label": "Factures en attente", "value": str(unpaid_count), "icon": ft.Icons.RECEIPT_LONG, "color": "#C62828"},
                {"label": "Solde total dû", "value": f"{solde_du:,.0f} FCFA".replace(",", " "), "icon": ft.Icons.ACCOUNT_BALANCE_WALLET, "color": "#F9A825"},
            ]
            summary_row.controls.clear()
            for kpi in kpis:
                summary_row.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Container(content=ft.Icon(kpi["icon"], color=Colors.TEXT_ON_DARK, size=24), bgcolor=kpi["color"], padding=10, border_radius=10),
                            ft.Column([ft.Text(kpi["label"], size=11, color=Colors.NEUTRAL), ft.Text(kpi["value"], size=18, weight=ft.FontWeight.BOLD, color=Colors.TEXT)], spacing=2, expand=True),
                        ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=14, bgcolor="#FFFFFF", border_radius=12, border=ft.Border(top=ft.BorderSide(3, kpi["color"])),
                        shadow=ft.BoxShadow(spread_radius=0, blur_radius=8, color="#00000012"),
                        col={"sm": 12, "md": 4},
                    )
                )

            reservations_list.controls.clear()
            reservations_list.controls.append(ft.Text("Mes réservations", style=heading_style(size=16)))
            if not reservations:
                reservations_list.controls.append(ft.Text("Aucune réservation pour le moment.", color=Colors.NEUTRAL, italic=True))
            else:
                for r in reservations:
                    status = r.get("status", "pending")
                    reservations_list.controls.append(
                        ft.Container(
                            content=ft.Row([
                                ft.Text(f"Caveau {r.get('grave_code', '?')}", weight=ft.FontWeight.W_600),
                                ft.Container(content=ft.Text(STATUS_LABELS.get(status, status), size=11, color=Colors.TEXT_ON_DARK), bgcolor=STATUS_COLORS.get(status, "#8B8B8B"), padding=ft.Padding(left=8, right=8, top=3, bottom=3), border_radius=10),
                                ft.TextButton("Détails", on_click=lambda _, res=r: show_reservation_details(res)),
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            padding=12, bgcolor="#FFFFFF", border_radius=8, border=ft.Border.all(1, Colors.BORDER),
                        )
                    )

            invoices_list.controls.clear()
            invoices_list.controls.append(ft.Text("Mes factures", style=heading_style(size=16)))
            if not invoices:
                invoices_list.controls.append(ft.Text("Aucune facture pour le moment.", color=Colors.NEUTRAL, italic=True))
            else:
                for inv in invoices:
                    solde = get_solde(inv)
                    payee = solde <= 0
                    invoices_list.controls.append(
                        ft.Container(
                            content=ft.Row([
                                ft.Text(f"Facture #{inv.get('numero', inv.get('id', '?'))}", weight=ft.FontWeight.W_600),
                                ft.Text("Soldée" if payee else f"Solde : {solde:,.0f} FCFA".replace(",", " "), color=Colors.PRIMARY if payee else Colors.ERROR, size=12),
                                ft.TextButton("Payer" if not payee else "Voir", on_click=lambda _, iid=inv.get('id'): page.go(f"/paiements?invoice_id={iid}")),
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            padding=12, bgcolor="#FFFFFF", border_radius=8, border=ft.Border.all(1, Colors.BORDER),
                        )
                    )
        except ApiError as exc:
            error_text.value = f"Impossible de charger vos informations : {exc.message}"
            error_text.visible = True
        finally:
            loading.visible = False
            page.update()

    def render_concessions(items):
        concessions_list.controls.clear()
        concessions_list.controls.append(ft.Text("Mes concessions", style=heading_style(size=16)))
        if not items:
            concessions_list.controls.append(ft.Text("Aucune concession active.", color=Colors.NEUTRAL, italic=True))
        else:
            for c in items:
                concessions_list.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Text(f"Caveau {c.get('grave_code', '?')}", weight=ft.FontWeight.W_600),
                            ft.Text(f"Type : {c.get('type_concession', 'N/A').capitalize()}", size=12, color=Colors.NEUTRAL),
                            ft.TextButton("Détails", on_click=lambda _, cid=c.get('id'): page.go(f"/concessions/detail?concession_id={cid}")),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        padding=12, bgcolor="#FFFFFF", border_radius=8, border=ft.Border.all(1, Colors.BORDER),
                    )
                )

    def render_notifications(items) -> None:
        notifications_list.controls.clear()
        if not items:
            notifications_list.controls.append(ft.Text("Aucune notification.", color=Colors.NEUTRAL, italic=True))
            return
        for n in items:
            lu = n.get("lu", False)
            notifications_list.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.NOTIFICATIONS if not lu else ft.Icons.NOTIFICATIONS_NONE,
                                color="#496042" if not lu else Colors.NEUTRAL, size=18),
                        ft.Column([
                            ft.Text(n.get("titre", "Notification"), size=13, weight=ft.FontWeight.W_600 if not lu else ft.FontWeight.NORMAL),
                            ft.Text(n.get("message", ""), size=11, color=Colors.NEUTRAL),
                        ], spacing=2, expand=True),
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=10, bgcolor="#FFFFFF", border_radius=8,
                    border=ft.Border(left=ft.BorderSide(3, "#496042" if not lu else Colors.BORDER)),
                    on_click=(lambda _, nid=n.get("id"): mark_notif_read(nid)) if not lu else None,
                )
            )

    def mark_notif_read(notif_id):
        try:
            auth.api.put(Endpoints.notification_read(notif_id))
            load_data()
        except Exception:
            pass

    load_data()

    # ✅ FIX : détection de largeur robuste — évite de figer le layout
    # en mode desktop si page.width est None/obsolète.
    width = getattr(page, 'window', page).width if hasattr(page, 'window') else (getattr(page, 'width', 1200) or 1200)
    device = get_device_type(width)

    return ft.View(
        route="/dashboard/client",
        controls=[
            ft.Column([
                ft.Row([
                    ft.Text(f"Bonjour, {auth.username or 'Client'} 👋", style=heading_style(size=24)),
                    ft.Container(expand=True),
                    ft.Stack([
                        ft.IconButton(icon=ft.Icons.NOTIFICATIONS_OUTLINED, tooltip="Notifications", on_click=lambda _: page.go("/notifications")),
                        ft.Container(content=notif_badge, alignment=ft.Alignment.TOP_RIGHT),
                    ], width=40, height=40),
                    ft.IconButton(icon=ft.Icons.PERSON_OUTLINE, tooltip="Modifier mon profil", on_click=lambda _: page.go("/profil")),
                    ft.ElevatedButton(
                        content=ft.Row([ft.Icon(ft.Icons.LOGOUT, size=18), ft.Text("Se déconnecter")], spacing=6),
                        on_click=lambda _: (auth.logout(), page.go("/login")),
                    ),
                ]),
                ft.Container(height=10),
                ft.Text("Bienvenue dans votre espace personnel. Voici un récapitulatif de vos démarches.", size=14, color=Colors.NEUTRAL),
                ft.Container(height=20),
                ft.Row([
                    ft.ElevatedButton(
                        content=ft.Row([ft.Icon(ft.Icons.MAP, color=Colors.TEXT_ON_DARK), ft.Text("Réserver un caveau", color=Colors.TEXT_ON_DARK, weight=ft.FontWeight.BOLD)], spacing=5),
                        style=ft.ButtonStyle(bgcolor=Colors.PRIMARY),
                        width=300, height=50,
                        on_click=lambda _: page.go("/carte"),
                    )
                ], alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(height=20),
                loading, error_text, summary_row, ft.Container(height=20),
                ft.ResponsiveRow([
                    ft.Container(content=reservations_list, padding=20, bgcolor="#FFFFFF", border_radius=12, shadow=ft.BoxShadow(spread_radius=0, blur_radius=8, color="#00000012"), col={"sm": 12, "md": 4}),
                    ft.Container(content=invoices_list, padding=20, bgcolor="#FFFFFF", border_radius=12, shadow=ft.BoxShadow(spread_radius=0, blur_radius=8, color="#00000012"), col={"sm": 12, "md": 4}),
                    ft.Container(content=ft.Column([ft.Text("Notifications récentes", style=heading_style(size=16)), ft.Container(height=10), notifications_list]), padding=20, bgcolor="#FFFFFF", border_radius=12, shadow=ft.BoxShadow(spread_radius=0, blur_radius=8, color="#00000012"), col={"sm": 12, "md": 4}),
                ], spacing=16, run_spacing=16),
                ft.Container(height=20),
                ft.Container(content=concessions_list, padding=20, bgcolor="#FFFFFF", border_radius=12, shadow=ft.BoxShadow(spread_radius=0, blur_radius=8, color="#00000012")),
            ]),
        ],
        bgcolor=Colors.BACKGROUND,
        padding=24 if device == "desktop" else 16,
    )