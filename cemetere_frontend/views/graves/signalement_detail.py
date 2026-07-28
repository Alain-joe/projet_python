"""
views/graves/signalement_detail.py — Détail et validation d'un signalement.
Compatible Flet 0.86.0
CORRECTION : Utilisation de page.overlay.append (comme dans detail.py) pour garantir l'affichage et l'exécution du dialog.
"""
from __future__ import annotations
import flet as ft
from urllib.parse import urlparse, parse_qs

from core.auth import AuthState
from core.api import ApiError
from core.theme import Colors, get_device_type, heading_style


def build_signalement_detail_view(page: ft.Page, auth: AuthState) -> ft.View:
    query = parse_qs(urlparse(page.route).query)
    signalement_id_str = query.get("signalement_id", [None])[0]

    if not signalement_id_str:
        page.go("/graves/signalements")
        return ft.View(route="/graves/signalements/detail", controls=[])

    try:
        signalement_id = int(signalement_id_str)
    except ValueError:
        page.go("/graves/signalements")
        return ft.View(route="/graves/signalements/detail", controls=[])

    sig_data = {}
    loading = ft.ProgressRing(visible=True)
    error_text = ft.Text("", color=Colors.ERROR, size=13, visible=False)
    info_column = ft.Column(spacing=8)

    def load_data():
        loading.visible, error_text.visible = True, False
        page.update()
        try:
            data = auth.api.get_signalement(signalement_id)
            sig_data.update(data)
            render_detail()
        except ApiError as exc:
            error_text.value = f"Erreur de chargement : {exc.message}"
            error_text.visible = True
        finally:
            loading.visible = False
            page.update()

    def render_detail():
        statut = sig_data.get("statut", "en_attente")
        color = "#F9A825" if statut == "en_attente" else ("#496042" if statut == "valide" else "#C62828")
        
        info_column.controls = [
            ft.Row([
                ft.Text(f"Signalement #{sig_data.get('id')}", style=heading_style(size=18)),
                ft.Container(
                    content=ft.Text(statut.upper(), size=12, color=Colors.TEXT_ON_DARK),
                    bgcolor=color, padding=ft.Padding(left=8, top=4, right=8, bottom=4), border_radius=12,
                )
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(),
            ft.Row([ft.Text("Caveau :", weight=ft.FontWeight.W_600), ft.Text(sig_data.get("grave_code", "N/A"))]),
            ft.Row([ft.Text("Signalé par :", weight=ft.FontWeight.W_600), ft.Text(sig_data.get("signale_par", "N/A"))]),
            ft.Row([ft.Text("Date :", weight=ft.FontWeight.W_600), ft.Text(str(sig_data.get("date_signalement", ""))[:10])]),
            ft.Divider(),
            ft.Text("Motif du problème", weight=ft.FontWeight.W_600, size=14),
            ft.Text(sig_data.get("motif", "Aucun motif"), size=13, color=Colors.TEXT),
            ft.Container(height=10),
            ft.Text("Description", weight=ft.FontWeight.W_600, size=14),
            ft.Text(sig_data.get("description", "Aucune description"), size=13, color=Colors.NEUTRAL),
        ]
        
        if sig_data.get("statut") == "rejete" and sig_data.get("motif_rejet"):
            info_column.controls.extend([
                ft.Divider(),
                ft.Text("Motif du rejet", weight=ft.FontWeight.W_600, size=14, color=Colors.ERROR),
                ft.Text(sig_data.get("motif_rejet"), size=13, color=Colors.ERROR),
            ])

    # ✅ CORRECTION : Structure identique à resiliate_concession dans detail.py
    def show_reject_dialog():
        motif_field = ft.TextField(label="Motif du rejet *", multiline=True, min_lines=3, border_radius=8)
        error_msg = ft.Text("", color=Colors.ERROR, size=12)

        def on_confirm(e):
            if not motif_field.value.strip():
                error_msg.value = "Le motif est obligatoire."
                error_msg.update()
                return
            try:
                auth.api.rejeter_signalement(signalement_id, motif_field.value.strip())
                dialog.open = False
                page.update()
                
                sb = ft.SnackBar(content=ft.Text("✅ Signalement rejeté avec succès.", color=Colors.TEXT_ON_DARK), bgcolor=Colors.ERROR)
                page.snack_bar = sb
                sb.open = True
                page.update()
                
                page.go("/graves/signalements")
            except Exception as exc:
                error_msg.value = f"Erreur : {exc}"
                error_msg.update()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Rejeter le signalement", weight=ft.FontWeight.BOLD),
            content=ft.Column([
                ft.Text("Le caveau conservera son statut actuel. Veuillez indiquer la raison du rejet."),
                motif_field,
                error_msg
            ], spacing=10),
            actions=[
                ft.TextButton("Annuler", on_click=lambda _: setattr(dialog, 'open', False) or page.update()),
                ft.ElevatedButton("Rejeter", bgcolor=Colors.ERROR, color=Colors.TEXT_ON_DARK, on_click=on_confirm),
            ],
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def on_validate(e):
        try:
            auth.api.valider_signalement(signalement_id)
            sb = ft.SnackBar(
                content=ft.Text("✅ Signalement validé. Le caveau est maintenant non exploitable.", color=Colors.TEXT_ON_DARK),
                bgcolor="#496042",
                duration=3000
            )
            page.snack_bar = sb
            sb.open = True
            page.update()
            page.go("/graves/signalements")
        except Exception as exc:
            error_text.value = f"Erreur de validation : {exc}"
            error_text.visible = True
            page.update()

    load_data()
    device = get_device_type(page.width or 1200)
    
    is_admin = auth.role.value in ["admin", "secretariat"]
    is_pending = sig_data.get("statut") == "en_attente"

    return ft.View(
        route="/graves/signalements/detail",
        controls=[
            ft.Row([
                ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: page.go("/graves/signalements")),
                ft.Text("Détail du signalement", style=heading_style(size=22)),
            ]),
            ft.Container(height=10),
            loading,
            error_text,
            ft.Container(
                content=ft.Column([
                    info_column,
                    ft.Container(height=20),
                    ft.Row([
                        ft.ElevatedButton(
                            "✅ Valider et rendre non exploitable",
                            icon=ft.Icons.CHECK_CIRCLE,
                            bgcolor="#496042",
                            color=Colors.TEXT_ON_DARK,
                            on_click=on_validate,
                            visible=(is_admin and is_pending)
                        ),
                        ft.ElevatedButton(
                            "❌ Rejeter le signalement",
                            icon=ft.Icons.CANCEL,
                            bgcolor=Colors.ERROR,
                            color=Colors.TEXT_ON_DARK,
                            on_click=lambda _: show_reject_dialog(),
                            visible=(is_admin and is_pending)
                        ),
                    ], spacing=10),
                ], spacing=0),
                padding=24,
                bgcolor="#FFFFFF",
                border_radius=12,
                expand=True,
            ),
        ],
        bgcolor=Colors.BACKGROUND,
        padding=24 if device == "desktop" else 16,
        scroll=ft.ScrollMode.AUTO,
    )