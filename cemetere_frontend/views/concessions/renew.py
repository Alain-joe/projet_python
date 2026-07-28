"""
views/concessions/renew.py — Renouvellement d'une concession existante.
Compatible Flet 0.86.0
"""
from __future__ import annotations
import flet as ft
from urllib.parse import urlparse, parse_qs
from core.auth import AuthState
from core.theme import Colors, get_device_type, heading_style


def build_concession_renewal_view(page: ft.Page, auth: AuthState) -> ft.View:
    query = parse_qs(urlparse(page.route).query)
    concession_id = query.get("concession_id", [None])[0]

    if not concession_id:
        return ft.View(route="/concessions/renewal", controls=[ft.Text("ID de concession manquant.")])

    loading = ft.ProgressRing(visible=True)
    error_text = ft.Text("", color=Colors.ERROR, size=13, visible=False)
    
    concession_data = {}
    
    type_field = ft.Dropdown(
        label="Nouveau type de concession *",
        border_radius=8,
        options=[
            ft.dropdown.Option("temporaire", "Temporaire"),
            ft.dropdown.Option("trentenaire", "Trentenaire (30 ans)"),
            ft.dropdown.Option("cinquantenaire", "Cinquantenaire (50 ans)"),
        ],
        value="temporaire",
    )
    
    duree_field = ft.TextField(
        label="Durée (années) *",
        border_radius=8,
        keyboard_type=ft.KeyboardType.NUMBER,
        visible=True,
    )
    
    montant_field = ft.TextField(
        label="Montant du renouvellement (FCFA)",
        border_radius=8,
        keyboard_type=ft.KeyboardType.NUMBER,
    )

    def on_type_change(e):
        if type_field.value in ["trentenaire", "cinquantenaire"]:
            duree_field.visible = False
            duree_field.value = ""
        else:
            duree_field.visible = True
        page.update()

    type_field.on_change = on_type_change

    def load_concession():
        loading.visible = True
        error_text.visible = False
        page.update()
        try:
            c_data = auth.api.get(f"/cemetery/concessions/{concession_id}")
            concession_data.update(c_data)
            montant_field.value = str(float(c_data.get("montant", 0)))
        except Exception as exc:
            error_text.value = f"Erreur de chargement : {exc}"
            error_text.visible = True
        finally:
            loading.visible = False
            page.update()

    def on_renew(e):
        if not type_field.value:
            error_text.value = "❌ Le type de concession est obligatoire."
            error_text.visible = True
            page.update()
            return
            
        if type_field.value == "temporaire" and not duree_field.value:
            error_text.value = "❌ La durée est obligatoire pour une concession temporaire."
            error_text.visible = True
            page.update()
            return

        try:
            payload = {
                "type_concession": type_field.value,
                "duree_annees": int(duree_field.value) if type_field.value == "temporaire" else None,
                "montant": float(montant_field.value) if montant_field.value else None,
            }
            auth.api.renew_concession(int(concession_id), payload)
            
            sb = ft.SnackBar(content=ft.Text("✅ Concession renouvelée ! Une facture a été générée."), bgcolor="#496042")
            page.snack_bar = sb
            sb.open = True
            page.update()
            page.go(f"/concessions/detail?concession_id={concession_id}")
        except Exception as exc:
            error_text.value = f"❌ Échec du renouvellement : {exc}"
            error_text.visible = True
            page.update()

    load_concession()
    device = get_device_type(page.width or 1200)

    return ft.View(
        route="/concessions/renewal",
        controls=[
            ft.Row([
                ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: page.go(f"/concessions/detail?concession_id={concession_id}")),
                ft.Text("Renouvellement de Concession", style=heading_style(size=22)),
            ]),
            ft.Container(height=10),
            loading,
            error_text,
            ft.Container(
                content=ft.Column([
                    ft.Text("Concession actuelle", style=heading_style(size=16)),
                    ft.Container(height=10),
                    ft.Row([ft.Text("Caveau :", weight=ft.FontWeight.W_600), ft.Text(concession_data.get("grave_code", "N/A"))]),
                    ft.Row([ft.Text("Client :", weight=ft.FontWeight.W_600), ft.Text(concession_data.get("client_username", "N/A"))]),
                    ft.Row([ft.Text("Date de fin actuelle :", weight=ft.FontWeight.W_600), ft.Text(concession_data.get("date_fin", "Perpétuelle"))]),
                    ft.Divider(),
                    ft.Text("Nouvelles conditions", style=heading_style(size=16)),
                    ft.Container(height=10),
                    type_field,
                    duree_field,
                    montant_field,
                    ft.Container(height=20),
                    ft.ElevatedButton(
                        "Valider le renouvellement",
                        bgcolor=Colors.PRIMARY,
                        color=Colors.TEXT_ON_DARK,
                        icon=ft.Icons.AUTORENEW,
                        width=300,
                        on_click=on_renew,
                    ),
                ], spacing=12),
                padding=24,
                bgcolor=Colors.SURFACE,
                border_radius=12,
                width=600 if device == "desktop" else None,
            ),
        ],
        bgcolor=Colors.BACKGROUND,
        padding=24 if device == "desktop" else 16,
        scroll=ft.ScrollMode.AUTO,
    )