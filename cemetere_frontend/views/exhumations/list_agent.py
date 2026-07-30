"""
views/exhumations/list_agent.py — Gestion des demandes d'exhumation (Agent).
Compatible Flet 0.86.3. L'agent peut voir les détails et marquer comme effectué, mais PAS valider/rejeter.
"""
from __future__ import annotations
import asyncio
import flet as ft
from datetime import date
from core.auth import AuthState
from core.theme import Colors, get_device_type, heading_style

STATUS_LABELS = {
    "pending": ("En attente", "#8B6B3F"),
    "approved": ("Validée", "#2E7D9A"),
    "rejected": ("Rejetée", "#8A4343"),
    "completed": ("Effectuée", "#496042"),
}

def build_exhumations_list_agent_view(page: ft.Page, auth: AuthState) -> ft.View:
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
            if isinstance(data, list):
                exhumations.extend(data)
            elif isinstance(data, dict):
                exhumations.extend(data.get("results", data.get("items", [])))
            render_list()
        except Exception as exc:
            error_text.value = f"Erreur : {exc}"
            error_text.visible = True
        finally:
            loading.visible = False
            page.update()

    def render_list() -> None:
        list_container.controls.clear()
        if not exhumations:
            list_container.controls.append(
                ft.Container(
                    content=ft.Text("Aucune demande d'exhumation.", color=Colors.NEUTRAL, italic=True),
                    padding=40, alignment=ft.Alignment(0.5, 0.5)
                )
            )
        else:
            for ex in exhumations:
                list_container.controls.append(build_exhumation_card(ex))
        page.update()

    def show_details_dialog(ex: dict) -> None:
        status_label, _ = STATUS_LABELS.get(ex.get("status", "pending"), ("Inconnu", "#8B8B8B"))
        inhumation_data = ex.get("inhumation") if isinstance(ex.get("inhumation"), dict) else {}
        defunt_nom = ex.get("defunt_nom") or inhumation_data.get("defunt_nom", "Inconnu")
        defunt_prenom = ex.get("defunt_prenom") or inhumation_data.get("defunt_prenom", "")
        grave_code = ex.get("grave_code") or "N/A"
        demandeur = ex.get("demandeur_username", "Non renseigné")
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Détails de l'exhumation", weight=ft.FontWeight.BOLD),
            content=ft.Container(
                content=ft.Column([
                    ft.Text(f"Caveau : {grave_code}", weight=ft.FontWeight.W_600, size=14),
                    ft.Text(f"Défunt : {defunt_prenom} {defunt_nom}".strip(), size=13, color=Colors.NEUTRAL),
                    ft.Text(f"Demandeur : {demandeur}", size=13, color=Colors.NEUTRAL),
                    ft.Divider(),
                    ft.Text(f"Statut : {status_label}", size=13, weight=ft.FontWeight.W_600),
                    ft.Text(f"Date prévue : {ex.get('date_prevue', 'N/A')}", size=13),
                    ft.Text(f"Date réelle : {ex.get('date_exhumation') or 'Non effectuée'}", size=13),
                    ft.Divider(),
                    ft.Text("Motif de la demande :", weight=ft.FontWeight.W_600, size=13),
                    ft.Text(ex.get("motif", "Aucun"), size=12, color=Colors.NEUTRAL),
                    ft.Container(height=8),
                    ft.Text("Observations / Motif de rejet :", weight=ft.FontWeight.W_600, size=13),
                    ft.Text(ex.get("observations") or ex.get("motif_rejet") or "Aucune", size=12, color=Colors.NEUTRAL),
                ], spacing=8, tight=True, scroll=ft.ScrollMode.AUTO),
                width=400,
            ),
            actions=[ft.TextButton("Fermer", on_click=lambda _: setattr(dialog, 'open', False) or page.update())],
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def build_exhumation_card(ex: dict) -> ft.Control:
        status = ex.get("status", "pending")
        label, color = STATUS_LABELS.get(status, ("Inconnu", "#8B8B8B"))
        
        inhumation_data = ex.get("inhumation") if isinstance(ex.get("inhumation"), dict) else {}
        defunt_nom = ex.get("defunt_nom") or inhumation_data.get("defunt_nom", "Inconnu")
        grave_code = ex.get("grave_code") or "N/A"
        ex_id = ex["id"]

        actions = [
            ft.IconButton(icon=ft.Icons.VISIBILITY, tooltip="Voir les détails", icon_size=20, on_click=lambda _, e=ex: show_details_dialog(e))
        ]

        # ✅ L'agent NE PEUT PAS valider ou rejeter (réservé à l'admin)
        if status == "pending":
            actions.append(ft.Text("En attente de validation Admin", size=11, color=Colors.NEUTRAL, italic=True))
                
        elif status == "approved":
            # ✅ L'agent PEUT marquer comme effectué sur le terrain
            actions.append(ft.ElevatedButton("Marquer comme effectué", bgcolor="#496042", color=Colors.TEXT_ON_DARK, height=36, on_click=lambda _, eid=ex_id: show_complete_dialog(eid)))
            actions.append(ft.TextButton(content=ft.Row([ft.Icon(ft.Icons.PICTURE_AS_PDF, size=14), ft.Text("PV", size=12)], spacing=4), on_click=lambda _, eid=ex_id: page.run_task(download_pv, eid)))
            
        elif status == "completed":
            actions.append(ft.TextButton(content=ft.Row([ft.Icon(ft.Icons.PICTURE_AS_PDF, size=14), ft.Text("PV", size=12)], spacing=4), on_click=lambda _, eid=ex_id: page.run_task(download_pv, eid)))

        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text(f"Exhumation - Caveau {grave_code}", weight=ft.FontWeight.W_600, size=14, expand=True),
                    ft.Container(content=ft.Text(label, size=11, color=Colors.TEXT_ON_DARK), bgcolor=color, padding=8, border_radius=12),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Text(f"Défunt : {defunt_nom}", size=12, color=Colors.NEUTRAL),
                ft.Text(f"Motif : {ex.get('motif', 'Non spécifié')}", size=12, color=Colors.NEUTRAL, italic=True, max_lines=2),
                ft.Divider(height=10, color=Colors.BORDER),
                ft.Row(actions, wrap=True, spacing=8, run_spacing=8) if actions else ft.Text("Aucune action", size=12, color=Colors.NEUTRAL, italic=True),
            ], spacing=6),
            padding=14, bgcolor="#FFFFFF", border_radius=10,
            border=ft.Border.all(1, Colors.BORDER),
        )

    def show_complete_dialog(ex_id: int) -> None:
        date_field = ft.TextField(label="Date réelle d'exhumation *", value=date.today().isoformat(), border_radius=8)
        obs_field = ft.TextField(label="Observations / N° PV", multiline=True, min_lines=3, border_radius=8)
        error_msg = ft.Text("", color=Colors.ERROR, size=12)

        def on_confirm(e):
            if not date_field.value or not date_field.value.strip():
                error_msg.value = "La date est obligatoire."
                error_msg.update()
                return
            try:
                auth.api.put(f"/cemetery/exhumations/{ex_id}/complete", json={
                    "date_exhumation": date_field.value.strip(),
                    "observations": obs_field.value.strip()
                })
                dialog.open = False
                page.update()
                sb = ft.SnackBar(content=ft.Text("✅ Exhumation clôturée. Caveau libéré.", color=Colors.TEXT_ON_DARK), bgcolor="#496042")
                page.snack_bar = sb
                sb.open = True
                page.update()
                page.run_task(_load_data)
            except Exception as exc:
                error_msg.value = f"Échec : {exc}"
                error_msg.update()

        dialog = ft.AlertDialog(
            modal=True, title=ft.Text("Clôturer l'exhumation", weight=ft.FontWeight.BOLD),
            content=ft.Column([
                ft.Text("Cette action libérera définitivement le caveau.", size=12, color=Colors.ERROR),
                date_field, obs_field, error_msg
            ], spacing=10),
            actions=[
                ft.TextButton("Annuler", on_click=lambda _: setattr(dialog, 'open', False) or page.update()),
                ft.ElevatedButton("Confirmer la clôture", bgcolor="#496042", color=Colors.TEXT_ON_DARK, on_click=on_confirm),
            ], actions_alignment=ft.MainAxisAlignment.END
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    async def download_pv(ex_id: int) -> None:
        try:
            token = auth.access_token or ""
            url = f"http://127.0.0.1:8000/api/cemetery/exhumations/{ex_id}/pv/download?token={token}"
            await page.launch_url(url)
        except Exception as e:
            print(f"Erreur téléchargement PV : {e}")

    width = getattr(page, 'window', page).width if hasattr(page, 'window') else (getattr(page, 'width', 1200) or 1200)
    device = get_device_type(width)
    page.run_task(_load_data)

    return ft.View(
        route="/exhumations",
        controls=[
            ft.Text("Gestion des Exhumations", style=heading_style(size=22)),
            ft.Container(height=10),
            ft.Text("Suivi des demandes (Lecture seule et clôture terrain).", size=14, color=Colors.NEUTRAL),
            ft.Container(height=20),
            error_text, loading, list_container,
        ],
        bgcolor=Colors.BACKGROUND,
        padding=16 if device == "mobile" else 32,
    )