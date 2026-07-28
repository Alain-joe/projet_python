"""
views/dashboard/agent.py — Tableau de bord de l'Agent de terrain.
Compatible Flet 0.86.3.
CORRECTION : on_click placé directement sur les ElevatedButton (pas sur le Container).
"""
from __future__ import annotations
import flet as ft
from datetime import datetime
from core.auth import AuthState, Role
from core.api import ApiError, Endpoints
from core.theme import Colors, get_device_type, heading_style

PALETTE = {"blue": "#2E7D9A", "orange": "#F9A825", "grey": "#8B8B8B", "green": "#496042"}


def build_agent_dashboard_view(page: ft.Page, auth: AuthState) -> ft.View:
    loading = ft.ProgressRing(visible=True, width=40, height=40)
    error_text = ft.Text("", color=Colors.ERROR, size=13, visible=False)

    kpi_row = ft.ResponsiveRow(spacing=12, run_spacing=12)
    actions_row = ft.ResponsiveRow(spacing=12, run_spacing=12)
    historique_list = ft.Column(spacing=8)
    search_field = ft.TextField(label="Code du caveau (ex: A-003)", border_radius=8, expand=True)
    search_results = ft.Column(spacing=6)

    def _parse_date(value):
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value)[:10])
        except (ValueError, TypeError):
            return None

    def _is_today(value) -> bool:
        d = _parse_date(value)
        return bool(d and d.date() == datetime.now().date())

    def load_data() -> None:
        loading.visible, error_text.visible = True, False
        page.update()

        errors = []
        inh_list, exh_list = [], []
        stats = {}
        signalements_en_attente = 0

        try:
            stats = auth.api.get("/cemetery/stats/")
        except Exception as exc:
            errors.append(f"Statistiques caveaux : {exc}")

        try:
            inhumations = auth.api.get("/cemetery/inhumations")
            inh_list = inhumations if isinstance(inhumations, list) else inhumations.get("results", [])
        except Exception as exc:
            errors.append(f"Inhumations : {exc}")

        try:
            exhumations = auth.api.get("/cemetery/exhumations", params={"status": "approved"})
            exh_list = exhumations if isinstance(exhumations, list) else exhumations.get("results", [])
        except Exception as exc:
            errors.append(f"Exhumations : {exc}")
            
        try:
            sigs = auth.api.get_signalements(statut="en_attente")
            sig_list = sigs if isinstance(sigs, list) else sigs.get("results", [])
            signalements_en_attente = len(sig_list)
        except Exception as exc:
            errors.append(f"Signalements : {exc}")

        if errors:
            error_text.value = " • ".join(errors)
            error_text.visible = True
        else:
            error_text.visible = False

        today_inh_count = sum(1 for i in inh_list if _is_today(i.get("date_inhumation")))

        render_kpis(stats, today_inh_count, signalements_en_attente)
        render_quick_actions()
        render_historique(inh_list, exh_list)

        loading.visible = False
        page.update()

    def render_kpis(stats, today_inh_count, signalements_en_attente) -> None:
        kpis = [
            {"label": "Caveaux disponibles", "value": stats.get("available", 0), "icon": ft.Icons.CHECK_CIRCLE, "color": PALETTE["green"]},
            {"label": "Caveaux réservés", "value": stats.get("reserved", 0), "icon": ft.Icons.HOURGLASS_TOP, "color": PALETTE["orange"]},
            {"label": "Caveaux occupés", "value": stats.get("occupied", 0), "icon": ft.Icons.DESCRIPTION, "color": PALETTE["grey"]},
            {"label": "Inhumations aujourd'hui", "value": today_inh_count, "icon": ft.Icons.HISTORY, "color": PALETTE["blue"]},
            {"label": "Mes signalements en attente", "value": signalements_en_attente, "icon": ft.Icons.WARNING, "color": "#F9A825"},
        ]
        kpi_row.controls.clear()
        for kpi in kpis:
            kpi_row.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Container(content=ft.Icon(kpi["icon"], color=Colors.TEXT_ON_DARK, size=24), bgcolor=kpi["color"], padding=10, border_radius=10),
                        ft.Column([ft.Text(kpi["label"], size=11, color=Colors.NEUTRAL), ft.Text(str(kpi["value"]), size=20, weight=ft.FontWeight.BOLD, color=Colors.TEXT)], spacing=2, expand=True),
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=14, bgcolor="#FFFFFF", border_radius=12, border=ft.Border(top=ft.BorderSide(3, kpi["color"])),
                    shadow=ft.BoxShadow(spread_radius=0, blur_radius=8, color="#00000012"),
                    col={"xs": 12, "sm": 12, "md": 6, "lg": 3},
                )
            )

    def render_quick_actions() -> None:
        """✅ CORRECTION : on_click directement sur le ElevatedButton, pas sur le Container"""
        actions_row.controls.clear()
        actions = [
            {"label": "Ouvrir la carte", "icon": ft.Icons.MAP, "route": "/carte", "color": PALETTE["blue"]},
            {"label": "Confirmer inhumation", "icon": ft.Icons.ADD_TASK, "route": "/inhumations", "color": PALETTE["green"]},
            {"label": "Consulter un caveau", "icon": ft.Icons.SEARCH, "route": "/carte", "color": None},
            {"label": "Mes signalements", "icon": ft.Icons.WARNING, "route": "/graves/signalements", "color": "#F9A825"},
        ]
        
        for act in actions:
            actions_row.controls.append(
                ft.Container(
                    content=ft.ElevatedButton(
                        content=ft.Row([ft.Icon(act["icon"], size=18), ft.Text(act["label"], size=12)], spacing=6),
                        style=ft.ButtonStyle(
                            bgcolor=act["color"] or "#FFFFFF", 
                            color=Colors.TEXT_ON_DARK if act["color"] else Colors.TEXT
                        ),
                        width=float("inf"),
                        on_click=lambda _, r=act["route"]: page.go(r),  # ✅ ICI le on_click
                    ),
                    col={"xs": 12, "sm": 6, "md": 3},
                )
            )

    def render_historique(inh_list, exh_list) -> None:
        historique_list.controls.clear()
        combined = []
        for item in inh_list:
            combined.append({
                "type": "inhumation",
                "date": item.get("date_inhumation"),
                "grave_code": item.get("grave_code", "?"),
                "defunt": f"{item.get('defunt_nom', 'N/A')} {item.get('defunt_prenom', '')}".strip(),
            })
        for item in exh_list:
            inh = item.get("inhumation", {})
            combined.append({
                "type": "exhumation",
                "date": item.get("date_prevue"),
                "grave_code": item.get("grave_code", "?"),
                "defunt": inh.get("defunt_nom", "N/A") if isinstance(inh, dict) else "N/A",
            })

        combined.sort(key=lambda x: x.get("date") or "", reverse=True)
        combined = combined[:8]

        if not combined:
            historique_list.controls.append(ft.Text("Aucune intervention récente.", color=Colors.NEUTRAL, italic=True))
            return

        for item in combined:
            is_inh = item["type"] == "inhumation"
            color = PALETTE["blue"] if is_inh else PALETTE["orange"]
            icon = ft.Icons.HISTORY if is_inh else ft.Icons.UNARCHIVE
            label = "Inhumation" if is_inh else "Exhumation"
            date_str = str(item["date"])[:10] if item["date"] else "?"
            historique_list.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(icon, color=color, size=20),
                        ft.Column([
                            ft.Text(f"{label} • Caveau {item['grave_code']}", size=13, weight=ft.FontWeight.W_600),
                            ft.Text(f"Défunt : {item['defunt']} • {date_str}", size=11, color=Colors.NEUTRAL),
                        ], spacing=2, expand=True),
                        ft.TextButton("Détails", on_click=lambda _, r=("/inhumations" if is_inh else "/exhumations"): page.go(r)),
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=10, bgcolor="#FFFFFF", border_radius=8, border=ft.Border(left=ft.BorderSide(3, color)),
                )
            )

    def do_search(_):
        code = (search_field.value or "").strip().lower()
        search_results.controls.clear()
        if not code:
            page.update()
            return
        try:
            all_graves = auth.api.get("/cemetery/graves")
            graves_list = all_graves if isinstance(all_graves, list) else all_graves.get("results", [])
            matches = [g for g in graves_list if code in g.get("code", "").lower()][:10]
            if not matches:
                search_results.controls.append(ft.Text("Aucun caveau trouvé.", color=Colors.NEUTRAL, italic=True))
            for g in matches:
                search_results.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Text(g.get("code", "?"), weight=ft.FontWeight.W_600, expand=True),
                            ft.TextButton("Voir", on_click=lambda _, gid=g.get("id"): page.go(f"/carte?grave_id={gid}")),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        padding=8, bgcolor="#FFFFFF", border_radius=8, border=ft.Border.all(1, Colors.BORDER),
                    )
                )
        except Exception as exc:
            search_results.controls.append(ft.Text(f"Erreur : {exc}", color=Colors.ERROR))
        page.update()

    load_data()
    width = page.window.width or 1200
    device = get_device_type(width)

    return ft.View(
        route="/dashboard/agent",
        controls=[
            ft.Column([
                ft.Row([ft.Text("Tableau de bord Agent", style=heading_style(size=22)), ft.Container(expand=True)]),
                ft.Container(height=16),
                loading, error_text, kpi_row, ft.Container(height=16),

                ft.Text("Actions rapides", style=heading_style(size=16)),
                ft.Container(height=8),
                actions_row,
                ft.Container(height=16),

                ft.Container(
                    content=ft.Column([
                        ft.Text("Rechercher un caveau", style=heading_style(size=16)),
                        ft.Container(height=8),
                        ft.Row([search_field, ft.Container(width=10)]),
                        ft.ElevatedButton(
                            content=ft.Row(
                                [ft.Icon(ft.Icons.SEARCH, size=18, color=Colors.TEXT_ON_DARK), ft.Text("Rechercher", color=Colors.TEXT_ON_DARK)],
                                spacing=6, tight=True,
                            ),
                            style=ft.ButtonStyle(bgcolor=Colors.PRIMARY),
                            width=float("inf"),
                            on_click=do_search,
                        ),
                        ft.Container(height=8),
                        search_results,
                    ]),
                    padding=20, bgcolor="#FFFFFF", border_radius=12, shadow=ft.BoxShadow(spread_radius=0, blur_radius=8, color="#00000012"),
                ),
                ft.Container(height=16),

                ft.Container(
                    content=ft.Column([ft.Text("Historique des dernières interventions", style=heading_style(size=16)), ft.Container(height=10), historique_list]),
                    padding=20, bgcolor="#FFFFFF", border_radius=12, shadow=ft.BoxShadow(spread_radius=0, blur_radius=8, color="#00000012"),
                ),
            ], expand=True),
        ],
        bgcolor=Colors.BACKGROUND,
        padding=24 if device != "mobile" else 16,
    )