"""
views/graves/generate_grid.py — Génération automatique d'une grille de caveaux.
Compatible Flet 0.86.3
CORRECTION : Redirection automatique vers la carte après génération réussie.
"""
from __future__ import annotations
import flet as ft
import asyncio
from core.auth import AuthState
from core.api import ApiError
from core.theme import Colors, get_device_type, heading_style


_ERROR_TRANSLATIONS = {
    "field required": "Ce champ est obligatoire.",
    "value is not a valid integer": "Une valeur numérique entière est attendue.",
    "value is not a valid float": "Une valeur numérique est attendue.",
    "ensure this value is greater than": "La valeur doit être supérieure au minimum autorisé.",
    "ensure this value is less than or equal to": "La valeur dépasse le maximum autorisé.",
    "string does not match regex": "Le préfixe doit être une seule lettre majuscule (ex: A).",
    "not found": "Section introuvable.",
}


def _friendly_error(exc) -> str:
    raw = getattr(exc, "message", None) or str(exc)
    raw_lower = raw.lower()
    for needle, translation in _ERROR_TRANSLATIONS.items():
        if needle in raw_lower:
            return translation
    if any(w in raw_lower for w in ["veuillez", "obligatoire", "invalide", "erreur", "échec"]):
        return raw
    return "Une erreur est survenue lors de la génération. Vérifiez les champs et réessayez."


def build_generate_grid_view(page: ft.Page, auth: AuthState) -> ft.View:
    sections_data: list[dict] = []
    cemetery_config: dict = {}

    loading = ft.ProgressRing(visible=True)
    error_text = ft.Text("", color=Colors.ERROR, size=13, visible=False)
    success_text = ft.Text("", color=Colors.PRIMARY, size=13, visible=False)

    section_dropdown = ft.Dropdown(label="Section *", border_radius=8, options=[])

    rows_field = ft.TextField(label="Nombre de rangées *", value="5", border_radius=8, keyboard_type=ft.KeyboardType.NUMBER)
    cols_field = ft.TextField(label="Nombre de colonnes *", value="5", border_radius=8, keyboard_type=ft.KeyboardType.NUMBER)
    spacing_field = ft.TextField(label="Espacement entre caveaux (m)", value="3.0", border_radius=8, keyboard_type=ft.KeyboardType.NUMBER)
    prefix_field = ft.TextField(label="Préfixe des codes (1 lettre) *", value="A", border_radius=8, max_length=1)
    price_field = ft.TextField(label="Prix par caveau (FCFA) *", value="50000", border_radius=8, keyboard_type=ft.KeyboardType.NUMBER)

    start_lat_field = ft.TextField(label="Latitude de départ *", border_radius=8, keyboard_type=ft.KeyboardType.NUMBER)
    start_lng_field = ft.TextField(label="Longitude de départ *", border_radius=8, keyboard_type=ft.KeyboardType.NUMBER)

    def show_error(message: str) -> None:
        error_text.value = message
        error_text.visible = True
        success_text.visible = False
        page.update()

    def load_cemetery_config():
        """Récupère la configuration du cimetière pour pré-remplir les coordonnées par défaut."""
        try:
            data = auth.api.get("/cemetery/config")
            if isinstance(data, dict):
                cemetery_config.update(data)
                # Pré-remplir avec les coordonnées du cimetière si disponibles
                if data.get("latitude") and not start_lat_field.value:
                    start_lat_field.value = str(data["latitude"])
                if data.get("longitude") and not start_lng_field.value:
                    start_lng_field.value = str(data["longitude"])
        except Exception:
            pass

    def load_sections():
        loading.visible = True
        error_text.visible = False
        page.update()
        
        # ✅ Charger d'abord la config du cimetière pour les coordonnées par défaut
        load_cemetery_config()
        
        try:
            data = auth.api.get("/cemetery/sections")
            sections_data.clear()
            if isinstance(data, list):
                sections_data.extend(data)
            section_dropdown.options = [
                ft.dropdown.Option(str(s["id"]), f"{s['name']} ({s.get('capacite_caveaux', '?')} places calc.)")
                for s in sections_data
            ]
            if sections_data:
                section_dropdown.value = str(sections_data[0]["id"])
                prefill_start_coords()
        except ApiError as exc:
            show_error(f"❌ Erreur de chargement des sections : {_friendly_error(exc)}")
        except Exception:
            show_error("❌ Impossible de charger la liste des sections.")
        finally:
            loading.visible = False
            page.update()

    def prefill_start_coords():
        """Pré-remplit lat/lng de départ avec le premier point du polygone de la section sélectionnée."""
        section_id = section_dropdown.value
        section = next((s for s in sections_data if str(s["id"]) == section_id), None)
        if section and section.get("polygon_coords"):
            first_point = section["polygon_coords"][0]
            start_lat_field.value = str(first_point[0])
            start_lng_field.value = str(first_point[1])
            page.update()

    section_dropdown.on_change = lambda e: prefill_start_coords()

    def validate() -> str | None:
        if not section_dropdown.value:
            return "❌ Veuillez sélectionner une section."
        try:
            rows = int(rows_field.value)
            if not (1 <= rows <= 50):
                return "❌ Le nombre de rangées doit être entre 1 et 50."
        except (ValueError, TypeError):
            return "❌ Le nombre de rangées doit être un nombre entier."
        try:
            cols = int(cols_field.value)
            if not (1 <= cols <= 50):
                return "❌ Le nombre de colonnes doit être entre 1 et 50."
        except (ValueError, TypeError):
            return "❌ Le nombre de colonnes doit être un nombre entier."
        try:
            float(spacing_field.value)
        except (ValueError, TypeError):
            return "❌ L'espacement doit être une valeur numérique."
        prefix = (prefix_field.value or "").strip()
        if not prefix or len(prefix) != 1 or not prefix.isalpha() or not prefix.isupper():
            return "❌ Le préfixe doit être une seule lettre majuscule (ex: A)."
        try:
            price = float(price_field.value)
            if price <= 0:
                return "❌ Le prix doit être supérieur à 0."
        except (ValueError, TypeError):
            return "❌ Le prix doit être une valeur numérique."
        try:
            lat = float(start_lat_field.value)
            if not (-90 <= lat <= 90):
                return "❌ Latitude de départ invalide."
        except (ValueError, TypeError):
            return "❌ La latitude de départ doit être une valeur numérique."
        try:
            lng = float(start_lng_field.value)
            if not (-180 <= lng <= 180):
                return "❌ Longitude de départ invalide."
        except (ValueError, TypeError):
            return "❌ La longitude de départ doit être une valeur numérique."
        return None

    def on_generate(e):
        error = validate()
        if error:
            show_error(error)
            return

        loading.visible = True
        error_text.visible = False
        success_text.visible = False
        page.update()

        try:
            payload = {
                "section_id": int(section_dropdown.value),
                "rows": int(rows_field.value),
                "cols": int(cols_field.value),
                "start_lat": float(start_lat_field.value),
                "start_lng": float(start_lng_field.value),
                "spacing_meters": float(spacing_field.value),
                "prefix": prefix_field.value.strip().upper(),
                "price": float(price_field.value),
            }
            result = auth.api.post("/cemetery/graves/generate-grid", json=payload)

            count = result.get("created_count", 0) if isinstance(result, dict) else 0
            
            # ✅ MESSAGE DE SUCCÈS AVEC REDIRECTION AUTOMATIQUE
            page.snack_bar = ft.SnackBar(
                content=ft.Text(
                    f"✅ {count} caveaux générés avec succès ! Redirection vers la carte...",
                    color=Colors.TEXT_ON_DARK,
                    weight=ft.FontWeight.BOLD
                ),
                bgcolor="#496042",
                duration=2500
            )
            page.snack_bar.open = True
            page.update()
            
            # ✅ CORRECTION CRITIQUE : Redirection automatique vers la carte
            async def redirect_to_map():
                await asyncio.sleep(1.8)  # Délai pour que l'utilisateur voie le message
                page.go("/carte")
            page.run_task(redirect_to_map)

        except ApiError as exc:
            loading.visible = False
            show_error(f"❌ Échec de la génération : {_friendly_error(exc)}")
        except Exception as exc:
            loading.visible = False
            show_error(f"❌ Une erreur inattendue est survenue : {exc}")

    load_sections()
    device = get_device_type(page.width or 1200)

    return ft.View(
        route="/graves/generate-grid",
        controls=[
            ft.Row([
                ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: page.go("/dashboard/admin")),
                ft.Text("Génération de grille de caveaux", style=heading_style(size=22)),
            ]),
            ft.Container(height=10),
            loading,
            error_text,
            success_text,
            ft.Container(
                content=ft.Column([
                    ft.Text("💡 Astuce : Les coordonnées sont pré-remplies depuis la configuration du cimetière.", size=12, color=Colors.NEUTRAL, italic=True),
                    ft.Container(height=10),
                    section_dropdown,
                    ft.Container(height=10),
                    ft.Row([rows_field, cols_field], spacing=16),
                    ft.Container(height=10),
                    ft.Row([spacing_field, prefix_field], spacing=16),
                    ft.Container(height=10),
                    price_field,
                    ft.Divider(height=20, color=Colors.BORDER),
                    ft.Text("Point de départ (pré-rempli depuis la section, ajustable)", size=13, color=Colors.NEUTRAL),
                    ft.Container(height=10),
                    ft.Row([start_lat_field, start_lng_field], spacing=16),
                    ft.Container(height=20),
                    ft.ElevatedButton(
                        content=ft.Row([ft.Icon(ft.Icons.GRID_ON, color=Colors.TEXT_ON_DARK), ft.Text("Générer et voir sur la carte", color=Colors.TEXT_ON_DARK, weight=ft.FontWeight.BOLD)], spacing=8),
                        style=ft.ButtonStyle(bgcolor=Colors.PRIMARY),
                        width=350,
                        height=50,
                        on_click=on_generate,
                    ),
                ], spacing=12),
                padding=24, bgcolor=Colors.SURFACE, border_radius=12,
                width=600 if device == "desktop" else None,
            ),
        ],
        bgcolor=Colors.BACKGROUND,
        padding=24 if device == "desktop" else 16,
        scroll=ft.ScrollMode.AUTO,
    )