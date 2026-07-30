"""
views/dashboard/admin.py — Tableau de bord administratif.
Compatible Flet 0.86.3
CORRECTIONS : 
- Détection de largeur de fenêtre sécurisée.
- Ajout du bouton "Générer la grille" à côté de la configuration.
- Gestion propre des erreurs d'alertes.
"""
from __future__ import annotations

import flet as ft
from datetime import datetime

from core.auth import AuthState, Role
from core.api import ApiError, Endpoints
from core.theme import Colors, get_device_type, heading_style

PALETTE = {
    "green": "#496042",
    "blue": "#2E7D9A",
    "purple": "#7E57C2",
    "orange": "#F9A825",
    "red": "#C62828",
    "brown": "#8B6B3F",
    "grey": "#8B8B8B",
}

KPI_CONFIG = [
    {"key": "total_graves", "label": "Sépultures (total)", "icon": ft.Icons.LOCATION_ON, "color": PALETTE["purple"]},
    {"key": "free", "label": "Disponibles", "icon": ft.Icons.CHECK_CIRCLE, "color": PALETTE["green"]},
    {"key": "reserved", "label": "Réservées", "icon": ft.Icons.EVENT_AVAILABLE, "color": PALETTE["orange"]},
    {"key": "occupied", "label": "Occupées", "icon": ft.Icons.DESCRIPTION, "color": PALETTE["red"]},
    {"key": "unavailable", "label": "Non exploitables", "icon": ft.Icons.BLOCK, "color": PALETTE["grey"]},
    {"key": "occupation_rate", "label": "Taux d'occupation", "icon": ft.Icons.PIE_CHART, "color": PALETTE["blue"], "suffix": "%"},
    {"key": "total_revenue", "label": "Revenus totaux", "icon": ft.Icons.ACCOUNT_BALANCE_WALLET, "color": PALETTE["green"], "suffix": " FCFA"},
]

def build_admin_dashboard_view(page: ft.Page, auth: AuthState) -> ft.View:
    stats = {}
    activities = []
    alerts = []
    ready_concessions_count = 0

    loading = ft.ProgressRing(visible=True, width=40, height=40)
    error_text = ft.Text("", color=Colors.ERROR, size=13, visible=False)
    kpi_row = ft.ResponsiveRow(spacing=12, run_spacing=12)

    occupancy_ring = ft.ProgressRing(
        value=0.0, width=120, height=120, stroke_width=12, color=PALETTE["green"], bgcolor="#E5E2D9"
    )
    occupancy_ring_label = ft.Text("0%", size=22, weight=ft.FontWeight.BOLD, color=Colors.TEXT)
    occupancy_legend = ft.Column(spacing=8)

    activities_list = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO)
    alerts_list = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO)

    revenue_bars_row = ft.Row(
        spacing=12,
        alignment=ft.MainAxisAlignment.SPACE_AROUND,
        vertical_alignment=ft.CrossAxisAlignment.END,
    )

    def get_french_date_time() -> str:
        now = datetime.now()
        jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
        mois = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        return f"{jours[now.weekday()]} {now.day} {mois[now.month - 1]} {now.year} à {now.strftime('%H:%M')}"

    def get_unread_count() -> int:
        try:
            data = auth.api.get("/notifications/notifications/unread-count")
            if isinstance(data, dict):
                return data.get("non_lues", 0)
        except Exception:
            pass
        return 0

    def on_bell_click(_: ft.ControlEvent) -> None:
        page.go("/notifications")

    def build_header(unread_count: int) -> ft.Control:
        return ft.Container(
            content=ft.Row(
                [
                    ft.Row([
                        ft.Icon(ft.Icons.PARK, color=Colors.PRIMARY, size=24),
                        ft.Text("Cimetière Connect", size=18, weight=ft.FontWeight.W_700, color=Colors.PRIMARY),
                    ], spacing=8),
                    ft.Container(expand=True),
                    ft.Row([
                        ft.Stack(
                            controls=[
                                ft.IconButton(
                                    icon=ft.Icons.NOTIFICATIONS_ACTIVE if unread_count > 0 else ft.Icons.NOTIFICATIONS,
                                    icon_color=Colors.NEUTRAL,
                                    icon_size=22,
                                    tooltip="Notifications",
                                    on_click=on_bell_click,
                                ),
                                ft.Container(
                                    content=ft.Text(str(unread_count), size=9, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
                                    bgcolor=ft.Colors.RED_700,
                                    border_radius=8,
                                    padding=ft.Padding(left=4, top=1, right=4, bottom=1),
                                    top=2,
                                    right=2,
                                ) if unread_count > 0 else ft.Container(),
                            ]
                        ),
                        ft.Container(width=16),
                        ft.Icon(ft.Icons.CALENDAR_MONTH, color=Colors.NEUTRAL, size=20),
                        ft.Text(get_french_date_time(), size=13, color=Colors.NEUTRAL),
                        ft.Container(width=16),
                        ft.CircleAvatar(
                            content=ft.Text(
                                (auth.username or "?")[0].upper(),
                                color=Colors.TEXT_ON_DARK,
                                weight=ft.FontWeight.BOLD,
                            ),
                            bgcolor=Colors.PRIMARY,
                            radius=18,
                        ),
                        ft.Column([
                            ft.Text(auth.username or "Utilisateur", size=13, weight=ft.FontWeight.W_600),
                            ft.Text(auth.role.value if auth.role else "", size=11, color=Colors.NEUTRAL),
                        ], spacing=0),
                    ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding(left=20, top=12, right=20, bottom=12),
            bgcolor="#FFFFFF",
            border=ft.Border(bottom=ft.BorderSide(1, Colors.BORDER)),
        )

    def load_dashboard() -> None:
        nonlocal ready_concessions_count
        loading.visible = True
        error_text.visible = False
        page.update()

        try:
            data = auth.api.get("/reports/dashboard")
            if isinstance(data, dict):
                stats.update(data)
        except ApiError as exc:
            error_text.value = f"Erreur de chargement : {exc.message}"
            error_text.visible = True
            stats.update({
                "total_graves": 120, "free": 45, "reserved": 25,
                "occupied": 40, "unavailable": 10, "occupation_rate": 68,
                "total_revenue": 4500000,
                "monthly_revenue": [
                    {"month": "Jan", "amount": 800000},
                    {"month": "Fév", "amount": 950000},
                    {"month": "Mar", "amount": 1100000}
                ]
            })
        except Exception:
            error_text.value = "Impossible de contacter le serveur."
            error_text.visible = True

        alerts.clear()
        try:
            pending = auth.api.get(Endpoints.RESERVATIONS_LIST, params={"status": "pending"})
            pending_list = pending if isinstance(pending, list) else pending.get("results", [])
            if pending_list:
                alerts.append({
                    "type": "warning",
                    "title": "Réservations en attente de validation",
                    "desc": f"{len(pending_list)} réservation(s)",
                    "target": "/reservations",
                })

            ready_data = auth.api.get(Endpoints.CONCESSIONS_READY)
            if isinstance(ready_data, list):
                ready_concessions_count = len(ready_data)
                if ready_concessions_count > 0:
                    alerts.append({
                        "type": "info",
                        "title": f"{ready_concessions_count} dossier(s) prêt(s) pour concession",
                        "desc": "Factures payées, en attente de validation",
                        "target": "/concessions/ready",
                    })
        except ApiError as exc:
            msg = f"Alertes : {exc.message}"
            error_text.value = (error_text.value + " • " + msg) if error_text.value else msg
            error_text.visible = True
        except Exception as exc:
            msg = f"Alertes : erreur inattendue ({exc})"
            error_text.value = (error_text.value + " • " + msg) if error_text.value else msg
            error_text.visible = True

        activities.clear()
        loading.visible = False
        render_kpis()
        render_occupancy()
        render_activities()
        render_alerts()
        render_revenue_bars()
        page.update()

    def render_kpis() -> None:
        kpi_row.controls.clear()
        for cfg in KPI_CONFIG:
            value = stats.get(cfg["key"], 0)
            display = f"{value:,}".replace(",", " ") + cfg.get("suffix", "")
            card = ft.Container(
                content=ft.Row(
                    [
                        ft.Container(
                            content=ft.Icon(cfg["icon"], color=Colors.TEXT_ON_DARK, size=24),
                            bgcolor=cfg["color"],
                            padding=10,
                            border_radius=10,
                        ),
                        ft.Column(
                            [
                                ft.Text(cfg["label"], size=11, color=Colors.NEUTRAL),
                                ft.Text(display, size=18, weight=ft.FontWeight.BOLD, color=Colors.TEXT),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=14,
                bgcolor="#FFFFFF",
                border_radius=12,
                border=ft.Border(top=ft.BorderSide(3, cfg["color"])),
                shadow=ft.BoxShadow(spread_radius=0, blur_radius=8, color="#00000012"),
                col={"sm": 12, "md": 6, "lg": 4, "xl": 2},
            )
            kpi_row.controls.append(card)

    def render_occupancy() -> None:
        total = stats.get("total_graves", 1) or 1
        rate = stats.get("occupation_rate", 0)
        occupancy_ring.value = min(rate / 100, 1.0)
        occupancy_ring_label.value = f"{rate}%"

        segments = [
            ("Disponible", stats.get("free", 0), PALETTE["green"]),
            ("Réservé", stats.get("reserved", 0), PALETTE["orange"]),
            ("Occupé", stats.get("occupied", 0), PALETTE["red"]),
            ("Non exploitable", stats.get("unavailable", 0), PALETTE["grey"]),
        ]

        occupancy_legend.controls.clear()
        for label, value, color in segments:
            pct = int((value / total * 100)) if total else 0
            occupancy_legend.controls.append(
                ft.Column([
                    ft.Row([
                        ft.Row([ft.Container(width=10, height=10, bgcolor=color, border_radius=5), ft.Text(label, size=12)], spacing=6),
                        ft.Text(f"{value} ({pct}%)", size=12, weight=ft.FontWeight.W_600),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Row([
                        ft.Container(bgcolor=color, border_radius=3, height=6, expand=max(pct, 1)),
                        ft.Container(bgcolor="#E5E2D9", border_radius=3, height=6, expand=max(100 - pct, 1)),
                    ], spacing=0)
                ], spacing=4)
            )

    def render_activities() -> None:
        activities_list.controls.clear()
        activities_list.controls.append(ft.Text("Aucune activité récente.", color=Colors.NEUTRAL, italic=True))

    def render_alerts() -> None:
        alerts_list.controls.clear()
        if not alerts:
            alerts_list.controls.append(ft.Text("Aucune alerte active.", color=Colors.NEUTRAL, italic=True))
            return
        for a in alerts:
            color = PALETTE["orange"] if a.get("type") == "warning" else PALETTE["blue"]
            alerts_list.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.NOTIFICATIONS_ACTIVE, color=color, size=20),
                        ft.Column([
                            ft.Text(a.get("title", ""), size=13, weight=ft.FontWeight.W_600),
                            ft.Text(a.get("desc", ""), size=11, color=Colors.NEUTRAL),
                        ], spacing=2, expand=True),
                        ft.TextButton(
                            content=ft.Text("Voir", size=11, color=Colors.PRIMARY),
                            on_click=lambda _, t=a.get("target", "/dashboard/admin"): page.go(t),
                        ),
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=10,
                    bgcolor="#FFFFFF",
                    border_radius=8,
                    border=ft.Border(left=ft.BorderSide(3, color)),
                )
            )

    def render_revenue_bars() -> None:
        monthly = stats.get("monthly_revenue", [])
        revenue_bars_row.controls.clear()
        if not monthly:
            revenue_bars_row.controls.append(ft.Text("Aucune donnée de revenus.", color=Colors.NEUTRAL, italic=True))
            return

        values = [m.get("amount", 0) for m in monthly]
        max_val = max(values) if any(values) else 1

        for entry in monthly:
            value = entry.get("amount", 0)
            bar_height = max(int(value / max_val * 140), 4)
            revenue_bars_row.controls.append(
                ft.Column([
                    ft.Text(f"{int(value)//1000}k", size=10, color=Colors.NEUTRAL),
                    ft.Container(
                        width=28,
                        height=bar_height,
                        bgcolor=PALETTE["green"],
                        border_radius=ft.BorderRadius(top_left=4, top_right=4, bottom_left=0, bottom_right=0),
                    ),
                    ft.Text(entry.get("month", ""), size=11, color=Colors.TEXT, weight=ft.FontWeight.W_600),
                ], spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            )

    load_dashboard()
    unread_count = get_unread_count()

    width = getattr(page, 'window', page).width if hasattr(page, 'window') else (getattr(page, 'width', 1200) or 1200)
    device = get_device_type(width)

    line2 = ft.ResponsiveRow(
        controls=[
            ft.Container(
                content=ft.Column([
                    ft.Text("Occupation par statut", style=heading_style(size=16)),
                    ft.Container(height=16),
                    ft.Row([
                        ft.Stack([
                            occupancy_ring,
                            ft.Container(content=occupancy_ring_label, alignment=ft.Alignment(0, 0), width=120, height=120),
                        ], width=120, height=120),
                        ft.Container(content=occupancy_legend, expand=True, padding=ft.Padding.only(left=20)),
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ], spacing=0),
                padding=20,
                bgcolor="#FFFFFF",
                border_radius=12,
                shadow=ft.BoxShadow(spread_radius=0, blur_radius=8, color="#00000012"),
                col={"sm": 12, "md": 7},
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("Carte SIG", style=heading_style(size=16)),
                    ft.Container(height=10),
                    ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.Icons.MAP, size=40, color=Colors.PRIMARY),
                            ft.Text("Aperçu du cimetière", size=12, color=Colors.NEUTRAL),
                            ft.Container(height=10),
                            ft.ElevatedButton(
                                content=ft.Text("Ouvrir la carte", color=Colors.TEXT_ON_DARK),
                                style=ft.ButtonStyle(bgcolor=Colors.PRIMARY),
                                on_click=lambda _: page.go("/carte"),
                            ),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=20,
                        bgcolor="#F5F3EE",
                        border_radius=12,
                        alignment=ft.Alignment(0, 0),
                        expand=True,
                    ),
                ], spacing=0),
                padding=20,
                bgcolor="#FFFFFF",
                border_radius=12,
                shadow=ft.BoxShadow(spread_radius=0, blur_radius=8, color="#00000012"),
                col={"sm": 12, "md": 5},
            ),
        ],
        spacing=16,
        run_spacing=16,
    )

    line3 = ft.ResponsiveRow(
        controls=[
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text("Activités récentes", style=heading_style(size=16)),
                        ft.Container(expand=True),
                        ft.TextButton("Voir tout", on_click=lambda _: page.go("/reports")),
                    ]),
                    ft.Container(height=10),
                    activities_list,
                ], spacing=0),
                padding=20,
                bgcolor="#FFFFFF",
                border_radius=12,
                shadow=ft.BoxShadow(spread_radius=0, blur_radius=8, color="#00000012"),
                height=300,
                col={"sm": 12, "md": 6},
            ),
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text("Alertes & Dossiers prêts", style=heading_style(size=16)),
                        ft.Container(expand=True),
                        ft.TextButton("Voir tout", on_click=lambda _: page.go("/alerts")),
                    ]),
                    ft.Container(height=10),
                    alerts_list,
                ], spacing=0),
                padding=20,
                bgcolor="#FFFFFF",
                border_radius=12,
                shadow=ft.BoxShadow(spread_radius=0, blur_radius=8, color="#00000012"),
                height=300,
                col={"sm": 12, "md": 6},
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("Évolution des revenus", style=heading_style(size=16)),
                    ft.Container(height=10),
                    ft.Container(content=revenue_bars_row, height=180, expand=True),
                ], spacing=0),
                padding=20,
                bgcolor="#FFFFFF",
                border_radius=12,
                shadow=ft.BoxShadow(spread_radius=0, blur_radius=8, color="#00000012"),
                col={"sm": 12, "md": 12},
            ),
        ],
        spacing=16,
        run_spacing=16,
    )

    dashboard_content = ft.Column(
        [
            ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text("Bonjour, " + (auth.username or "Admin") + " 👋", style=heading_style(size=22)),
                            ft.Text("Aperçu général de la gestion du cimetière.", size=14, color=Colors.NEUTRAL),
                        ]
                    ),
                    # ✅ AJOUT DU BOUTON "GÉNÉRER LA GRILLE" ICI
                    ft.Row([
                        ft.ElevatedButton(
                            "⚙️ Configurer le cimetière",
                            icon=ft.Icons.SETTINGS,
                            bgcolor=Colors.PRIMARY,
                            color=Colors.TEXT_ON_DARK,
                            on_click=lambda _: page.go("/cimetiere/setup")
                        ),
                        ft.Container(width=10),
                        ft.ElevatedButton(
                            "🗺️ Générer la grille",
                            icon=ft.Icons.GRID_ON,
                            bgcolor=PALETTE["purple"],
                            color=Colors.TEXT_ON_DARK,
                            on_click=lambda _: page.go("/graves/generate-grid")
                        ),
                    ])
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Container(height=20),
            loading,
            error_text,
            kpi_row,
            ft.Container(height=16),
            line2,
            ft.Container(height=16),
            line3,
            ft.Container(height=20),
        ],
        spacing=0,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    return ft.View(
        route="/dashboard/admin",
        controls=[
            ft.Column(
                [
                    build_header(unread_count),
                    ft.Container(
                        content=dashboard_content,
                        expand=True,
                        padding=24 if device == "desktop" else 16,
                    ),
                ],
                expand=True,
            ),
        ],
        bgcolor=Colors.BACKGROUND,
        padding=0,
    )