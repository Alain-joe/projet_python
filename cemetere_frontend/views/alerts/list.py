"""
views/alerts/list.py — Centralisation des alertes et notifications.
Cahier des charges 6 : Alertes Admin (réservations, retards, concessions).
Compatible Flet 0.86.0
"""

from __future__ import annotations
import flet as ft
from datetime import datetime, date

from core.auth import AuthState
from core.api import ApiError, Endpoints
from core.theme import Colors, get_device_type, heading_style

# Configuration des niveaux de sévérité
SEVERITY_CONFIG = {
    "critical": {"label": "Critique", "color": "#8A4343", "icon": ft.Icons.ERROR},
    "warning": {"label": "Attention", "color": "#8B6B3F", "icon": ft.Icons.WARNING},
    "info": {"label": "Info", "color": "#2E7D9A", "icon": ft.Icons.INFO},
}


def build_alerts_view(page: ft.Page, auth: AuthState) -> ft.View:
    alerts_data = {
        "concessions_expiring": [],
        "pending_reservations": [],
        "overdue_payments": []
    }

    loading = ft.ProgressRing(visible=True)
    error_text = ft.Text("", color=Colors.ERROR, size=13, visible=False)

    # Conteneurs pour chaque section
    concessions_list = ft.Column(spacing=10)
    reservations_list = ft.Column(spacing=10)
    payments_list = ft.Column(spacing=10)

    # KPI Cards
    # ✅ padding normalisé en ft.Padding(...) plutôt qu'un tuple brut
    # (forme la plus fiable et cohérente avec le reste de l'app en 0.86).
    kpi_concessions = ft.Container(
        content=ft.Column([
            ft.Icon(ft.Icons.EVENT_BUSY, color="#8A4343", size=30),
            ft.Text("Concessions à échoir", size=12, color=Colors.NEUTRAL),
            ft.Text("0", size=24, weight=ft.FontWeight.BOLD, color="#8A4343"),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
        padding=ft.Padding(left=20, top=20, right=20, bottom=20),
        bgcolor="#FFFFFF", border_radius=12,
        border=ft.Border(left=ft.BorderSide(4, "#8A4343"))
    )

    kpi_reservations = ft.Container(
        content=ft.Column([
            ft.Icon(ft.Icons.PENDING, color="#8B6B3F", size=30),
            ft.Text("Réservations en attente", size=12, color=Colors.NEUTRAL),
            ft.Text("0", size=24, weight=ft.FontWeight.BOLD, color="#8B6B3F"),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
        padding=ft.Padding(left=20, top=20, right=20, bottom=20),
        bgcolor="#FFFFFF", border_radius=12,
        border=ft.Border(left=ft.BorderSide(4, "#8B6B3F"))
    )

    kpi_payments = ft.Container(
        content=ft.Column([
            ft.Icon(ft.Icons.PAYMENTS, color="#2E7D9A", size=30),
            ft.Text("Paiements en retard", size=12, color=Colors.NEUTRAL),
            ft.Text("0", size=24, weight=ft.FontWeight.BOLD, color="#2E7D9A"),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
        padding=ft.Padding(left=20, top=20, right=20, bottom=20),
        bgcolor="#FFFFFF", border_radius=12,
        border=ft.Border(left=ft.BorderSide(4, "#2E7D9A"))
    )

    kpi_row = ft.ResponsiveRow([
        ft.Container(content=kpi_concessions, col={"sm": 12, "md": 4}),
        ft.Container(content=kpi_reservations, col={"sm": 12, "md": 4}),
        ft.Container(content=kpi_payments, col={"sm": 12, "md": 4}),
    ], spacing=16, run_spacing=16)

    def load_alerts() -> None:
        loading.visible = True
        error_text.visible = False
        page.update()

        today = date.today()

        # 1. Charger les réservations en attente (API Réelle)
        try:
            res_data = auth.api.get(Endpoints.RESERVATIONS_LIST, params={"status": "pending"})
            res_list = res_data if isinstance(res_data, list) else res_data.get("results", res_data.get("items", []))

            alerts_data["pending_reservations"] = [
                {
                    "id": r.get("id"),
                    "username": r.get("client_username", "Inconnu"),
                    "grave_code": r.get("grave_code", f"ID:{r.get('grave_id')}"),
                    "created_at": r.get("reservation_date", "")[:10] if r.get("reservation_date") else "récemment"
                }
                for r in res_list
            ]
        except ApiError:
            pass  # On garde la liste vide en cas d'erreur

        # 2. Charger les concessions et filtrer celles qui expirent dans <= 30 jours
        try:
            conc_data = auth.api.get(Endpoints.CONCESSIONS)
            conc_list = conc_data if isinstance(conc_data, list) else conc_data.get("results", conc_data.get("items", []))

            expiring = []
            for c in conc_list:
                if c.get("date_fin") and c.get("status") == "active":
                    try:
                        d_fin = datetime.strptime(c.get("date_fin"), "%Y-%m-%d").date()
                        days_left = (d_fin - today).days
                        if 0 <= days_left <= 30:
                            expiring.append({
                                "id": c.get("id"),
                                "grave_code": c.get("grave_code", f"ID:{c.get('grave_id')}"),
                                "client": c.get("client_username", "Inconnu"),
                                "date_fin": c.get("date_fin"),
                                "days_left": days_left
                            })
                    except ValueError:
                        pass
            alerts_data["concessions_expiring"] = expiring
        except ApiError:
            pass

        # 3. Charger les factures et filtrer les paiements en retard
        try:
            fact_data = auth.api.get(Endpoints.FACTURES)
            fact_list = fact_data if isinstance(fact_data, list) else fact_data.get("results", fact_data.get("items", []))

            overdue = []
            for f in fact_list:
                if f.get("statut") in ["en_attente", "partielle"] and f.get("date_echeance"):
                    try:
                        d_ech = datetime.strptime(f.get("date_echeance"), "%Y-%m-%d").date()
                        days_overdue = (today - d_ech).days
                        if days_overdue > 0:
                            overdue.append({
                                "id": f.get("id"),
                                "facture": f.get("numero", "N/A"),
                                "client": f.get("client_username", "Inconnu"),
                                "amount": f.get("montant_restant", f.get("montant_total", 0)),
                                "days_overdue": days_overdue
                            })
                    except ValueError:
                        pass
            alerts_data["overdue_payments"] = overdue
        except ApiError:
            pass

        loading.visible = False
        render_alerts()

    def build_alert_item(title: str, subtitle: str, severity: str, action_text: str = "Voir", on_click=None) -> ft.Control:
        config = SEVERITY_CONFIG.get(severity, SEVERITY_CONFIG["info"])
        return ft.Container(
            content=ft.Row(
                [
                    ft.Icon(config["icon"], color=config["color"], size=24),
                    ft.Column(
                        [
                            ft.Text(title, weight=ft.FontWeight.W_600, size=14),
                            ft.Text(subtitle, size=12, color=Colors.NEUTRAL),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    ft.TextButton(
                        content=ft.Text(action_text, size=12, color=Colors.PRIMARY),
                        on_click=on_click,
                    )
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding(left=16, top=12, right=16, bottom=12),
            bgcolor="#FFFFFF",
            border_radius=10,
            border=ft.Border(
                left=ft.BorderSide(1, Colors.BORDER),
                right=ft.BorderSide(1, Colors.BORDER),
                top=ft.BorderSide(1, Colors.BORDER),
                bottom=ft.BorderSide(1, Colors.BORDER),
            ),
        )

    def render_alerts() -> None:
        # Update KPIs
        kpi_concessions.content.controls[2].value = str(len(alerts_data["concessions_expiring"]))
        kpi_reservations.content.controls[2].value = str(len(alerts_data["pending_reservations"]))
        kpi_payments.content.controls[2].value = str(len(alerts_data["overdue_payments"]))

        # Render Concessions
        concessions_list.controls.clear()
        if not alerts_data["concessions_expiring"]:
            concessions_list.controls.append(ft.Text("Aucune concession n'expire dans les 30 prochains jours.", color=Colors.NEUTRAL, italic=True))
        else:
            for c in alerts_data["concessions_expiring"]:
                severity = "critical" if c.get("days_left", 99) <= 7 else "warning"
                concessions_list.controls.append(build_alert_item(
                    title=f"Caveau {c.get('grave_code')} - {c.get('client')}",
                    subtitle=f"Expire dans {c.get('days_left')} jours (Le {c.get('date_fin')})",
                    severity=severity,
                    action_text="Voir",
                    on_click=lambda _: page.go("/concessions")
                ))

        # Render Reservations
        reservations_list.controls.clear()
        if not alerts_data["pending_reservations"]:
            reservations_list.controls.append(ft.Text("Aucune réservation en attente de validation.", color=Colors.NEUTRAL, italic=True))
        else:
            for r in alerts_data["pending_reservations"]:
                reservations_list.controls.append(build_alert_item(
                    title=f"Demande de {r.get('username')} - Caveau {r.get('grave_code')}",
                    subtitle=f"Reçue le {r.get('created_at')}",
                    severity="warning",
                    action_text="Valider",
                    on_click=lambda _: page.go("/reservations")
                ))

        # Render Payments
        payments_list.controls.clear()
        if not alerts_data["overdue_payments"]:
            payments_list.controls.append(ft.Text("Aucun paiement en retard.", color=Colors.NEUTRAL, italic=True))
        else:
            for p in alerts_data["overdue_payments"]:
                payments_list.controls.append(build_alert_item(
                    title=f"Facture {p.get('facture')} - {p.get('client')}",
                    subtitle=f"Retard de {p.get('days_overdue')} j. - Montant: {float(p.get('amount', 0)):,.0f} FCFA".replace(",", " "),
                    severity="critical",
                    action_text="Relancer",
                    on_click=lambda _: page.go("/finance")
                ))

        page.update()

    load_alerts()

    device = get_device_type(page.window.width or 1200)

    content_card = ft.Container(
        content=ft.Column(
            [
                ft.Text("Centre de Notifications", style=heading_style(size=22)),
                ft.Container(height=10),
                ft.Text("Vue d'ensemble des actions urgentes nécessitant votre attention.", size=14, color=Colors.NEUTRAL),
                ft.Container(height=20),
                kpi_row,
                ft.Container(height=30),

                ft.Text("⚠️ Concessions expirant bientôt", style=heading_style(size=16)),
                ft.Container(height=10),
                concessions_list,

                ft.Container(height=20),
                ft.Text("⏳ Réservations en attente", style=heading_style(size=16)),
                ft.Container(height=10),
                reservations_list,

                ft.Container(height=20),
                ft.Text("💰 Paiements en retard", style=heading_style(size=16)),
                ft.Container(height=10),
                payments_list,

                ft.Container(height=20),
                loading,
                error_text,
            ],
            spacing=0,
            # ✅ CORRECTIF SCROLL : c'était exactement le même bug que sur
            # /finance et /graves. Un Container "expand=True" imbriqué dans
            # une View(scroll=AUTO) se retrouve avec une hauteur non bornée
            # -> il s'écrase à 0px, et tout ce qu'on met dedans (vos alertes)
            # est bien construit mais invisible à l'écran, sans erreur.
            # Ici, la View ne scrolle plus (cadre fixe), et c'est cette
            # unique Column, bornée par expand=True, qui porte tout le
            # défilement de la page.
            expand=True,
            scroll=ft.ScrollMode.ALWAYS,
        ),
        padding=24,
        bgcolor="#FFFFFF",
        border_radius=16,
        expand=True,
        shadow=ft.BoxShadow(spread_radius=0, blur_radius=16, color="#0000000F"),
    )

    return ft.View(
        route="/alerts",
        controls=[content_card],
        bgcolor=Colors.BACKGROUND,
        padding=16 if device == "mobile" else 32,
        # ✅ Pas de scroll ici : la View est le cadre fixe, pas une deuxième
        # zone de scroll (cf. commentaire ci-dessus).
    )