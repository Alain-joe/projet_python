"""
views/concessions/create.py — Création d'une concession depuis une réservation validée.
Compatible Flet 0.86.0
"""
from __future__ import annotations
import flet as ft
from urllib.parse import urlparse, parse_qs
from core.auth import AuthState
from core.theme import Colors, get_device_type, heading_style
from core.api import Endpoints


def build_concession_create_view(page: ft.Page, auth: AuthState) -> ft.View:
    query = parse_qs(urlparse(page.route).query)
    reservation_id = query.get("reservation_id", [None])[0]

    loading = ft.ProgressRing(visible=True)
    error_text = ft.Text("", color=Colors.ERROR, size=13, visible=False)
    
    reservation_data = {}
    
    # Champs du formulaire
    type_field = ft.Dropdown(
        label="Type de concession *",
        border_radius=8,
        options=[
            ft.dropdown.Option("temporaire", "Temporaire"),
            ft.dropdown.Option("trentenaire", "Trentenaire (30 ans)"),
            ft.dropdown.Option("cinquantenaire", "Cinquantenaire (50 ans)"),
            ft.dropdown.Option("perpetuelle", "Perpétuelle"),
        ],
        value="temporaire",
    )
    
    duree_field = ft.TextField(
        label="Durée (années) *",
        border_radius=8,
        keyboard_type=ft.KeyboardType.NUMBER,
        visible=True,
    )
    
    obs_field = ft.TextField(
        label="Observations",
        border_radius=8,
        multiline=True,
        min_lines=2,
    )

    def on_type_change(e):
        if type_field.value in ["trentenaire", "cinquantenaire", "perpetuelle"]:
            duree_field.visible = False
            duree_field.value = ""
        else:
            duree_field.visible = True
        page.update()

    type_field.on_change = on_type_change

    def load_reservation():
        loading.visible = True
        error_text.visible = False
        page.update()
        try:
            if reservation_id:
                res = auth.api.get(Endpoints.reservation_details(int(reservation_id)))
                reservation_data.update(res)
            else:
                error_text.value = "Aucune réservation sélectionnée."
                error_text.visible = True
        except Exception as exc:
            error_text.value = f"Erreur de chargement : {exc}"
            error_text.visible = True
        finally:
            loading.visible = False
            page.update()

    def on_create(e):
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
                "reservation_id": int(reservation_id),
                "type_concession": type_field.value,
                "duree_annees": int(duree_field.value) if type_field.value == "temporaire" else None,
                "observations": obs_field.value.strip(),
            }
            auth.api.post(Endpoints.CONCESSIONS_FROM_RESERVATION, json=payload)
            
            sb = ft.SnackBar(content=ft.Text("✅ Concession créée avec succès !"), bgcolor="#496042")
            page.snack_bar = sb
            sb.open = True
            page.update()
            page.go("/concessions")
        except Exception as exc:
            error_text.value = f"❌ Échec de la création : {exc}"
            error_text.visible = True
            page.update()

    load_reservation()
    device = get_device_type(page.width or 1200)

    return ft.View(
        route="/concessions/nouvelle",
        controls=[
            ft.Row([
                ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: page.go("/concessions")),
                ft.Text("Nouvelle Concession", style=heading_style(size=22)),
            ]),
            ft.Container(height=10),
            loading,
            error_text,
            ft.Container(
                content=ft.Column([
                    ft.Text("Informations de la réservation", style=heading_style(size=16)),
                    ft.Container(height=10),
                    ft.Row([ft.Text("Caveau :", weight=ft.FontWeight.W_600), ft.Text(reservation_data.get("grave_code", "N/A"))]),
                    ft.Row([ft.Text("Client :", weight=ft.FontWeight.W_600), ft.Text(reservation_data.get("client_username", "N/A"))]),
                    ft.Row([ft.Text("Montant payé :", weight=ft.FontWeight.W_600), ft.Text(f"{float(reservation_data.get('montant', 0)):,.0f} FCFA".replace(",", " "))]),
                    ft.Divider(),
                    ft.Text("Détails de la concession", style=heading_style(size=16)),
                    ft.Container(height=10),
                    type_field,
                    duree_field,
                    obs_field,
                    ft.Container(height=20),
                    ft.ElevatedButton(
                        "Valider et créer la concession",
                        bgcolor=Colors.PRIMARY,
                        color=Colors.TEXT_ON_DARK,
                        icon=ft.Icons.CHECK,
                        width=300,
                        on_click=on_create,
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