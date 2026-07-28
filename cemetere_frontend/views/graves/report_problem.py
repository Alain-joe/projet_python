"""
views/graves/report_problem.py — Formulaire de signalement d'un problème sur un caveau.
Compatible Flet 0.86.3
CORRECTION : Redirection asynchrone simple sans page.views.clear() pour éviter la corruption de session.
"""
from __future__ import annotations
import flet as ft
from urllib.parse import urlparse, parse_qs
import asyncio

from core.auth import AuthState
from core.api import ApiError
from core.theme import Colors, get_device_type, heading_style


def build_report_problem_view(page: ft.Page, auth: AuthState) -> ft.View:
    query = parse_qs(urlparse(page.route).query)
    grave_id_str = query.get("grave_id", [None])[0]
    grave_code = query.get("grave_code", ["Inconnu"])[0]

    if not grave_id_str or str(grave_id_str).lower() == "undefined":
        page.go("/graves")
        return ft.View(route="/graves/signaler", controls=[])
    
    try:
        grave_id = int(grave_id_str)
    except ValueError:
        page.go("/graves")
        return ft.View(route="/graves/signaler", controls=[])

    motif_field = ft.TextField(
        label="Motif du problème *",
        border_radius=8,
        hint_text="Ex: Effondrement, fissures importantes, terrain instable..."
    )
    
    description_field = ft.TextField(
        label="Description détaillée",
        border_radius=8,
        multiline=True,
        min_lines=4,
        hint_text="Décrivez le problème constaté sur le terrain..."
    )
    
    photos_field = ft.TextField(
        label="Référence photo / URL (optionnel)",
        border_radius=8,
        hint_text="Lien vers la photo ou référence du dossier..."
    )

    error_text = ft.Text("", color=Colors.ERROR, size=13, visible=False)
    loading = ft.ProgressRing(visible=False, width=20, height=20)

    def on_submit(e):
        if not motif_field.value.strip():
            error_text.value = "❌ Le motif du problème est obligatoire."
            error_text.visible = True
            page.update()
            return

        loading.visible = True
        error_text.visible = False
        page.update()

        try:
            auth.api.signaler_probleme_caveau(
                grave_id=grave_id,
                motif=motif_field.value.strip(),
                description=description_field.value.strip(),
                photos=[photos_field.value.strip()] if photos_field.value.strip() else None
            )
            
            sb = ft.SnackBar(
                content=ft.Text("✅ Signalement envoyé avec succès. En attente de validation.", color=Colors.TEXT_ON_DARK),
                bgcolor="#496042",
                duration=2000
            )
            page.snack_bar = sb
            sb.open = True
            page.update()
            
            # ✅ CORRECTION : Redirection simple et sûre après un court délai
            async def delayed_redirect():
                await asyncio.sleep(1.5)
                page.go("/graves/signalements")
            
            page.run_task(delayed_redirect)

        except ApiError as exc:
            error_text.value = f"❌ Échec : {exc.message}"
            error_text.visible = True
            loading.visible = False
            page.update()
        except Exception as exc:
            error_text.value = f"❌ Erreur inattendue : {str(exc)}"
            error_text.visible = True
            loading.visible = False
            page.update()

    submit_button = ft.ElevatedButton(
        content=ft.Row([
            ft.Icon(ft.Icons.SEND, color=Colors.TEXT_ON_DARK),
            ft.Text("Envoyer le signalement", color=Colors.TEXT_ON_DARK, weight=ft.FontWeight.BOLD)
        ], spacing=5),
        style=ft.ButtonStyle(bgcolor=Colors.PRIMARY),
        width=float("inf"),
        height=50,
        on_click=on_submit
    )

    width = getattr(page, 'window', page).width if hasattr(page, 'window') else (getattr(page, 'width', 1200) or 1200)
    device = get_device_type(width)

    return ft.View(
        route="/graves/signaler",
        controls=[
            ft.Row([
                ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: page.go("/graves")),
                ft.Text("Signaler un problème", style=heading_style(size=22)),
            ]),
            ft.Container(height=10),
            ft.Text(f"Caveau concerné : {grave_code}", size=14, color=Colors.NEUTRAL, weight=ft.FontWeight.W_600),
            ft.Container(height=20),
            ft.Container(
                content=ft.Column([
                    motif_field,
                    ft.Container(height=10),
                    description_field,
                    ft.Container(height=10),
                    photos_field,
                    ft.Container(height=20),
                    error_text,
                    submit_button,
                    ft.Container(height=10),
                    loading,
                ], spacing=0),
                padding=24,
                bgcolor="#FFFFFF",
                border_radius=12,
                width=600 if device != "mobile" else None,
            ),
        ],
        bgcolor=Colors.BACKGROUND,
        padding=24 if device != "mobile" else 16,
        scroll=ft.ScrollMode.AUTO,
    )