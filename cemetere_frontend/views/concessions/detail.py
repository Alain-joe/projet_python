"""
views/concessions/detail.py — Fiche détaillée d'une concession.
Compatible Flet 0.86.0
CORRECTION : Ajout du champ motif pour la résiliation et correction Flet 0.86 (page.dialog)
"""
from __future__ import annotations
import asyncio
import flet as ft
from urllib.parse import urlparse, parse_qs
from core.auth import AuthState
from core.theme import Colors, get_device_type, heading_style


def build_concession_detail_view(page: ft.Page, auth: AuthState) -> ft.View:
    query = parse_qs(urlparse(page.route).query)
    concession_id = query.get("concession_id", [None])[0]

    if not concession_id:
        return ft.View(route="/concessions/detail", controls=[ft.Text("ID de concession manquant.")])

    concession = {}
    history = []
    loading = ft.ProgressRing(visible=True)
    error_text = ft.Text("", color=Colors.ERROR, size=13, visible=False)
    
    info_column = ft.Column(spacing=8)
    history_column = ft.Column(spacing=8)

    async def _load_data() -> None:
        await asyncio.sleep(0.1)
        loading.visible = True
        error_text.visible = False
        page.update()
        
        try:
            c_data = auth.api.get(f"/cemetery/concessions/{concession_id}")
            concession.update(c_data)
            
            h_data = auth.api.get(f"/cemetery/concessions/{concession_id}/historique")
            history.extend(h_data if isinstance(h_data, list) else [])
            
            render_detail()
        except Exception as exc:
            error_text.value = f"Erreur de chargement : {exc}"
            error_text.visible = True
        finally:
            loading.visible = False
            page.update()

    def render_detail() -> None:
        status_color = "#496042" if concession.get("status") == "active" else "#8A4343"
        
        info_column.controls = [
            ft.Row([
                ft.Text(f"Concession N° {concession.get('id')}", style=heading_style(size=18)),
                ft.Container(
                    content=ft.Text(concession.get("status", "unknown").upper(), size=12, color=Colors.TEXT_ON_DARK),
                    bgcolor=status_color, 
                    padding=ft.Padding(left=8, top=4, right=8, bottom=4), 
                    border_radius=12,
                )
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(),
            ft.Row([ft.Text("Caveau :", weight=ft.FontWeight.W_600), ft.Text(concession.get("grave_code", "N/A"))]),
            ft.Row([ft.Text("Client :", weight=ft.FontWeight.W_600), ft.Text(concession.get("client_username", "N/A"))]),
            ft.Row([ft.Text("Type :", weight=ft.FontWeight.W_600), ft.Text(concession.get("type_concession", "N/A").capitalize())]),
            ft.Row([ft.Text("Début :", weight=ft.FontWeight.W_600), ft.Text(concession.get("date_debut", "N/A"))]),
            ft.Row([ft.Text("Fin :", weight=ft.FontWeight.W_600), ft.Text(concession.get("date_fin", "Perpétuelle"))]),
            ft.Row([ft.Text("Montant :", weight=ft.FontWeight.W_600), ft.Text(f"{float(concession.get('montant', 0)):,.0f} FCFA".replace(",", " "))]),
        ]

        history_column.controls.clear()
        if not history:
            history_column.controls.append(ft.Text("Aucun renouvellement enregistré.", color=Colors.NEUTRAL, italic=True))
        else:
            for h in history:
                history_column.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Text(f"Renouvelé de {h.get('duree_extension_annees')} ans", weight=ft.FontWeight.W_600),
                            ft.Text(f"Nouvelle fin : {h.get('nouvelle_date_fin')} | Montant : {float(h.get('montant_paye', 0)):,.0f} FCFA".replace(",", " "), size=12, color=Colors.NEUTRAL),
                        ], spacing=2),
                        padding=12, 
                        bgcolor="#F5F3EE", 
                        border_radius=8,
                    )
                )

    async def download_contrat() -> None:
        try:
            token = auth.access_token or ""
            url = f"http://127.0.0.1:8000/api/cemetery/concessions/{concession_id}/contrat/download?token={token}"
            await page.launch_url(url)
        except Exception as e:
            print(f"Erreur launch_url: {e}")
            error_text.value = f"Erreur téléchargement : {e}"
            error_text.visible = True
            page.update()

    def send_contrat_email() -> None:
        try:
            auth.api.post(f"/cemetery/concessions/{concession_id}/send-contrat")
            sb = ft.SnackBar(content=ft.Text("✅ Contrat envoyé par email."), bgcolor=Colors.PRIMARY)
            page.snack_bar = sb
            sb.open = True
            page.update()
        except Exception as exc:
            error_text.value = f"Erreur envoi : {exc}"
            error_text.visible = True
            page.update()

    # ✅ CORRECTION : Ajout du champ motif obligatoire pour la résiliation
    def resiliate_concession() -> None:
        motif_field = ft.TextField(label="Motif de la résiliation *", multiline=True, min_lines=3, border_radius=8)
        error_msg = ft.Text("", color=Colors.ERROR, size=12)

        def on_confirm(e):
            if not motif_field.value.strip():
                error_msg.value = "Le motif est obligatoire."
                error_msg.update()
                return
            try:
                auth.api.resiliate_concession(concession_id, motif_field.value.strip())
                dialog.open = False
                page.update()
                sb = ft.SnackBar(content=ft.Text("Concession résiliée."), bgcolor=Colors.ERROR)
                page.snack_bar = sb
                sb.open = True
                page.update()
                page.go("/concessions")
            except Exception as exc:
                error_msg.value = f"Erreur résiliation : {exc}"
                error_msg.update()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirmer la résiliation", weight=ft.FontWeight.BOLD),
            content=ft.Column([
                ft.Text("Cette action libérera le caveau et ne pourra pas être annulée."),
                motif_field,
                error_msg
            ], spacing=10),
            actions=[
                ft.TextButton("Annuler", on_click=lambda _: setattr(dialog, 'open', False) or page.update()),
                ft.ElevatedButton("Confirmer", bgcolor=Colors.ERROR, color=Colors.TEXT_ON_DARK, on_click=on_confirm),
            ],
        )
        # ✅ CORRECTION FLET 0.86
        page.dialog = dialog
        dialog.open = True
        page.update()

    page.run_task(_load_data)
    device = get_device_type(page.width or 1200) # ✅ CORRECTION: page.width

    return ft.View(
        route="/concessions/detail",
        controls=[
            ft.Row([
                ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: page.go("/concessions")),
                ft.Text("Détail de la Concession", style=heading_style(size=22)),
            ]),
            ft.Container(height=10),
            loading,
            error_text,
            ft.Container(
                content=ft.Column([
                    ft.Text("Informations générales", style=heading_style(size=16)),
                    ft.Container(height=10),
                    info_column,
                    ft.Container(height=20),
                    ft.Text("Historique des renouvellements", style=heading_style(size=16)),
                    ft.Container(height=10),
                    history_column,
                    ft.Container(height=20),
                    ft.Row([
                        ft.ElevatedButton(
                            "Télécharger Contrat", 
                            icon=ft.Icons.DOWNLOAD, 
                            on_click=lambda _: page.run_task(download_contrat)
                        ),
                        ft.ElevatedButton(
                            "Renvoyer par Email", 
                            icon=ft.Icons.EMAIL, 
                            on_click=lambda _: send_contrat_email()
                        ),
                    ], spacing=10),
                    ft.Row([
                        ft.ElevatedButton(
                            "Renouveler", 
                            icon=ft.Icons.AUTORENEW, 
                            bgcolor="#1A2B4C", 
                            color=Colors.TEXT_ON_DARK, 
                            on_click=lambda _: page.go(f"/concessions/renewal?concession_id={concession_id}"),
                            visible=(concession.get("status") == "active")
                        ),
                        ft.ElevatedButton(
                            "Résilier", 
                            icon=ft.Icons.CANCEL, 
                            bgcolor=Colors.ERROR, 
                            color=Colors.TEXT_ON_DARK, 
                            on_click=resiliate_concession,
                            visible=(concession.get("status") == "active")
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
        padding=16 if device == "mobile" else 32,
    )