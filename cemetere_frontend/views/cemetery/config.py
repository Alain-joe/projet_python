"""
views/cemetery/config.py — Configuration du cimetière (Admin uniquement).
Compatible Flet 0.86.0
"""
from __future__ import annotations
import flet as ft
from core.auth import AuthState
from core.api import ApiError, Endpoints
from core.theme import Colors, get_device_type, heading_style

def build_cemetery_config_view(page: ft.Page, auth: AuthState) -> ft.View:
    config_data = {}
    loading = ft.ProgressRing(visible=True)
    error_text = ft.Text("", color=Colors.ERROR, size=13, visible=False)
    success_text = ft.Text("", color=Colors.PRIMARY, size=13, visible=False)
    submit_loading = ft.ProgressRing(visible=False, width=20, height=20)

    # Champs du formulaire
    name_field = ft.TextField(label="Nom du cimetière", border_radius=12, filled=True, bgcolor=Colors.BACKGROUND)
    city_field = ft.TextField(label="Ville", border_radius=12, filled=True, bgcolor=Colors.BACKGROUND)
    address_field = ft.TextField(label="Adresse", border_radius=12, filled=True, bgcolor=Colors.BACKGROUND, multiline=True, min_lines=2)
    total_area_field = ft.TextField(label="Superficie totale (m²)", keyboard_type=ft.KeyboardType.NUMBER, border_radius=12, filled=True, bgcolor=Colors.BACKGROUND)
    grave_length_field = ft.TextField(label="Longueur standard caveau (m)", keyboard_type=ft.KeyboardType.NUMBER, border_radius=12, filled=True, bgcolor=Colors.BACKGROUND)
    grave_width_field = ft.TextField(label="Largeur standard caveau (m)", keyboard_type=ft.KeyboardType.NUMBER, border_radius=12, filled=True, bgcolor=Colors.BACKGROUND)

    def load_config() -> None:
        loading.visible = True
        page.update()
        try:
            data = auth.api.get(Endpoints.CEMETERY_CONFIG) # Assure-toi que cet endpoint existe dans core/api.py
            config_data.update(data)
            
            name_field.value = data.get("name", "")
            city_field.value = data.get("city", "")
            address_field.value = data.get("address", "")
            total_area_field.value = str(data.get("total_area", 0))
            grave_length_field.value = str(data.get("grave_length", 2.5))
            grave_width_field.value = str(data.get("grave_width", 1.2))
        except ApiError as exc:
            error_text.value = f"Erreur de chargement : {exc.message}"
            error_text.visible = True
        finally:
            loading.visible = False
            page.update()

    def save_config(e) -> None:
        error_text.visible = False
        success_text.visible = False
        submit_loading.visible = True
        page.update()

        payload = {
            "name": name_field.value,
            "city": city_field.value,
            "address": address_field.value,
            "total_area": float(total_area_field.value or 0),
            "grave_length": float(grave_length_field.value or 2.5),
            "grave_width": float(grave_width_field.value or 1.2),
        }

        try:
            auth.api.put(Endpoints.CEMETERY_CONFIG, json=payload) # Assure-toi que cet endpoint PUT existe
            success_text.value = "✅ Configuration enregistrée avec succès."
            success_text.visible = True
        except ApiError as exc:
            error_text.value = f"Échec : {exc.message}"
            error_text.visible = True
        finally:
            submit_loading.visible = False
            page.update()

    load_config()
    device = get_device_type(page.window.width or 1200)

    return ft.View(
        route="/cimetiere/config",
        controls=[
            ft.Text("Configuration du Cimetière", style=heading_style(size=22)),
            ft.Container(height=10),
            ft.Text("Modifiez les paramètres globaux du cimetière. Ces changements affecteront les calculs de capacité futurs.", size=14, color=Colors.NEUTRAL),
            ft.Container(height=20),
            loading,
            ft.Container(
                content=ft.Column([
                    name_field, ft.Container(height=10),
                    ft.Row([city_field, ft.Container(width=10)], expand=True), ft.Container(height=10),
                    address_field, ft.Container(height=10),
                    ft.Text("Dimensions et Superficie", style=heading_style(size=16)), ft.Container(height=10),
                    ft.Row([total_area_field, ft.Container(width=10)], expand=True), ft.Container(height=10),
                    ft.Row([grave_length_field, grave_width_field], spacing=10),
                    ft.Container(height=20),
                    error_text, success_text,
                    ft.Row([
                        ft.ElevatedButton(
                            "Enregistrer les modifications", 
                            icon=ft.Icons.SAVE, 
                            bgcolor=Colors.PRIMARY, 
                            color=Colors.TEXT_ON_DARK,
                            on_click=save_config
                        ),
                        submit_loading,
                    ]),
                ], spacing=0),
                padding=24,
                bgcolor="#FFFFFF",
                border_radius=12,
                expand=True,
            ),
        ],
        bgcolor=Colors.BACKGROUND,
        padding=16 if device == "mobile" else 32,
        scroll=ft.ScrollMode.AUTO,
    )