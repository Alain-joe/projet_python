"""
views/cemetery/initial_setup.py — Configuration standard du cimetière en une seule étape.
Compatible Flet 0.86.0

NOUVELLE VERSION : suppression de l'étape de dessin des allées (trop complexe
pour un usage standard). L'utilisateur saisit les propriétés du cimetière
(position GPS, dimensions, dimensions des caveaux, prix), la superficie et
la capacité théorique sont calculées et affichées en aperçu, et au clic sur
"Terminer" :
  1. Le cimetière est créé/mis à jour sans allées (une seule section couvre
     tout le terrain — le backend gère déjà ce cas : GeometryService.
     split_cemetery_by_allees retourne le rectangle entier si allees=[]).
  2. Une grille de caveaux est générée automatiquement dans cette section
     unique, dimensionnée pour atteindre la capacité calculée.
"""
from __future__ import annotations
import math
import flet as ft
from core.auth import AuthState
from core.api import ApiError, Endpoints
from core.theme import Colors, get_device_type, heading_style
from data.villes_congo import VILLES_CONGO, VILLES_COORDS

METERS_PER_DEGREE = 111111.0

_ERROR_TRANSLATIONS = {
    "field required": "Ce champ est obligatoire.",
    "this field is required": "Ce champ est obligatoire.",
    "value is not a valid integer": "Une valeur numérique entière est attendue.",
    "value is not a valid float": "Une valeur numérique est attendue.",
    "ensure this value is greater than": "La valeur doit être supérieure au minimum autorisé.",
    "ensure this value is less than or equal to": "La valeur dépasse le maximum autorisé.",
    "not found": "Élément introuvable.",
    "session expir": "Votre session a expiré. Veuillez vous reconnecter.",
}


def _friendly_error(exc) -> str:
    raw = getattr(exc, "message", None) or str(exc)
    raw_lower = raw.lower()
    for needle, translation in _ERROR_TRANSLATIONS.items():
        if needle in raw_lower:
            return translation
    if any(w in raw_lower for w in ["veuillez", "obligatoire", "invalide", "erreur", "échec"]):
        return raw
    return "Une erreur est survenue. Vérifiez les champs et réessayez."


def build_initial_setup_view(page: ft.Page, auth: AuthState) -> ft.View:
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

    price_field = ft.TextField(label="Prix par caveau (FCFA) *", value="50000", border_radius=8, keyboard_type=ft.KeyboardType.NUMBER)

    preview_text = ft.Text("", size=13, color=Colors.PRIMARY, weight=ft.FontWeight.W_600)
    error_text = ft.Text("", color=Colors.ERROR, size=13, visible=False)
    success_text = ft.Text("", color=Colors.PRIMARY, size=13, visible=False)
    loading = ft.ProgressRing(visible=False, width=20, height=20)

    def update_preview(e=None) -> None:
        try:
            longueur = float(longueur_field.value)
            largeur = float(largeur_field.value)
            gl = float(grave_length_field.value)
            gw = float(grave_width_field.value)
            esp = float(espacement_field.value)
            surface = longueur * largeur
            grave_area = (gl + esp) * (gw + esp)
            capacite = int(surface / grave_area) if grave_area > 0 else 0
            preview_text.value = f"📐 Superficie : {surface:,.0f} m² — Capacité estimée : {capacite:,} caveaux".replace(",", " ")
        except (ValueError, TypeError, ZeroDivisionError):
            preview_text.value = ""
        page.update()

    for f in (longueur_field, largeur_field, grave_length_field, grave_width_field, espacement_field):
        f.on_change = update_preview

    def on_city_change(e):
        if city_field.value and city_field.value in VILLES_COORDS:
            coords = VILLES_COORDS[city_field.value]
            lat_field.value = str(coords["lat"])
            lng_field.value = str(coords["lng"])
            page.update()

    city_field.on_change = on_city_change

    def validate() -> str | None:
        if not all([name_field.value, city_field.value, address_field.value, lat_field.value, lng_field.value, longueur_field.value, largeur_field.value, price_field.value]):
            return "❌ Veuillez remplir tous les champs obligatoires (*)."
        try:
            float(lat_field.value); float(lng_field.value)
            float(longueur_field.value); float(largeur_field.value)
            float(grave_length_field.value); float(grave_width_field.value)
            float(espacement_field.value)
            price = float(price_field.value)
            if price <= 0:
                return "❌ Le prix par caveau doit être supérieur à 0."
        except ValueError:
            return "❌ Valeurs numériques invalides."
        return None

    def on_terminer(e):
        error = validate()
        if error:
            error_text.value = error
            error_text.visible = True
            success_text.visible = False
            page.update()
            return

        loading.visible = True
        error_text.visible = False
        success_text.visible = False
        page.update()

        try:
            lat = float(lat_field.value.strip())
            lng = float(lng_field.value.strip())
            longueur = float(longueur_field.value.strip())
            largeur = float(largeur_field.value.strip())
            grave_length = float(grave_length_field.value.strip())
            grave_width = float(grave_width_field.value.strip())
            espacement = float(espacement_field.value.strip())
            price = float(price_field.value.strip())

            # Étape 1 : créer le cimetière SANS allées -> une seule section
            # couvrant tout le terrain (le backend gère déjà ce cas).
            init_payload = {
                "cemetery": {
                    "name": name_field.value.strip(),
                    "city": city_field.value,
                    "address": address_field.value.strip(),
                    "latitude": lat,
                    "longitude": lng,
                    "total_area": longueur * largeur,
                    "longueur_totale": longueur,
                    "largeur_totale": largeur,
                    "grave_length": grave_length,
                    "grave_width": grave_width,
                    "espacement_caveaux": espacement,
                    "non_exploitable_area": 0.0,
                },
                "allees": [],
            }
            init_result = auth.api.post(Endpoints.CEMETERY_INITIALIZE_COMPLETE, json=init_payload)

            sections = init_result.get("sections", []) if isinstance(init_result, dict) else []
            if not sections:
                raise ApiError("Aucune section n'a pu être générée à partir de ces dimensions.")

            section = sections[0]
            section_id = section["id"]
            capacite = section.get("capacite", 0)

            if capacite <= 0:
                success_text.value = "✅ Cimetière configuré. Aucun caveau généré (capacité calculée = 0, vérifiez les dimensions)."
                success_text.visible = True
                loading.visible = False
                page.update()
                return

            # Étape 2 : générer la grille de caveaux dans cette section unique.
            # Grille approximativement carrée pour atteindre la capacité visée,
            # plafonnée à 50x50 (limite de l'endpoint generate-grid).
            side = min(50, max(1, math.ceil(math.sqrt(capacite))))
            rows = side
            cols = min(50, max(1, math.ceil(capacite / side)))

            # Point de départ : coin sud-ouest du rectangle du cimetière.
            delta_lat = (largeur / 2) / METERS_PER_DEGREE
            delta_lng = (longueur / 2) / (METERS_PER_DEGREE * math.cos(math.radians(lat)))
            start_lat = lat - delta_lat
            start_lng = lng - delta_lng

            grid_payload = {
                "section_id": section_id,
                "rows": rows,
                "cols": cols,
                "start_lat": start_lat,
                "start_lng": start_lng,
                "spacing_meters": grave_length + espacement,
                "prefix": "A",
                "price": price,
            }
            grid_result = auth.api.post("/cemetery/graves/generate-grid", json=grid_payload)
            created = grid_result.get("created_count", 0) if isinstance(grid_result, dict) else 0

            success_text.value = f"✅ Configuration terminée ! {created} caveaux générés."
            success_text.visible = True
            error_text.visible = False
            loading.visible = False
            page.update()

            page.go("/dashboard/admin")

        except ApiError as exc:
            error_text.value = f"❌ Échec : {_friendly_error(exc)}"
            error_text.visible = True
            loading.visible = False
            page.update()
        except Exception:
            error_text.value = "❌ Une erreur inattendue est survenue lors de la configuration."
            error_text.visible = True
            loading.visible = False
            page.update()

    device = get_device_type(page.width or 1200)

    return ft.View(
        route="/cimetiere/setup",
        controls=[
            ft.Row([ft.Text("Configuration du Cimetière", style=heading_style(size=24)), ft.Container(expand=True), ft.ElevatedButton("← Retour", on_click=lambda _: page.go("/dashboard/admin"))]),
            ft.Container(height=10),
            ft.Text("Configuration standard — les caveaux sont générés automatiquement.", size=14, color=Colors.NEUTRAL),
            ft.Container(height=20),
            error_text,
            success_text,
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
                    ft.Container(height=10),
                    price_field,
                    ft.Container(height=10),
                    preview_text,
                    ft.Container(height=20),
                    loading,
                    ft.ElevatedButton(
                        content=ft.Row([ft.Text("Terminer et générer les caveaux"), ft.Icon(ft.Icons.CHECK_CIRCLE)]),
                        bgcolor=Colors.PRIMARY, color=Colors.TEXT_ON_DARK, width=320, on_click=on_terminer
                    ),
                ], spacing=12),
                padding=24, bgcolor=Colors.SURFACE, border_radius=12, width=600 if device == "desktop" else None,
            ),
        ],
        bgcolor=Colors.BACKGROUND, padding=24 if device == "desktop" else 16, scroll=ft.ScrollMode.AUTO,
    )