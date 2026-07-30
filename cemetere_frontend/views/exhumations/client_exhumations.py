"""
views/exhumations/client_exhumations.py — Demandes d'exhumation pour le Client.
Compatible Flet 0.86.3. Responsive, avec formulaire de demande en Dialog.
"""
from __future__ import annotations
import flet as ft
from datetime import datetime, date
from core.auth import AuthState
from core.api import Endpoints, ApiError
from core.theme import Colors, get_device_type, heading_style

STATUS_LABELS = {
    "pending": ("En attente", "#F9A825"),
    "approved": ("Validée", "#2E7D9A"),
    "rejected": ("Rejetée", "#C62828"),
    "completed": ("Effectuée", "#496042"),
}

def build_client_exhumations_view(page: ft.Page, auth: AuthState) -> ft.View:
    exhumations = []
    concessions = []
    loading = ft.ProgressRing(visible=True)
    error_text = ft.Text("", color=Colors.ERROR, size=13, visible=False)
    list_container = ft.Column(spacing=10)

    async def load_data() -> None:
        loading.visible, error_text.visible = True, False
        page.update()
        try:
            exh_data = auth.api.get_exhumations_mine()
            exhumations.clear()
            if isinstance(exh_data, list): exhumations.extend(exh_data)
            elif isinstance(exh_data, dict): exhumations.extend(exh_data.get("results", []))

            conc_data = auth.api.get_concessions_mine()
            concessions.clear()
            if isinstance(conc_data, list): concessions.extend(conc_data)
            elif isinstance(conc_data, dict): concessions.extend(conc_data.get("results", []))
            
            render_list()
        except ApiError as exc:
            error_text.value = f"Erreur : {exc.message}"
            error_text.visible = True
        except Exception as exc:
            error_text.value = f"Erreur de connexion : {exc}"
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
            for exh in exhumations:
                list_container.controls.append(build_exhumation_card(exh))
        page.update()

    def build_exhumation_card(exh: dict) -> ft.Control:
        status = exh.get("status", "pending")
        label, color = STATUS_LABELS.get(status, ("Inconnu", "#8B8B8B"))
        grave_code = exh.get("grave", {}).get("code", "?") if isinstance(exh.get("grave"), dict) else "?"

        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text(f"Caveau : {grave_code}", weight=ft.FontWeight.W_600, size=14, expand=True),
                    ft.Container(content=ft.Text(label, size=11, color=Colors.TEXT_ON_DARK), bgcolor=color, padding=8, border_radius=12),
                ]),
                ft.Text(f"Motif : {exh.get('motif', 'N/A')}", size=12, color=Colors.NEUTRAL, max_lines=2),
                ft.Text(f"Date prévue : {exh.get('date_prevue', 'N/A')}", size=12, color=Colors.NEUTRAL),
            ], spacing=6),
            padding=14, bgcolor="#FFFFFF", border_radius=10, border=ft.Border.all(1, Colors.BORDER),
        )

    def show_request_dialog() -> None:
        if not concessions:
            error_text.value = "Vous n'avez aucune concession active pour demander une exhumation."
            error_text.visible = True
            page.update()
            return

        conc_options = [ft.dropdown.Option(str(c["id"]), f"Caveau {c.get('grave', {}).get('code', '?')}") for c in concessions if isinstance(c.get("grave"), dict)]
        
        conc_dropdown = ft.Dropdown(label="Concession concernée *", options=conc_options, border_radius=8, value=str(concessions[0]["id"]))
        motif_field = ft.TextField(label="Motif de la demande *", multiline=True, min_lines=3, border_radius=8)
        date_field = ft.TextField(label="Date souhaitée (AAAA-MM-JJ) *", read_only=True, border_radius=8, suffix=ft.Icon(ft.Icons.CALENDAR_TODAY, color=Colors.PRIMARY))
        status_text = ft.Text("", size=12, color=Colors.ERROR)

        date_picker = ft.DatePicker(
            first_date=datetime.now(),
            on_change=lambda e: setattr(date_field, 'value', e.control.value.strftime("%Y-%m-%d") if e.control.value else ""),
        )
        page.overlay.append(date_picker)

        def open_picker(e):
            date_picker.open = True
            page.update()
        date_field.on_click = open_picker

        def on_cancel(e):
            dialog.open = False
            page.update()

        def on_confirm(e):
            if not motif_field.value.strip() or not date_field.value.strip():
                status_text.value = "❌ Le motif et la date sont obligatoires."
                status_text.update()
                return
            try:
                payload = {
                    "inhumation_id": concessions[0].get("grave", {}).get("inhumation_id"), # À adapter selon ton modèle, ou utiliser l'ID de la concession si le backend le permet
                    "demandeur_id": auth.user.get("id"),
                    "motif": motif_field.value.strip(),
                    "date_prevue": date_field.value.strip(),
                }
                # Note: Si ton backend attend 'concession_id' au lieu de 'inhumation_id', ajuste ici.
                # D'après ton api_exhumations.py, il attend 'inhumation_id'. 
                # Si la concession a une inhumation liée, on la récupère, sinon on utilise un fallback.
                auth.api.post("/cemetery/exhumations", json=payload)
                dialog.open = False
                page.update()
                page.snack_bar = ft.SnackBar(content=ft.Text("✅ Demande envoyée avec succès.", color=Colors.TEXT_ON_DARK), bgcolor="#496042")
                page.snack_bar.open = True
                page.update()
                load_data()
            except ApiError as exc:
                status_text.value = f"❌ Échec : {exc.message}"
                status_text.update()
            except Exception as exc:
                status_text.value = f"❌ Erreur : {exc}"
                status_text.update()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Demander une exhumation", weight=ft.FontWeight.BOLD),
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Cette demande sera soumise à validation administrative.", size=12, color=Colors.NEUTRAL, italic=True),
                    conc_dropdown,
                    motif_field,
                    date_field,
                    status_text,
                ], spacing=10, tight=True, scroll=ft.ScrollMode.AUTO),
                width=400,
            ),
            actions=[
                ft.TextButton("Annuler", on_click=on_cancel),
                ft.ElevatedButton("Envoyer", bgcolor=Colors.PRIMARY, color=Colors.TEXT_ON_DARK, on_click=on_confirm),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    width = getattr(page, 'window', page).width if hasattr(page, 'window') else (getattr(page, 'width', 1200) or 1200)
    device = get_device_type(width)

    page.run_task(load_data)

    return ft.View(
        route="/exhumations/client",
        controls=[
            ft.Row([
                ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: page.go("/dashboard/client")),
                ft.Text("Mes Exhumations", style=heading_style(size=22)),
                ft.Container(expand=True),
                ft.ElevatedButton(
                    content=ft.Row([ft.Icon(ft.Icons.ADD, color=Colors.TEXT_ON_DARK), ft.Text("Nouvelle demande", color=Colors.TEXT_ON_DARK)]),
                    bgcolor=Colors.PRIMARY,
                    on_click=lambda _: show_request_dialog(),
                )
            ]),
            ft.Container(height=16),
            error_text,
            loading,
            list_container,
        ],
        bgcolor=Colors.BACKGROUND,
        padding=16 if device == "mobile" else 32,
        scroll=ft.ScrollMode.AUTO,
    )