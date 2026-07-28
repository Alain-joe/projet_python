"""
views/concessions/list.py — Liste des concessions avec filtres et indicateurs.
Compatible Flet 0.86.0
CORRECTION : Ajout du statut 'en_attente_creation' et bouton de création
CORRECTION : Réduction de la taille des boutons de filtre (taille standard)
"""
from __future__ import annotations
import asyncio
import flet as ft
from core.auth import AuthState
from core.api import ApiError, Endpoints
from core.theme import Colors, get_device_type, heading_style

STATUS_CONFIG = {
    "en_attente_creation": {"label": "À créer", "color": "#8B6B3F", "icon": ft.Icons.PENDING}, # ✅ NOUVEAU
    "active": {"label": "Active", "color": "#496042", "icon": ft.Icons.CHECK_CIRCLE},
    "expired": {"label": "Expirée", "color": "#8A4343", "icon": ft.Icons.WARNING},
    "resiliee": {"label": "Résiliée", "color": "#8B8B8B", "icon": ft.Icons.CANCEL},
}

FILTERS = [
    ("all", "Toutes", ft.Icons.FILTER_LIST),
    ("active", "Actives", ft.Icons.CHECK_CIRCLE),
    ("en_attente_creation", "À créer", ft.Icons.PENDING), # ✅ NOUVEAU
    ("expired", "Expirées", ft.Icons.WARNING),
    ("resiliee", "Résiliées", ft.Icons.CANCEL),
]


def build_concessions_list_view(page: ft.Page, auth: AuthState) -> ft.View:
    concessions: list[dict] = []
    current_filter = "all"
    search_query = ""

    error_text = ft.Text("", color=Colors.ERROR, size=13, visible=False)
    loading = ft.ProgressRing(visible=True)
    list_container = ft.Column(spacing=10)

    search_field = ft.TextField(
        label="Rechercher (Client, Caveau...)",
        prefix_icon=ft.Icons.SEARCH,
        border_radius=12,
        filled=True,
        bgcolor=Colors.BACKGROUND,
        expand=True,
        on_change=lambda e: on_search_change(e.data),
    )

    filter_buttons = []

    def on_search_change(query: str):
        nonlocal search_query
        search_query = query.strip().lower()
        render_concessions()

    def _filter_button_style(active: bool) -> ft.ButtonStyle:
        return ft.ButtonStyle(
            bgcolor=Colors.PRIMARY if active else "#FFFFFF",
            color=Colors.TEXT_ON_DARK if active else Colors.TEXT,
            side=ft.BorderSide(1, Colors.PRIMARY if active else Colors.BORDER),
            padding=ft.Padding(left=10, right=10, top=6, bottom=6),
            shape=ft.RoundedRectangleBorder(radius=8),
        )

    def on_filter_click(filter_key: str, btn: ft.ElevatedButton):
        nonlocal current_filter
        current_filter = filter_key
        for b in filter_buttons:
            b.style = _filter_button_style(b == btn)
        page.update()
        load_concessions()

    for key, label, icon in FILTERS:
        btn = ft.ElevatedButton(
            content=ft.Row(
                [ft.Icon(icon, size=14), ft.Text(label, size=12)],
                spacing=4,
                tight=True,
            ),
            style=_filter_button_style(key == current_filter),
        )
        btn.on_click = lambda _, k=key, b=btn: on_filter_click(k, b)
        filter_buttons.append(btn)

    def load_concessions() -> None:
        loading.visible = True
        error_text.visible = False
        page.update()
        try:
            params = {"status": current_filter} if current_filter != "all" else None
            data = auth.api.get(Endpoints.CONCESSIONS, params=params)
            concessions.clear()
            if isinstance(data, list):
                concessions.extend(data)
            elif isinstance(data, dict):
                concessions.extend(data.get("results", data.get("items", [])))
            render_concessions()
        except Exception as exc:
            error_text.value = f"Erreur : {exc}"
            error_text.visible = True
            list_container.controls = []
        finally:
            loading.visible = False
            page.update()

    async def _delayed_load() -> None:
        await asyncio.sleep(0.1)
        load_concessions()

    async def _download_pdf(concession_id: int) -> None:
        try:
            token = auth.access_token or ""
            url = f"http://127.0.0.1:8000/api/cemetery/concessions/{concession_id}/contrat/download?token={token}"
            await page.launch_url(url)
        except Exception as e:
            print(f"Erreur téléchargement : {e}")

    def get_expiration_badge(c: dict) -> ft.Control:
        days = c.get("days_remaining")
        is_expiring = c.get("is_expiring_soon", False)
        is_expired = c.get("is_expired", False)
        if is_expired or (days is not None and days < 0):
            return ft.Container(content=ft.Text("Expirée", size=11, color=Colors.TEXT_ON_DARK), bgcolor="#8A4343", padding=8, border_radius=12)
        elif is_expiring or (days is not None and 0 <= days <= 30):
            color = "#8A4343" if days <= 15 else "#8B6B3F"
            return ft.Container(content=ft.Text(f"Exp. dans {days}j", size=11, color=Colors.TEXT_ON_DARK), bgcolor=color, padding=8, border_radius=12)
        return ft.Container()

    def build_concession_card(c: dict) -> ft.Control:
        status = c.get("status", "active")
        config = STATUS_CONFIG.get(status, STATUS_CONFIG["active"])
        grave_code = c.get("grave_code", f"ID:{c.get('grave_id')}")
        client = c.get("client_username", "Inconnu")
        date_fin = c.get("date_fin", "Perpétuelle")
        cid = c['id']

        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text(f"Caveau {grave_code}", weight=ft.FontWeight.W_600, size=14),
                    ft.Container(content=ft.Text(config["label"], size=11, color=Colors.TEXT_ON_DARK), bgcolor=config["color"], padding=8, border_radius=12),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Text(f"Client : {client}", size=12, color=Colors.NEUTRAL),
                ft.Row([ft.Text(f"Fin : {date_fin}", size=12, color=Colors.NEUTRAL), get_expiration_badge(c)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(height=10, color=Colors.BORDER),
                ft.Row([
                    ft.TextButton("Détails", icon=ft.Icons.INFO, on_click=lambda _: page.go(f"/concessions/detail?concession_id={cid}")),
                    ft.TextButton(
                        content=ft.Row([ft.Icon(ft.Icons.DOWNLOAD, size=14), ft.Text("PDF", size=12)], spacing=4), 
                        on_click=lambda _, download_id=cid: page.run_task(_download_pdf, download_id)
                    ),
                    ft.TextButton("Renouveler", icon=ft.Icons.AUTORENEW, visible=(status == "active"), on_click=lambda _: page.go(f"/concessions/renewal?concession_id={cid}")),
                ], alignment=ft.MainAxisAlignment.END),
            ], spacing=6),
            padding=14,
            bgcolor="#FFFFFF",
            border_radius=10,
            border=ft.Border(left=ft.BorderSide(1, Colors.BORDER), right=ft.BorderSide(1, Colors.BORDER), top=ft.BorderSide(1, Colors.BORDER), bottom=ft.BorderSide(1, Colors.BORDER)),
        )

    def render_concessions() -> None:
        list_container.controls.clear()
        filtered = concessions
        if search_query:
            filtered = [c for c in concessions if search_query in str(c.get("client_username", "")).lower() or search_query in str(c.get("grave_code", "")).lower()]
        if not filtered:
            list_container.controls.append(ft.Container(content=ft.Text("Aucune concession trouvée.", color=Colors.NEUTRAL, italic=True), padding=40, alignment=ft.Alignment(0.5, 0.5)))
        else:
            for c in filtered:
                list_container.controls.append(build_concession_card(c))
        page.update()

    device = get_device_type(page.width or 1200) # ✅ CORRECTION: page.width au lieu de page.window.width
    page.run_task(_delayed_load)

    return ft.View(
        route="/concessions",
        controls=[
            ft.Row([
                ft.Text("Gestion des Concessions", style=heading_style(size=22)),
                ft.Container(expand=True),
                # ✅ NOUVEAU : Bouton pour créer une concession depuis une réservation
                ft.ElevatedButton(
                    "Nouvelle Concession",
                    icon=ft.Icons.ADD,
                    bgcolor=Colors.PRIMARY,
                    color=Colors.TEXT_ON_DARK,
                    on_click=lambda _: page.go("/concessions/nouvelle")
                )
            ]),
            ft.Container(height=10), 
            search_field, 
            ft.Container(height=10),
            ft.Row(filter_buttons, wrap=True, spacing=8), 
            ft.Container(height=15),
            error_text, loading, list_container,
        ],
        bgcolor=Colors.BACKGROUND,
        padding=16 if device == "mobile" else 32,
    )