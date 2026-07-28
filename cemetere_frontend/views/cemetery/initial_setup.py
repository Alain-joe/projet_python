"""
views/cemetery/initial_setup.py — Étape 1 : Informations du cimetière.
Compatible Flet 0.86.0
"""
from __future__ import annotations
import flet as ft
from urllib.parse import urlencode
from core.auth import AuthState
from core.theme import Colors, get_device_type, heading_style
from data.villes_congo import VILLES_CONGO, VILLES_COORDS


def build_initial_setup_view(page: ft.Page, auth: AuthState) -> ft.View:
    if not hasattr(page, "setup_data"):
        page.setup_data = {}

    existing_config = None
    try:
        config = auth.api.get("/cemetery/config/")
        if isinstance(config, dict) and "id" in config:
            existing_config = config
    except Exception:
        pass

    name_field = ft.TextField(label="Nom du cimetière *", border_radius=8, value=existing_config.get("name", "") if existing_config else "")
    
    city_field = ft.Dropdown(
        label="Ville *", border_radius=8,
        options=[ft.dropdown.Option(v) for v in VILLES_CONGO],
        value=existing_config.get("city", "") if existing_config else None,
    )
    
    address_field = ft.TextField(label="Adresse / Quartier *", border_radius=8, value=existing_config.get("address", "") if existing_config else "")

    lat_field = ft.TextField(label="Latitude *", border_radius=8, keyboard_type=ft.KeyboardType.NUMBER, value=str(existing_config.get("latitude", "")) if existing_config else "")
    lng_field = ft.TextField(label="Longitude *", border_radius=8, keyboard_type=ft.KeyboardType.NUMBER, value=str(existing_config.get("longitude", "")) if existing_config else "")

    longueur_field = ft.TextField(label="Longueur totale (m) *", value=str(existing_config.get("longueur_totale", 100)) if existing_config else "100", border_radius=8, keyboard_type=ft.KeyboardType.NUMBER)
    largeur_field = ft.TextField(label="Largeur totale (m) *", value=str(existing_config.get("largeur_totale", 100)) if existing_config else "100", border_radius=8, keyboard_type=ft.KeyboardType.NUMBER)
    
    grave_length_field = ft.TextField(label="Longueur caveau (m)", value=str(existing_config.get("grave_length", 2.5)) if existing_config else "2.5", border_radius=8, keyboard_type=ft.KeyboardType.NUMBER)
    grave_width_field = ft.TextField(label="Largeur caveau (m)", value=str(existing_config.get("grave_width", 1.2)) if existing_config else "1.2", border_radius=8, keyboard_type=ft.KeyboardType.NUMBER)
    espacement_field = ft.TextField(label="Espacement (m)", value=str(existing_config.get("espacement_caveaux", 0.5)) if existing_config else "0.5", border_radius=8, keyboard_type=ft.KeyboardType.NUMBER)

    error_text = ft.Text("", color=Colors.ERROR, size=13, visible=False)

    def on_city_change(e):
        if city_field.value and city_field.value in VILLES_COORDS:
            coords = VILLES_COORDS[city_field.value]
            lat_field.value = str(coords["lat"])
            lng_field.value = str(coords["lng"])
            page.update()

    city_field.on_change = on_city_change

    def on_next(e):
        if not all([name_field.value, city_field.value, address_field.value, lat_field.value, lng_field.value, longueur_field.value, largeur_field.value]):
            error_text.value = "❌ Veuillez remplir tous les champs obligatoires (*)."
            error_text.visible = True
            page.update()
            return

        try:
            # On stocke les données pour les passer à l'étape 2 via l'URL
            page.setup_data = {
                "latitude": float(lat_field.value.strip()),
                "longitude": float(lng_field.value.strip()),
                "longueur_totale": float(longueur_field.value.strip()),
                "largeur_totale": float(largeur_field.value.strip()),
                "grave_length": float(grave_length_field.value.strip()),
                "grave_width": float(grave_width_field.value.strip()),
                "espacement_caveaux": float(espacement_field.value.strip()),
                "name": name_field.value.strip(),
                "city": city_field.value,
                "address": address_field.value.strip(),
                "total_area": float(longueur_field.value.strip()) * float(largeur_field.value.strip()),
                "non_exploitable_area": 0.0,
            }
            error_text.visible = False
            page.go("/cimetiere/alleys")
        except ValueError:
            error_text.value = "❌ Valeurs numériques invalides."
            error_text.visible = True
            page.update()

    device = get_device_type(page.width or 1200)

    return ft.View(
        route="/cimetiere/setup",
        controls=[
            ft.Row([ft.Text("Configuration du Cimetière", style=heading_style(size=24)), ft.Container(expand=True), ft.ElevatedButton("← Retour", on_click=lambda _: page.go("/dashboard/admin"))]),
            ft.Container(height=10),
            ft.Text("Étape 1/2 : Informations générales", size=14, color=Colors.NEUTRAL),
            ft.Container(height=20),
            error_text,
            ft.Container(
                content=ft.Column([
                    ft.Row([name_field, city_field], spacing=16),
                    address_field,
                    ft.Divider(),
                    ft.Text("📍 Position GPS", weight=ft.FontWeight.W_600, size=14),
                    ft.Row([lat_field, lng_field], spacing=16),
                    ft.Divider(),
                    ft.Text("Dimensions", weight=ft.FontWeight.W_600, size=14),
                    ft.Row([longueur_field, largeur_field], spacing=16),
                    ft.Divider(),
                    ft.Text("Dimensions des caveaux", weight=ft.FontWeight.W_600, size=14),
                    ft.Row([grave_length_field, grave_width_field, espacement_field], spacing=16),
                    ft.Container(height=20),
                    ft.ElevatedButton(content=ft.Row([ft.Text("Suivant : Dessiner sur la carte"), ft.Icon(ft.Icons.MAP)]), bgcolor=Colors.PRIMARY, color=Colors.TEXT_ON_DARK, width=300, on_click=on_next),
                ], spacing=12),
                padding=24, bgcolor=Colors.SURFACE, border_radius=12, width=600 if device == "desktop" else None,
            ),
        ],
        bgcolor=Colors.BACKGROUND, padding=24 if device == "desktop" else 16, scroll=ft.ScrollMode.AUTO,
    )