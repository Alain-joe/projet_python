"""
views/concessions/renewal.py — Formulaire de renouvellement.
Compatible Flet 0.86.0
"""
from __future__ import annotations
import asyncio
import flet as ft
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta
from core.auth import AuthState
from core.api import ApiError
from core.theme import Colors, get_device_type, heading_style

def build_concession_renewal_view(page: ft.Page, auth: AuthState) -> ft.View:
    query = parse_qs(urlparse(page.route).query)
    concession_id = query.get("concession_id", [None])[0]

    if not concession_id:
        return ft.View(route="/concessions/renewal", controls=[ft.Text("ID manquant.")])

    concession = {}
    loading = ft.ProgressRing(visible=True)
    error_text = ft.Text("", color=Colors.ERROR, size=13, visible=False)
    success_text = ft.Text("", color=Colors.PRIMARY, size=13, visible=False)
    submit_loading = ft.ProgressRing(visible=False, width=20, height=20)

    duree_dropdown = ft.Dropdown(
        label="Durée du renouvellement",
        options=[
            ft.dropdown.Option("5", "5 ans"),
            ft.dropdown.Option("10", "10 ans"),
            ft.dropdown.Option("15", "15 ans"),
            ft.dropdown.Option("custom", "Personnalisé"),
        ],
        value="5", border_radius=12, filled=True, bgcolor=Colors.BACKGROUND,
    )
    
    custom_duree_field = ft.TextField(
        label="Durée personnalisée (en années)", keyboard_type=ft.KeyboardType.NUMBER,
        border_radius=12, filled=True, bgcolor=Colors.BACKGROUND, visible=False,
    )

    recap_text = ft.Text("", size=14, color=Colors.NEUTRAL, weight=ft.FontWeight.W_600)

    async def _load_data() -> None:
        await asyncio.sleep(0.1)
        loading.visible = True
        page.update()
        try:
            c_data = await auth.api.get_async(f"/cemetery/concessions/{concession_id}")
            concession.update(c_data)
            update_recap()
        except Exception as exc:
            error_text.value = f"Erreur : {exc}"
            error_text.visible = True
        finally:
            loading.visible = False
            page.update()

    def update_recap() -> None:
        if not concession: return
        duree_val = custom_duree_field.value if duree_dropdown.value == "custom" else duree_dropdown.value
        try:
            duree = int(duree_val) if duree_val else 0
        except ValueError:
            duree = 0

        if duree > 0 and concession.get("date_fin"):
            try:
                current_end = datetime.strptime(concession["date_fin"], "%Y-%m-%d").date()
                new_end = current_end + timedelta(days=duree * 365)
                recap_text.value = f"Nouvelle date de fin : {new_end.strftime('%d/%m/%Y')} | Coût : {float(concession.get('montant', 0)):,.0f} FCFA".replace(",", " ")
                recap_text.visible = True
            except Exception:
                recap_text.visible = False
        else:
            recap_text.visible = False
        page.update()

    def on_duree_change(e) -> None:
        custom_duree_field.visible = (duree_dropdown.value == "custom")
        if not custom_duree_field.visible: custom_duree_field.value = ""
        update_recap()

    duree_dropdown.on_change = on_duree_change
    custom_duree_field.on_change = lambda _: update_recap()

    def submit_renewal(e) -> None:
        error_text.visible = False
        duree_val = custom_duree_field.value if duree_dropdown.value == "custom" else duree_dropdown.value
        try:
            duree_annees = int(duree_val)
            if duree_annees <= 0: raise ValueError
        except (ValueError, TypeError):
            error_text.value = "Veuillez entrer une durée valide."
            error_text.visible = True
            page.update()
            return

        submit_loading.visible = True
        page.update()

        try:
            auth.api.put(f"/cemetery/concessions/{concession_id}/renew", json={"duree_annees": duree_annees})
            success_text.value = "✅ Concession renouvelée avec succès."
            success_text.visible = True
            page.update()
            import time; time.sleep(1.5)
            page.go(f"/concessions/detail?concession_id={concession_id}")
        except Exception as exc:
            error_text.value = f"Échec : {exc}"
            error_text.visible = True
        finally:
            submit_loading.visible = False
            page.update()

    page.run_task(_load_data)
    device = get_device_type(page.window.width or 1200)

    return ft.View(
        route="/concessions/renewal",
        controls=[
            ft.Row([
                ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: page.go("/concessions")),
                ft.Text("Renouveler la Concession", style=heading_style(size=22)),
            ]),
            ft.Container(height=20),
            loading,
            ft.Container(
                content=ft.Column([
                    ft.Text(f"Caveau : {concession.get('grave_code', 'N/A')}", weight=ft.FontWeight.W_600, size=16),
                    ft.Divider(height=20, color=Colors.BORDER),
                    ft.Text("Paramètres du renouvellement", style=heading_style(size=16)),
                    ft.Container(height=10),
                    duree_dropdown,
                    ft.Container(height=10),
                    custom_duree_field,
                    ft.Container(height=15),
                    recap_text,
                    ft.Container(height=20),
                    error_text, success_text,
                    ft.Row([
                        ft.ElevatedButton("Confirmer le renouvellement", icon=ft.Icons.CHECK_CIRCLE, bgcolor=Colors.PRIMARY, color=Colors.TEXT_ON_DARK, width=300, on_click=submit_renewal),
                        submit_loading,
                    ], alignment=ft.MainAxisAlignment.CENTER),
                ], spacing=0),
                padding=24, bgcolor="#FFFFFF", border_radius=12, expand=True,
            ),
        ],
        bgcolor=Colors.BACKGROUND,
        padding=16 if device == "mobile" else 32,
    )