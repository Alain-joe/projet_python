"""
views/inhumations/list.py — Registre des inhumations (Historique).
Compatible Flet 0.86.3
CORRECTION : Le bouton "Demander une exhumation" est masqué pour le Secrétariat.
"""
from __future__ import annotations
import flet as ft
from core.auth import AuthState, Role
from core.theme import Colors, get_device_type, heading_style

def build_inhumations_list_view(page: ft.Page, auth: AuthState) -> ft.View:
    inhumations = []
    loading = ft.ProgressRing(visible=True)
    error_text = ft.Text("", color=Colors.ERROR, size=13, visible=False)
    empty_text = ft.Text("Aucune inhumation enregistrée.", color=Colors.NEUTRAL, italic=True, visible=False)
    list_container = ft.Column(spacing=10)

    search_field = ft.TextField(
        hint_text="Rechercher par nom, prénom ou caveau...",
        prefix_icon=ft.Icons.SEARCH,
        expand=True,
        border_radius=8,
    )

    async def load_inhumations(search_query: str = "") -> None:
        loading.visible, error_text.visible, empty_text.visible = True, False, False
        page.update()
        try:
            params = {"search": search_query.strip()} if search_query.strip() else {}
            data = auth.api.get("/cemetery/inhumations", params=params)
            inhumations.clear()
            if isinstance(data, list):
                inhumations.extend(data)
            elif isinstance(data, dict):
                inhumations.extend(data.get("results", []))
            render_list()
        except Exception as exc:
            error_text.value = f"Erreur de chargement : {exc}"
            error_text.visible = True
        finally:
            loading.visible = False
            page.update()

    async def apply_filters(e=None):
        await load_inhumations(search_field.value)

    search_field.on_submit = apply_filters

    def render_list():
        list_container.controls.clear()
        if not inhumations:
            empty_text.visible = True
        else:
            empty_text.visible = False
            for inh in inhumations:
                date_str = str(inh.get("date_inhumation", ""))[:10] if inh.get("date_inhumation") else "N/A"
                heure_str = inh.get("heure_inhumation", "")
                defunt = f"{inh.get('defunt_prenom', '')} {inh.get('defunt_nom', '')}".strip() or "Inconnu"
                grave_code = inh.get("grave_code", "?")
                agent = inh.get("agent_username", "Non renseigné")

                # ✅ CORRECTION : Le bouton "Demander une exhumation" n'est visible que pour Admin et Agent
                actions = [
                    ft.IconButton(
                        icon=ft.Icons.VISIBILITY,
                        tooltip="Voir détails",
                        on_click=lambda _, i=inh: show_details_dialog(i),
                    )
                ]
                if auth.role in [Role.ADMIN, Role.AGENT]:
                    actions.append(
                        ft.IconButton(
                            icon=ft.Icons.UNARCHIVE,
                            icon_color=Colors.ERROR,
                            tooltip="Demander une exhumation",
                            on_click=lambda _, i=inh: show_request_exhumation_dialog(i),
                        )
                    )

                list_container.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Column([
                                ft.Text(f"Caveau {grave_code}", weight=ft.FontWeight.W_600, size=14),
                                ft.Text(f"Défunt : {defunt}", size=12, color=Colors.NEUTRAL),
                                ft.Text(f"Agent : {agent}", size=11, color=Colors.NEUTRAL, italic=True),
                            ], spacing=4, expand=True),
                            ft.Column([
                                ft.Text(f"Date : {date_str}", size=12, weight=ft.FontWeight.W_600),
                                ft.Text(f"Heure : {heure_str or 'N/A'}", size=11, color=Colors.NEUTRAL),
                            ], spacing=4, horizontal_alignment=ft.CrossAxisAlignment.END),
                            ft.Row(actions, spacing=4),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=14, bgcolor="#FFFFFF", border_radius=10, border=ft.Border.all(1, Colors.BORDER),
                    )
                )
        page.update()

    def show_request_exhumation_dialog(inh: dict):
        motif_field = ft.TextField(label="Motif de l'exhumation *", multiline=True, min_lines=3, border_radius=8)
        date_field = ft.TextField(label="Date prévue *", border_radius=8, hint_text="AAAA-MM-JJ")
        status_text = ft.Text("", size=12, color=Colors.ERROR)

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
                    "inhumation_id": inh["id"],
                    "motif": motif_field.value.strip(),
                    "date_prevue": date_field.value.strip(),
                }
                auth.api.post("/cemetery/exhumations", json=payload)
                dialog.open = False
                page.update()
                
                sb = ft.SnackBar(content=ft.Text("✅ Demande d'exhumation envoyée à l'administration.", color=Colors.TEXT_ON_DARK), bgcolor="#496042")
                page.snack_bar = sb
                sb.open = True
                page.update()
            except Exception as exc:
                status_text.value = f"❌ Échec : {exc}"
                status_text.update()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Demander une exhumation", weight=ft.FontWeight.BOLD),
            content=ft.Container(
                content=ft.Column([
                    ft.Text(f"Caveau concerné : {inh.get('grave_code', '?')}", weight=ft.FontWeight.W_600),
                    ft.Text(f"Défunt : {inh.get('defunt_nom', '')} {inh.get('defunt_prenom', '')}", size=13, color=Colors.NEUTRAL),
                    ft.Divider(),
                    ft.Text("Cette demande sera soumise à validation administrative.", size=12, color=Colors.NEUTRAL, italic=True),
                    motif_field,
                    date_field,
                    status_text,
                ], spacing=10, tight=True),
                width=400,
            ),
            actions=[
                ft.TextButton("Annuler", on_click=on_cancel),
                ft.ElevatedButton("Envoyer la demande", bgcolor=Colors.PRIMARY, color=Colors.TEXT_ON_DARK, on_click=on_confirm),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def show_details_dialog(inh: dict):
        defunt = f"{inh.get('defunt_prenom', '')} {inh.get('defunt_nom', '')}".strip() or "Inconnu"
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Détails de l'inhumation", weight=ft.FontWeight.BOLD),
            content=ft.Container(
                content=ft.Column([
                    ft.Text(f"Défunt : {defunt}", weight=ft.FontWeight.W_600),
                    ft.Text(f"Caveau : {inh.get('grave_code', '?')}", size=13),
                    ft.Text(f"Date de naissance : {inh.get('defunt_date_naissance') or 'N/A'}", size=13),
                    ft.Text(f"Date de décès : {inh.get('defunt_date_deces') or 'N/A'}", size=13),
                    ft.Divider(),
                    ft.Text(f"Date d'inhumation : {str(inh.get('date_inhumation', ''))[:10]}", size=13),
                    ft.Text(f"Heure : {inh.get('heure_inhumation') or 'N/A'}", size=13),
                    ft.Text(f"Agent responsable : {inh.get('agent_username', 'N/A')}", size=13),
                    ft.Divider(),
                    ft.Text("Observations :", weight=ft.FontWeight.W_600, size=13),
                    ft.Text(inh.get("observations") or "Aucune", size=12, color=Colors.NEUTRAL),
                ], spacing=8, tight=True),
                width=400,
            ),
            actions=[ft.TextButton("Fermer", on_click=lambda _: setattr(dialog, 'open', False) or page.update())],
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    device = get_device_type(page.width or 1200)
    page.run_task(load_inhumations)

    return ft.View(
        route="/inhumations",
        controls=[
            ft.Row([
                ft.Text("Registre des Inhumations", style=heading_style(size=22)),
                ft.Container(expand=True),
                ft.ElevatedButton("🔄 Actualiser", icon=ft.Icons.REFRESH, bgcolor=Colors.PRIMARY, color=Colors.TEXT_ON_DARK, on_click=apply_filters),
            ]),
            ft.Container(height=10),
            search_field,
            ft.Container(height=15),
            error_text, loading, empty_text, list_container,
        ],
        bgcolor=Colors.BACKGROUND,
        padding=16 if device == "mobile" else 32,
        scroll=ft.ScrollMode.AUTO,
    )