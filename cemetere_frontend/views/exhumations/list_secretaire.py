"""
views/exhumations/list_secretaire.py — Gestion des demandes d'exhumation (Secrétariat).
Compatible Flet 0.86.3. Lecture seule : pas de validation ni de rejet.
"""
from __future__ import annotations
import asyncio
import flet as ft
from core.auth import AuthState
from core.theme import Colors, get_device_type, heading_style

STATUS_LABELS = {"pending": ("En attente", "#8B6B3F"), "approved": ("Validée", "#2E7D9A"), "rejected": ("Rejetée", "#8A4343"), "completed": ("Effectuée", "#496042")}

def build_exhumations_list_secretaire_view(page: ft.Page, auth: AuthState) -> ft.View:
    exhumations: list[dict] = []
    loading = ft.ProgressRing(visible=True)
    error_text = ft.Text("", color=Colors.ERROR, size=13, visible=False)
    list_container = ft.Column(spacing=10)

    async def _load_data() -> None:
        loading.visible, error_text.visible = True, False
        page.update()
        try:
            data = auth.api.get("/cemetery/exhumations")
            exhumations.clear()
            if isinstance(data, list): exhumations.extend(data)
            elif isinstance(data, dict): exhumations.extend(data.get("results", data.get("items", [])))
            render_list()
        except Exception as exc:
            error_text.value, error_text.visible = f"Erreur : {exc}", True
        finally:
            loading.visible = False
            page.update()

    def render_list() -> None:
        list_container.controls.clear()
        if not exhumations:
            list_container.controls.append(ft.Container(content=ft.Text("Aucune demande d'exhumation.", color=Colors.NEUTRAL, italic=True), padding=40, alignment=ft.Alignment(0.5, 0.5)))
        else:
            for ex in exhumations: list_container.controls.append(build_exhumation_card(ex))
        page.update()

    def show_details_dialog(ex: dict) -> None:
        status_label, _ = STATUS_LABELS.get(ex.get("status", "pending"), ("Inconnu", "#8B8B8B"))
        inhumation_data = ex.get("inhumation") if isinstance(ex.get("inhumation"), dict) else {}
        dialog = ft.AlertDialog(modal=True, title=ft.Text("Détails de l'exhumation", weight=ft.FontWeight.BOLD),
            content=ft.Container(content=ft.Column([
                ft.Text(f"Caveau : {ex.get('grave_code') or 'N/A'}", weight=ft.FontWeight.W_600, size=14),
                ft.Text(f"Défunt : {ex.get('defunt_nom') or inhumation_data.get('defunt_nom', 'Inconnu')}", size=13, color=Colors.NEUTRAL),
                ft.Divider(),
                ft.Text(f"Statut : {status_label}", size=13, weight=ft.FontWeight.W_600),
                ft.Text(f"Motif : {ex.get('motif', 'Aucun')}", size=12, color=Colors.NEUTRAL),
            ], spacing=8, tight=True, scroll=ft.ScrollMode.AUTO), width=400),
            actions=[ft.TextButton("Fermer", on_click=lambda _: setattr(dialog, 'open', False) or page.update())])
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def build_exhumation_card(ex: dict) -> ft.Control:
        status = ex.get("status", "pending")
        label, color = STATUS_LABELS.get(status, ("Inconnu", "#8B8B8B"))
        actions = [ft.IconButton(icon=ft.Icons.VISIBILITY, tooltip="Voir les détails", icon_size=20, on_click=lambda _, e=ex: show_details_dialog(e))]
        
        if status == "pending":
            actions.append(ft.Text("En attente de validation Admin", size=11, color=Colors.NEUTRAL, italic=True))
        elif status in ["approved", "completed"]:
            actions.append(ft.TextButton(content=ft.Row([ft.Icon(ft.Icons.PICTURE_AS_PDF, size=14), ft.Text("PV", size=12)], spacing=4), on_click=lambda _, eid=ex["id"]: page.run_task(download_pv, eid)))

        return ft.Container(content=ft.Column([
            ft.Row([ft.Text(f"Exhumation - Caveau {ex.get('grave_code') or 'N/A'}", weight=ft.FontWeight.W_600, size=14, expand=True), ft.Container(content=ft.Text(label, size=11, color=Colors.TEXT_ON_DARK), bgcolor=color, padding=8, border_radius=12)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Text(f"Motif : {ex.get('motif', 'Non spécifié')}", size=12, color=Colors.NEUTRAL, italic=True, max_lines=2),
            ft.Divider(height=10, color=Colors.BORDER),
            ft.Row(actions, wrap=True, spacing=8) if actions else ft.Text("Aucune action", size=12, color=Colors.NEUTRAL, italic=True),
        ], spacing=6), padding=14, bgcolor="#FFFFFF", border_radius=10, border=ft.Border.all(1, Colors.BORDER))

    async def download_pv(ex_id: int) -> None:
        try:
            await page.launch_url(f"http://127.0.0.1:8000/api/cemetery/exhumations/{ex_id}/pv/download?token={auth.access_token or ''}")
        except Exception: pass

    width = getattr(page, 'window', page).width if hasattr(page, 'window') else (getattr(page, 'width', 1200) or 1200)
    device = get_device_type(width)
    page.run_task(_load_data)

    return ft.View(route="/exhumations", controls=[ft.Text("Gestion des Exhumations", style=heading_style(size=22)), ft.Container(height=10), ft.Text("Suivi des demandes (Lecture seule).", size=14, color=Colors.NEUTRAL), ft.Container(height=20), error_text, loading, list_container], bgcolor=Colors.BACKGROUND, padding=16 if device == "mobile" else 32)