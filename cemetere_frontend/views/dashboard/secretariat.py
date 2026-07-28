"""
views/dashboard/secretariat.py — Tableau de bord du Secrétariat.
Compatible Flet 0.86.3
CORRECTIONS : 
- Ajout des listes de lecture seule pour Inhumations et Exhumations.
- Responsivité stricte (page.window.width, ResponsiveRow).
- Aucun bouton d'action (confirmer/demander) pour ces modules.
"""
from __future__ import annotations
import flet as ft
from datetime import datetime
from core.auth import AuthState, Role
from core.api import ApiError, Endpoints
from core.theme import Colors, get_device_type, heading_style

PALETTE = {"green": "#496042", "blue": "#2E7D9A", "orange": "#F9A825", "red": "#C62828", "grey": "#8B8B8B", "purple": "#7E57C2"}

BUTTON_HEIGHT = 46
BUTTON_RADIUS = 10

KPI_CONFIG = [
    {"key": "today_reservations", "label": "Réservations aujourd'hui", "icon": ft.Icons.EVENT, "color": PALETTE["green"]},
    {"key": "pending_reservations", "label": "À valider", "icon": ft.Icons.EVENT_AVAILABLE, "color": PALETTE["orange"]},
    {"key": "today_inhumations", "label": "Inhumations du jour", "icon": ft.Icons.HISTORY, "color": PALETTE["blue"]},
    {"key": "unpaid_invoices", "label": "Factures impayées", "icon": ft.Icons.RECEIPT_LONG, "color": PALETTE["red"]},
    {"key": "expiring_concessions", "label": "Concessions < 30j", "icon": ft.Icons.HOURGLASS_TOP, "color": PALETTE["purple"]},
    {"key": "monthly_revenue", "label": "Recettes du mois", "icon": ft.Icons.ACCOUNT_BALANCE_WALLET, "color": PALETTE["green"], "suffix": " FCFA"},
]

QUICK_ACTIONS = [
    {"label": "Nouvel utilisateur", "icon": ft.Icons.PERSON_ADD, "route": "/users/nouveau", "color": PALETTE["blue"]},
    {"label": "Concessions à créer", "icon": ft.Icons.PENDING_ACTIONS, "route": "/concessions/ready", "color": PALETTE["green"]},
    {"label": "Encaisser Paiement", "icon": ft.Icons.PAYMENTS, "route": "/finance", "color": PALETTE["orange"]},
    {"label": "Envoyer Relances", "icon": ft.Icons.EMAIL, "route": "/concessions", "color": PALETTE["red"]},
]


def _is_today(date_str: str | None) -> bool:
    if not date_str: return False
    try: return str(date_str)[:10] == datetime.now().strftime("%Y-%m-%d")
    except Exception: return False


def _current_month_revenue(monthly_revenue: list[dict]) -> float:
    current_month = datetime.now().strftime("%Y-%m")
    for entry in monthly_revenue:
        if str(entry.get("month", ""))[:7] == current_month:
            return float(entry.get("total", entry.get("amount", 0)))
    return 0.0


def build_secretariat_dashboard_view(page: ft.Page, auth: AuthState) -> ft.View:
    stats = {}
    loading = ft.ProgressRing(visible=True, width=40, height=40)
    error_text = ft.Text("", color=Colors.ERROR, size=13, visible=False)

    kpi_row = ft.ResponsiveRow(spacing=12, run_spacing=12)
    actions_row = ft.Row(spacing=12, wrap=True)
    
    pending_res_list = ft.Column(spacing=8)
    ready_concessions_list = ft.Column(spacing=8)
    expiring_list = ft.Column(spacing=8)
    
    # ✅ NOUVEAU : Listes en lecture seule pour le secrétariat
    inh_list_view = ft.Column(spacing=4)
    exh_list_view = ft.Column(spacing=4)

    revenue_bars_row = ft.Row(spacing=8, alignment=ft.MainAxisAlignment.SPACE_AROUND, vertical_alignment=ft.CrossAxisAlignment.END)
    concession_status_row = ft.Row(spacing=15, vertical_alignment=ft.CrossAxisAlignment.CENTER)

    def load_data() -> None:
        loading.visible, error_text.visible = True, False
        page.update()

        errors = []
        pending_list, ready_list, expiring_list_data = [], [], []
        inh_data, exh_data = [], []
        unpaid_count = today_res_count = today_inh_count = 0
        concession_stats = {"actives": 0, "expired": 0, "resiliees": 0}

        try:
            data = auth.api.get("/reports/dashboard")
            if isinstance(data, dict): stats.update(data)
        except Exception as exc: errors.append(f"Stats: {exc}")

        try:
            pending = auth.api.get(Endpoints.RESERVATIONS_LIST, params={"status": "pending"})
            pending_list = (pending if isinstance(pending, list) else pending.get("results", []))[:5]
            all_res = auth.api.get(Endpoints.RESERVATIONS_LIST)
            all_res_list = all_res if isinstance(all_res, list) else all_res.get("results", [])
            today_res_count = sum(1 for r in all_res_list if _is_today(r.get("reservation_date")))
        except Exception as exc: errors.append(f"Réservations: {exc}")

        try:
            ready_data = auth.api.get(Endpoints.CONCESSIONS_READY)
            ready_list = (ready_data if isinstance(ready_data, list) else ready_data.get("results", []))[:5]
            
            expiring = auth.api.get("/cemetery/concessions/expiring", params={"days": 30})
            expiring_list_data = (expiring if isinstance(expiring, list) else expiring.get("results", []))[:5]
            
            c_stats = auth.api.get("/cemetery/concessions/stats")
            if isinstance(c_stats, dict): concession_stats.update(c_stats)
        except Exception as exc: errors.append(f"Concessions: {exc}")

        try:
            factures = auth.api.get("/finance/factures")
            factures_list = factures if isinstance(factures, list) else factures.get("results", [])
            unpaid_count = sum(1 for f in factures_list if f.get("statut") in ("en_attente", "partielle"))
            
            # ✅ Récupération des listes pour affichage en lecture seule
            inhumations = auth.api.get("/cemetery/inhumations")
            inh_data = inhumations if isinstance(inhumations, list) else inhumations.get("results", [])
            today_inh_count = sum(1 for i in inh_data if _is_today(i.get("date_inhumation")))
            
            exhumations = auth.api.get("/cemetery/exhumations")
            exh_data = exhumations if isinstance(exhumations, list) else exhumations.get("results", [])
        except Exception as exc: errors.append(f"Finance/Opérations: {exc}")

        if errors:
            error_text.value = " • ".join(errors)
            error_text.visible = True
        else:
            error_text.visible = False

        render_kpis(today_res_count, len(pending_list), today_inh_count, unpaid_count, len(expiring_list_data), _current_month_revenue(stats.get("monthly_revenue", [])))
        render_quick_actions()
        render_pending(pending_list)
        render_ready_concessions(ready_list)
        render_expiring(expiring_list_data)
        render_field_operations(inh_data, exh_data) # ✅ NOUVEAU
        render_revenue_chart(stats.get("monthly_revenue", []))
        render_concession_chart(concession_stats)

        loading.visible = False
        page.update()

    def render_kpis(today_res, pending_count, today_inh, unpaid_count, expiring_count, revenue) -> None:
        kpi_row.controls.clear()
        values = {
            "today_reservations": today_res, "pending_reservations": pending_count,
            "today_inhumations": today_inh, "unpaid_invoices": unpaid_count,
            "expiring_concessions": expiring_count, "monthly_revenue": revenue,
        }
        for cfg in KPI_CONFIG:
            val = values.get(cfg["key"], 0)
            display = f"{val:,.0f}".replace(",", " ") + cfg.get("suffix", "")
            kpi_row.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Container(content=ft.Icon(cfg["icon"], color=Colors.TEXT_ON_DARK, size=22), bgcolor=cfg["color"], padding=10, border_radius=12),
                        ft.Column([ft.Text(cfg["label"], size=11, color=Colors.NEUTRAL), ft.Text(display, size=18, weight=ft.FontWeight.BOLD, color=Colors.TEXT)], spacing=2, expand=True),
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=16, bgcolor="#FFFFFF", border_radius=14, border=ft.Border(top=ft.BorderSide(3, cfg["color"])),
                    shadow=ft.BoxShadow(spread_radius=0, blur_radius=10, color="#00000014"),
                    col={"xs": 12, "sm": 12, "md": 6, "lg": 4},
                )
            )

    def render_quick_actions() -> None:
        actions_row.controls.clear()
        for act in QUICK_ACTIONS:
            actions_row.controls.append(
                ft.ElevatedButton(
                    content=ft.Row(
                        [ft.Icon(act["icon"], color=Colors.TEXT_ON_DARK, size=19), ft.Text(act["label"], color=Colors.TEXT_ON_DARK, weight=ft.FontWeight.W_600, size=13)],
                        spacing=8, alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    style=ft.ButtonStyle(
                        bgcolor=act["color"], shape=ft.RoundedRectangleBorder(radius=BUTTON_RADIUS),
                        elevation={"": 0, "hovered": 3}, padding=ft.Padding(left=18, right=18, top=0, bottom=0),
                    ),
                    height=BUTTON_HEIGHT,
                    on_click=lambda _, r=act["route"]: page.go(r),
                )
            )

    def render_pending(items) -> None:
        pending_res_list.controls.clear()
        if not items:
            pending_res_list.controls.append(ft.Text("Aucune réservation en attente.", color=Colors.NEUTRAL, italic=True))
            return
        for item in items:
            pending_res_list.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.EVENT_NOTE, color=PALETTE["orange"], size=20),
                        ft.Column([ft.Text(f"Caveau {item.get('grave_code', '?')}", size=13, weight=ft.FontWeight.W_600), ft.Text(f"Client : {item.get('client_username', 'N/A')}", size=11, color=Colors.NEUTRAL)], spacing=2, expand=True),
                        ft.TextButton("Voir", on_click=lambda _: page.go("/reservations")),
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=10, bgcolor="#FFFFFF", border_radius=8, border=ft.Border(left=ft.BorderSide(3, PALETTE["orange"])),
                )
            )

    def render_ready_concessions(items) -> None:
        ready_concessions_list.controls.clear()
        if not items:
            ready_concessions_list.controls.append(ft.Text("Aucun dossier prêt.", color=Colors.NEUTRAL, italic=True))
            return
        for item in items:
            ready_concessions_list.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.PENDING_ACTIONS, color=PALETTE["green"], size=20),
                        ft.Column([ft.Text(f"Caveau {item.get('grave_code', '?')}", size=13, weight=ft.FontWeight.W_600), ft.Text(f"Client : {item.get('client_username', 'N/A')}", size=11, color=Colors.NEUTRAL)], spacing=2, expand=True),
                        ft.TextButton("Créer", on_click=lambda _, rid=item.get('reservation_id'): page.go(f"/concessions/nouvelle?reservation_id={rid}")),
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=10, bgcolor="#FFFFFF", border_radius=8, border=ft.Border(left=ft.BorderSide(3, PALETTE["green"])),
                )
            )

    def render_expiring(items) -> None:
        expiring_list.controls.clear()
        if not items:
            expiring_list.controls.append(ft.Text("Aucune concession expirant bientôt.", color=Colors.NEUTRAL, italic=True))
            return
        for item in items:
            user_name = item.get("user", {}).get("username", "N/A") if isinstance(item.get("user"), dict) else "N/A"
            expiring_list.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.HOURGLASS_TOP, color=PALETTE["purple"], size=20),
                        ft.Column([ft.Text(f"Caveau {item.get('grave_code', '?')}", size=13, weight=ft.FontWeight.W_600), ft.Text(f"Client : {user_name} • Fin : {item.get('date_fin', '?')}", size=11, color=Colors.NEUTRAL)], spacing=2, expand=True),
                        ft.TextButton("Relancer", on_click=lambda _: page.go("/concessions")),
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=10, bgcolor="#FFFFFF", border_radius=8, border=ft.Border(left=ft.BorderSide(3, PALETTE["purple"])),
                )
            )

    # ✅ NOUVEAU : Rendu des listes en lecture seule (pas de boutons d'action)
    def render_field_operations(inh_items, exh_items) -> None:
        inh_list_view.controls.clear()
        exh_list_view.controls.clear()
        
        # Inhumations (Lecture seule)
        if not inh_items:
            inh_list_view.controls.append(ft.Text("Aucune inhumation enregistrée.", color=Colors.NEUTRAL, italic=True, size=12))
        else:
            for item in inh_items[:5]: # Top 5
                inh_list_view.controls.append(
                    ft.ListTile(
                        title=ft.Text(f"Caveau {item.get('grave_code', '?')} - {item.get('defunt_nom', '')}", size=13, weight=ft.FontWeight.W_600),
                        subtitle=ft.Text(f"Date : {str(item.get('date_inhumation', ''))[:10]}", size=11, color=Colors.NEUTRAL),
                        leading=ft.Icon(ft.Icons.HISTORY, color=PALETTE["blue"], size=20),
                        dense=True,
                    )
                )

        # Exhumations (Lecture seule)
        if not exh_items:
            exh_list_view.controls.append(ft.Text("Aucune exhumation en cours.", color=Colors.NEUTRAL, italic=True, size=12))
        else:
            for item in exh_items[:5]: # Top 5
                inh_data = item.get("inhumation", {}) if isinstance(item.get("inhumation"), dict) else {}
                defunt = item.get("defunt_nom") or inh_data.get("defunt_nom", "N/A")
                status = item.get("status", "N/A")
                
                exh_list_view.controls.append(
                    ft.ListTile(
                        title=ft.Text(f"Caveau {item.get('grave_code', '?')} - {defunt}", size=13, weight=ft.FontWeight.W_600),
                        subtitle=ft.Text(f"Statut : {status}", size=11, color=Colors.NEUTRAL),
                        leading=ft.Icon(ft.Icons.UNARCHIVE, color=PALETTE["orange"], size=20),
                        dense=True,
                    )
                )

    def render_revenue_chart(monthly) -> None:
        revenue_bars_row.controls.clear()
        if not monthly:
            revenue_bars_row.controls.append(ft.Text("Aucune donnée.", color=Colors.NEUTRAL, italic=True, size=12))
            return
        values = [m.get("total", m.get("amount", 0)) for m in monthly]
        max_val = max(values) if any(values) else 1
        for entry in monthly:
            value = entry.get("total", entry.get("amount", 0))
            bar_height = max(int(value / max_val * 120), 4)
            month_lbl = str(entry.get("month", ""))[5:7]
            revenue_bars_row.controls.append(
                ft.Column([
                    ft.Text(f"{int(value)//1000}k", size=9, color=Colors.NEUTRAL),
                    ft.Container(width=24, height=bar_height, bgcolor=PALETTE["green"], border_radius=ft.BorderRadius(top_left=4, top_right=4, bottom_left=0, bottom_right=0)),
                    ft.Text(month_lbl, size=10, color=Colors.TEXT, weight=ft.FontWeight.W_600),
                ], spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            )

    def render_concession_chart(c_stats) -> None:
        concession_status_row.controls.clear()
        total = c_stats.get("actives", 0) + c_stats.get("expired", 0) + c_stats.get("resiliees", 0)
        if total == 0:
            concession_status_row.controls.append(ft.Text("Aucune concession.", color=Colors.NEUTRAL, italic=True, size=12))
            return
            
        segments = [
            ("Actives", c_stats.get("actives", 0), PALETTE["green"]),
            ("Expirées", c_stats.get("expired", 0), PALETTE["red"]),
            ("Résiliées", c_stats.get("resiliees", 0), PALETTE["grey"]),
        ]
        
        for label, value, color in segments:
            pct = int((value / total * 100)) if total else 0
            concession_status_row.controls.append(
                ft.Column([
                    ft.Row([ft.Container(width=12, height=12, bgcolor=color, border_radius=6), ft.Text(label, size=12)], spacing=6),
                    ft.Text(f"{value} ({pct}%)", size=12, weight=ft.FontWeight.W_600),
                    ft.Container(bgcolor=color, border_radius=4, height=8, width=100 * (pct/100) if pct > 0 else 2),
                ], spacing=4, horizontal_alignment=ft.CrossAxisAlignment.START)
            )

    load_data()
    
    # ✅ CORRECTION CRITIQUE : Détection de largeur robuste pour Flet 0.86.3
    width = getattr(page, 'window', page).width if hasattr(page, 'window') else (getattr(page, 'width', 1200) or 1200)
    device = get_device_type(width)

    return ft.View(
        route="/dashboard/secretariat",
        controls=[
            ft.Column([
                ft.Row([
                    ft.Text("Tableau de bord Secrétariat", style=heading_style(size=22)),
                    ft.Container(expand=True),
                    ft.ElevatedButton(
                        content=ft.Row([ft.Icon(ft.Icons.ADD, size=18, color=Colors.TEXT_ON_DARK), ft.Text("Nouvelle réservation", color=Colors.TEXT_ON_DARK, size=13, weight=ft.FontWeight.W_600)], spacing=8),
                        style=ft.ButtonStyle(bgcolor=Colors.PRIMARY, shape=ft.RoundedRectangleBorder(radius=BUTTON_RADIUS), elevation={"": 0, "hovered": 3}, padding=ft.Padding(left=18, right=18, top=0, bottom=0)),
                        height=BUTTON_HEIGHT,
                        on_click=lambda _: page.go("/reservations/nouvelle"),
                    ),
                ]),
                ft.Container(height=16),
                loading, error_text, kpi_row, ft.Container(height=16),
                
                ft.Text("Actions Rapides", style=heading_style(size=16)),
                ft.Container(height=8),
                actions_row, ft.Container(height=20),
                
                ft.ResponsiveRow([
                    ft.Container(content=ft.Column([ft.Text("Réservations à valider", style=heading_style(size=16)), ft.Container(height=10), pending_res_list], spacing=0), padding=20, bgcolor="#FFFFFF", border_radius=14, shadow=ft.BoxShadow(spread_radius=0, blur_radius=10, color="#00000014"), col={"xs": 12, "sm": 12, "md": 4}),
                    ft.Container(content=ft.Column([ft.Text("Concessions à créer", style=heading_style(size=16)), ft.Container(height=10), ready_concessions_list], spacing=0), padding=20, bgcolor="#FFFFFF", border_radius=14, shadow=ft.BoxShadow(spread_radius=0, blur_radius=10, color="#00000014"), col={"xs": 12, "sm": 12, "md": 4}),
                    ft.Container(content=ft.Column([ft.Text("Concessions à relancer", style=heading_style(size=16)), ft.Container(height=10), expiring_list], spacing=0), padding=20, bgcolor="#FFFFFF", border_radius=14, shadow=ft.BoxShadow(spread_radius=0, blur_radius=10, color="#00000014"), col={"xs": 12, "sm": 12, "md": 4}),
                ], spacing=16, run_spacing=16),
                ft.Container(height=20),

                # ✅ NOUVEAU : Section Opérations Terrain (Lecture seule pour le secrétariat)
                ft.Text("Suivi des opérations terrain (Lecture seule)", style=heading_style(size=16)),
                ft.Container(height=8),
                ft.ResponsiveRow([
                    ft.Container(
                        content=ft.Column([ft.Text("Dernières inhumations", size=14, weight=ft.FontWeight.W_600), ft.Container(height=8), inh_list_view], spacing=0),
                        padding=16, bgcolor="#FFFFFF", border_radius=14, shadow=ft.BoxShadow(spread_radius=0, blur_radius=10, color="#00000014"), col={"xs": 12, "sm": 12, "md": 6}
                    ),
                    ft.Container(
                        content=ft.Column([ft.Text("Exhumations en cours", size=14, weight=ft.FontWeight.W_600), ft.Container(height=8), exh_list_view], spacing=0),
                        padding=16, bgcolor="#FFFFFF", border_radius=14, shadow=ft.BoxShadow(spread_radius=0, blur_radius=10, color="#00000014"), col={"xs": 12, "sm": 12, "md": 6}
                    ),
                ], spacing=16, run_spacing=16),
                ft.Container(height=20),
                
                ft.ResponsiveRow([
                    ft.Container(
                        content=ft.Column([ft.Text("Évolution des revenus", style=heading_style(size=16)), ft.Container(height=10), ft.Container(content=revenue_bars_row, height=160, alignment=ft.Alignment(0, 1))], spacing=0),
                        padding=20, bgcolor="#FFFFFF", border_radius=14, shadow=ft.BoxShadow(spread_radius=0, blur_radius=10, color="#00000014"), col={"xs": 12, "sm": 12, "md": 7},
                    ),
                    ft.Container(
                        content=ft.Column([ft.Text("État du portefeuille concessions", style=heading_style(size=16)), ft.Container(height=10), ft.Container(content=concession_status_row, height=160, alignment=ft.Alignment(0, 0.5))], spacing=0),
                        padding=20, bgcolor="#FFFFFF", border_radius=14, shadow=ft.BoxShadow(spread_radius=0, blur_radius=10, color="#00000014"), col={"xs": 12, "sm": 12, "md": 5},
                    ),
                ], spacing=16, run_spacing=16),
                ft.Container(height=20),
            ], expand=True),
        ],
        bgcolor=Colors.BACKGROUND,
        padding=24 if device != "mobile" else 16,
    )