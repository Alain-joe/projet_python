"""
views/finance/pending_virements.py — Liste des virements bancaires en attente de confirmation.
Compatible Flet 0.86.0
"""
from __future__ import annotations
import flet as ft
from datetime import datetime

from core.auth import AuthState
from core.api import ApiError
from core.theme import Colors, get_device_type, heading_style
from core.ui_utils import show_overlay


def build_pending_virements_view(page: ft.Page, auth: AuthState) -> ft.View:
    virements = []
    loading = ft.ProgressRing(visible=True)
    error_text = ft.Text("", color=Colors.ERROR, size=13, visible=False)
    virements_container = ft.Column(spacing=10)

    def load_virements() -> None:
        loading.visible = True
        error_text.visible = False
        page.update()

        try:
            data = auth.api.get_virements_en_attente()
            virements.clear()
            if isinstance(data, list):
                virements.extend(data)
            elif isinstance(data, dict):
                virements.extend(data.get("results", data.get("items", [])))
            render_virements()
        except ApiError as exc:
            error_text.value = f"Erreur de chargement : {exc.message}"
            error_text.visible = True
        except Exception:
            error_text.value = "Impossible de contacter le serveur."
            error_text.visible = True
        finally:
            loading.visible = False
            page.update()

    def render_virements() -> None:
        virements_container.controls.clear()
        
        if not virements:
            virements_container.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.CHECK_CIRCLE, size=60, color="#496042"),
                        ft.Container(height=10),
                        ft.Text("Aucun virement en attente de confirmation.", size=16, color=Colors.NEUTRAL, text_align=ft.TextAlign.CENTER),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=40,
                    alignment=ft.Alignment(0.5, 0.5),
                )
            )
        else:
            for v in virements:
                virements_container.controls.append(build_virement_card(v))
        
        page.update()

    def build_virement_card(v: dict) -> ft.Control:
        """Construit une carte pour un virement en attente"""
        facture_numero = v.get("facture_numero", "N/A")
        client = v.get("client_username", "Inconnu")
        montant = float(v.get("montant", 0))
        reference = v.get("reference", "N/A")
        date_str = str(v.get("date_paiement", ""))[:10] if v.get("date_paiement") else "Date inconnue"
        paiement_id = v.get("id")

        def on_confirmer(e):
            """Confirme le virement après demande de confirmation"""
            def close_dialog(_):
                dialog.open = False
                page.update()

            def on_confirm_click(_):
                try:
                    auth.api.confirmer_virement(paiement_id)
                    close_dialog(None)
                    show_overlay(page, ft.SnackBar(
                        content=ft.Text(f"✅ Virement {reference} confirmé avec succès !", color=Colors.TEXT_ON_DARK),
                        bgcolor="#496042",
                    ))
                    load_virements()
                except ApiError as exc:
                    close_dialog(None)
                    show_overlay(page, ft.SnackBar(
                        content=ft.Text(f"❌ Erreur : {exc.message}", color=Colors.TEXT_ON_DARK),
                        bgcolor=Colors.ERROR,
                    ))

            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("Confirmer le virement", weight=ft.FontWeight.BOLD),
                content=ft.Column([
                    ft.Text(f"Êtes-vous sûr d'avoir reçu le virement de {montant:,.0f} FCFA".replace(",", " ")),
                    ft.Text(f"Référence : {reference}", size=13, color=Colors.NEUTRAL),
                    ft.Text(f"Client : {client}", size=13, color=Colors.NEUTRAL),
                    ft.Container(height=10),
                    ft.Text("⚠️ Cette action est irréversible. Le paiement sera marqué comme validé et la facture mise à jour.", size=12, color=Colors.ERROR),
                ], spacing=8),
                actions=[
                    ft.TextButton("Annuler", on_click=close_dialog),
                    ft.ElevatedButton(
                        "✅ Confirmer la réception",
                        bgcolor="#496042",
                        color=Colors.TEXT_ON_DARK,
                        on_click=on_confirm_click,
                    ),
                ],
            )
            page.overlay.append(dialog)
            dialog.open = True
            page.update()

        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Column([
                        ft.Text(f"Facture #{facture_numero}", weight=ft.FontWeight.W_600, size=16),
                        ft.Text(f"Client : {client}", size=13, color=Colors.NEUTRAL),
                        ft.Text(f"Référence : {reference}", size=12, color=Colors.NEUTRAL),
                        ft.Text(f"Date : {date_str}", size=11, color=Colors.NEUTRAL, italic=True),
                    ], spacing=4, expand=True),
                    ft.Container(
                        content=ft.Column([
                            ft.Text("En attente", size=11, color=Colors.TEXT_ON_DARK),
                            ft.Text(f"{montant:,.0f} FCFA".replace(",", " "), size=18, weight=ft.FontWeight.BOLD, color=Colors.TEXT_ON_DARK),
                        ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        bgcolor="#F9A825",
                        padding=ft.Padding(left=12, top=8, right=12, bottom=8),
                        border_radius=12,
                    ),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Divider(height=10, color=Colors.BORDER),
                ft.ElevatedButton(
                    content=ft.Row([
                        ft.Icon(ft.Icons.CHECK_CIRCLE, size=18, color=Colors.TEXT_ON_DARK),
                        ft.Text("Confirmer la réception du virement", color=Colors.TEXT_ON_DARK, weight=ft.FontWeight.W_600),
                    ], spacing=6),
                    style=ft.ButtonStyle(bgcolor="#496042"),
                    width=float("inf"),
                    on_click=on_confirmer,
                ),
            ], spacing=8),
            padding=16,
            bgcolor="#FFFFFF",
            border_radius=10,
            border=ft.Border(
                left=ft.BorderSide(4, "#F9A825"),
                right=ft.BorderSide(1, Colors.BORDER),
                top=ft.BorderSide(1, Colors.BORDER),
                bottom=ft.BorderSide(1, Colors.BORDER),
            ),
        )

    load_virements()
    device = get_device_type(page.window.width or 1200)

    return ft.View(
        route="/finance/virements-en-attente",
        controls=[
            ft.Row([
                ft.IconButton(ft.Icons.ARROW_BACK, tooltip="Retour aux finances", on_click=lambda _: page.go("/finance")),
                ft.Text("Virements en attente de confirmation", style=heading_style(size=22)),
            ]),
            ft.Container(height=10),
            ft.Text(
                "Liste des paiements par virement bancaire qui attendent votre confirmation de réception.",
                size=14, color=Colors.NEUTRAL,
            ),
            ft.Container(height=20),
            loading,
            error_text,
            virements_container,
        ],
        bgcolor=Colors.BACKGROUND,
        padding=24 if device == "desktop" else 16,
        scroll=ft.ScrollMode.AUTO,
    )