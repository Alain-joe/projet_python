"""
views/graves/list_secretaire.py — Liste des sépultures (Secrétariat).
Compatible Flet 0.86.3. Pas de bouton de signalement.
CORRECTION : Suppression du slash final dans l'appel API pour éviter le 404.
"""
from __future__ import annotations
import flet as ft
from core.auth import AuthState
from core.api import ApiError
from core.theme import Colors, get_device_type, heading_style

STATUS_CONFIG = {
    "available": {"label": "Disponible", "color": "#496042", "icon": ft.Icons.CHECK_CIRCLE}, 
    "reserved": {"label": "Réservé", "color": "#8B6B3F", "icon": ft.Icons.EVENT_NOTE}, 
    "occupied": {"label": "Occupé", "color": "#8A4343", "icon": ft.Icons.LOCK}, 
    "non_exploitable": {"label": "Non exploitable", "color": "#8B8B8B", "icon": ft.Icons.BLOCK}
}
FILTERS = [
    ("all", "Tous", ft.Icons.FILTER_LIST), 
    ("available", "Disponibles", ft.Icons.CHECK_CIRCLE), 
    ("reserved", "Réservés", ft.Icons.EVENT_NOTE), 
    ("occupied", "Occupés", ft.Icons.LOCK)
]

def build_graves_list_secretaire_view(page: ft.Page, auth: AuthState) -> ft.View:
    graves: list[dict] = []
    current_filter = "all"
    error_text = ft.Text("", color=Colors.ERROR, size=13, visible=False)
    loading = ft.ProgressRing(visible=True)
    search_field = ft.TextField(
        label="Rechercher un caveau (Code, Section...)", 
        prefix_icon=ft.Icons.SEARCH, 
        border_radius=12, 
        filled=True, 
        bgcolor=Colors.BACKGROUND, 
        expand=True, 
        on_change=lambda _: render_graves()
    )

    filter_buttons = []
    def on_filter_click(filter_key: str, btn: ft.ElevatedButton):
        nonlocal current_filter
        current_filter = filter_key
        for b in filter_buttons: 
            b.style = ft.ButtonStyle(
                bgcolor=Colors.PRIMARY if b == btn else "#FFFFFF", 
                color=Colors.TEXT_ON_DARK if b == btn else Colors.TEXT, 
                side=ft.BorderSide(1, Colors.PRIMARY if b == btn else Colors.BORDER), 
                padding=ft.Padding(left=10, top=6, right=10, bottom=6)
            )
        page.update()
        render_graves()

    for key, label, icon in FILTERS:
        btn = ft.ElevatedButton(
            content=ft.Row([ft.Icon(icon, size=14), ft.Text(label, size=12)], spacing=4, tight=True), 
            style=ft.ButtonStyle(
                bgcolor=Colors.PRIMARY if key == current_filter else "#FFFFFF", 
                color=Colors.TEXT_ON_DARK if key == current_filter else Colors.TEXT, 
                side=ft.BorderSide(1, Colors.PRIMARY if key == current_filter else Colors.BORDER), 
                padding=ft.Padding(left=10, top=6, right=10, bottom=6)
            )
        )
        btn.on_click = lambda _, k=key, b=btn: on_filter_click(k, b)
        filter_buttons.append(btn)

    graves_container = ft.Column(spacing=10)

    def load_graves() -> None:
        loading.visible, error_text.visible = True, False
        page.update()
        try:
            # ✅ CORRECTION CRITIQUE : Suppression du slash final pour correspondre au backend
            data = auth.api.get("/cemetery/graves")
            graves.clear()
            if isinstance(data, list): 
                graves.extend(data)
            elif isinstance(data, dict): 
                graves.extend(data.get("items", data.get("results", data.get("data", []))))
        except ApiError as exc: 
            error_text.value, error_text.visible = f"Erreur : {exc.message}", True
        except Exception: 
            error_text.value, error_text.visible = "Impossible de contacter le serveur.", True
        
        loading.visible = False
        render_graves()

    def get_filtered_graves() -> list[dict]:
        filtered = [g for g in graves if g.get("status") == current_filter] if current_filter != "all" else graves
        query = (search_field.value or "").lower().strip()
        if query: 
            filtered = [g for g in filtered if query in str(g.get("code", "")).lower() or query in str(g.get("section", "")).lower()]
        return filtered

    def render_graves() -> None:
        graves_container.controls.clear()
        filtered = get_filtered_graves()
        if not filtered:
            graves_container.controls.append(
                ft.Container(
                    content=ft.Column(
                        [ft.Icon(ft.Icons.MAP, size=40, color=Colors.BORDER), ft.Text("Aucun caveau ne correspond.", color=Colors.NEUTRAL, italic=True)], 
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER, 
                        spacing=10
                    ), 
                    padding=40, 
                    alignment=ft.Alignment(0.5, 0.5)
                )
            )
        else:
            width = getattr(page, 'window', page).width if hasattr(page, 'window') else (getattr(page, 'width', 1200) or 1200)
            device = get_device_type(width)
            if device == "mobile":
                for g in filtered: 
                    graves_container.controls.append(build_grave_card(g))
            else:
                graves_container.controls.append(ft.Row([build_grave_table(filtered)], scroll=ft.ScrollMode.AUTO))
        page.update()

    def build_grave_table(data: list[dict]) -> ft.Control:
        columns = [
            ft.DataColumn(ft.Text("Code", weight=ft.FontWeight.W_600)), 
            ft.DataColumn(ft.Text("Section", weight=ft.FontWeight.W_600)), 
            ft.DataColumn(ft.Text("Statut", weight=ft.FontWeight.W_600)), 
            ft.DataColumn(ft.Text("Prix", weight=ft.FontWeight.W_600)), 
            ft.DataColumn(ft.Text("Actions", weight=ft.FontWeight.W_600))
        ]
        rows = []
        for g in data:
            status = g.get("status", "available")
            config = STATUS_CONFIG.get(status, STATUS_CONFIG["non_exploitable"])
            rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.Text(g.get("code", "?"), weight=ft.FontWeight.W_600)),
                ft.DataCell(ft.Text(g.get("section", "-"))),
                ft.DataCell(ft.Container(
                    content=ft.Row([ft.Icon(config["icon"], size=14, color=Colors.TEXT_ON_DARK), ft.Text(config["label"], size=12, color=Colors.TEXT_ON_DARK)], spacing=4), 
                    bgcolor=config["color"], 
                    padding=ft.Padding(left=8, top=4, right=8, bottom=4), 
                    border_radius=12
                )),
                ft.DataCell(ft.Text(f"{float(g.get('price', 0)):,.0f}".replace(",", " "))),
                ft.DataCell(ft.TextButton(content=ft.Text("Détails", size=12, color=Colors.PRIMARY), on_click=lambda _, grave=g: show_grave_details(grave))),
            ]))
        return ft.DataTable(
            columns=columns, 
            rows=rows, 
            heading_row_color="#F5F3EE", 
            border=ft.Border.all(1, Colors.BORDER), 
            border_radius=8, 
            horizontal_lines=ft.BorderSide(1, Colors.BORDER)
        )

    def build_grave_card(g: dict) -> ft.Control:
        status = g.get("status", "available")
        config = STATUS_CONFIG.get(status, STATUS_CONFIG["non_exploitable"])
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text(g.get("code", "?"), weight=ft.FontWeight.W_600, size=16), 
                    ft.Container(content=ft.Text(config["label"], size=11, color=Colors.TEXT_ON_DARK), bgcolor=config["color"], padding=ft.Padding(left=8, top=4, right=8, bottom=4), border_radius=12)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Text(f"Section : {g.get('section', '-')}", size=13, color=Colors.NEUTRAL),
                ft.Text(f"Prix : {float(g.get('price', 0)):,.0f} FCFA".replace(",", " "), size=13, weight=ft.FontWeight.W_600),
                ft.Divider(height=10, color=Colors.BORDER),
                ft.ElevatedButton(
                    content=ft.Text("Voir les détails", color=Colors.TEXT_ON_DARK), 
                    style=ft.ButtonStyle(bgcolor=Colors.PRIMARY), 
                    width=float("inf"), 
                    on_click=lambda _, grave=g: show_grave_details(grave)
                )
            ], spacing=8), 
            padding=16, 
            bgcolor="#FFFFFF", 
            border_radius=10, 
            border=ft.Border.all(1, Colors.BORDER)
        )

    def show_grave_details(grave: dict):
        page.snack_bar = ft.SnackBar(content=ft.Text(f"Détails du caveau {grave.get('code')} (ID: {grave.get('id')})"), bgcolor=Colors.SECONDARY)
        page.snack_bar.open = True
        page.update()

    load_graves()
    width = getattr(page, 'window', page).width if hasattr(page, 'window') else (getattr(page, 'width', 1200) or 1200)
    device = get_device_type(width)
    
    return ft.View(
        route="/graves", 
        controls=[
            ft.Container(
                content=ft.Column([
                    ft.Text("Gestion des Sépultures", style=heading_style(size=22)), 
                    ft.Container(height=16), 
                    search_field, 
                    ft.Container(height=15), 
                    ft.Row(filter_buttons, wrap=True, spacing=8), 
                    ft.Container(height=15), 
                    error_text, 
                    loading, 
                    ft.Container(
                        content=graves_container, 
                        bgcolor="#FAF9F6", 
                        border_radius=10, 
                        padding=10, 
                        border=ft.Border.all(1, Colors.BORDER)
                    )
                ], spacing=0, expand=True, scroll=ft.ScrollMode.ALWAYS), 
                padding=24, 
                bgcolor="#FFFFFF", 
                border_radius=16, 
                expand=True, 
                shadow=ft.BoxShadow(spread_radius=0, blur_radius=16, color="#0000000F")
            )
        ], 
        bgcolor=Colors.BACKGROUND, 
        padding=16 if device == "mobile" else 32
    )