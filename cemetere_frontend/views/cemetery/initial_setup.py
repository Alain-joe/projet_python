"""
views/cemetery/initial_setup.py — Configuration complète du cimetière en une seule étape.
Compatible Flet 0.86.3
CORRECTION : Suppression de l'étape 2 (tracé des allées). 
La configuration se termine directement par un appel API et retour au dashboard.
"""
from __future__ import annotations
import flet as ft
from core.auth import AuthState
from core.theme import Colors, get_device_type, heading_style
from core.api import ApiError
from data.villes_congo import VILLES_CONGO, VILLES_COORDS


def build_initial_setup_view(page: ft.Page, auth: AuthState) -> ft.View:
    # Récupération de la config existante (si elle existe déjà)
    existing_config = None
    try:
        config = auth.api.get("/cemetery/config/")
        if isinstance(config, dict) and "id" in config:
            existing_config = config
    except Exception:
        pass

    # Champs du formulaire
    name_field = ft.TextField(
        label="Nom du cimetière *", 
        border_radius=8, 
        value=existing_config.get("name", "") if existing_config else ""
    )
    
    city_field = ft.Dropdown(
        label="Ville *", 
        border_radius=8,
        options=[ft.dropdown.Option(v) for v in VILLES_CONGO],
        value=existing_config.get("city", "") if existing_config else None,
    )
    
    address_field = ft.TextField(
        label="Adresse / Quartier *", 
        border_radius=8, 
        value=existing_config.get("address", "") if existing_config else ""
    )

    lat_field = ft.TextField(
        label="Latitude *", 
        border_radius=8, 
        keyboard_type=ft.KeyboardType.NUMBER, 
        value=str(existing_config.get("latitude", "")) if existing_config else ""
    )
    lng_field = ft.TextField(
        label="Longitude *", 
        border_radius=8, 
        keyboard_type=ft.KeyboardType.NUMBER, 
        value=str(existing_config.get("longitude", "")) if existing_config else ""
    )

    longueur_field = ft.TextField(
        label="Longueur totale (m) *", 
        value=str(existing_config.get("longueur_totale", 100)) if existing_config else "100", 
        border_radius=8, 
        keyboard_type=ft.KeyboardType.NUMBER
    )
    largeur_field = ft.TextField(
        label="Largeur totale (m) *", 
        value=str(existing_config.get("largeur_totale", 100)) if existing_config else "100", 
        border_radius=8, 
        keyboard_type=ft.KeyboardType.NUMBER
    )
    
    grave_length_field = ft.TextField(
        label="Longueur caveau (m)", 
        value=str(existing_config.get("grave_length", 2.5)) if existing_config else "2.5", 
        border_radius=8, 
        keyboard_type=ft.KeyboardType.NUMBER
    )
    grave_width_field = ft.TextField(
        label="Largeur caveau (m)", 
        value=str(existing_config.get("grave_width", 1.2)) if existing_config else "1.2", 
        border_radius=8, 
        keyboard_type=ft.KeyboardType.NUMBER
    )
    espacement_field = ft.TextField(
        label="Espacement (m)", 
        value=str(existing_config.get("espacement_caveaux", 0.5)) if existing_config else "0.5", 
        border_radius=8, 
        keyboard_type=ft.KeyboardType.NUMBER
    )

    error_text = ft.Text("", color=Colors.ERROR, size=13, visible=False)
    success_text = ft.Text("", color=Colors.PRIMARY, size=13, visible=False)
    loading = ft.ProgressRing(visible=False, width=24, height=24)

    # Auto-remplissage des coordonnées quand on change de ville
    def on_city_change(e):
        if city_field.value and city_field.value in VILLES_COORDS:
            coords = VILLES_COORDS[city_field.value]
            lat_field.value = str(coords["lat"])
            lng_field.value = str(coords["lng"])
            page.update()

    city_field.on_change = on_city_change

    # ✅ CORRECTION : Sauvegarde directe sans passer par l'étape 2
    def on_save(e):
        error_text.visible = False
        success_text.visible = False

        # Validation des champs obligatoires
        if not all([
            name_field.value, city_field.value, address_field.value,
            lat_field.value, lng_field.value, 
            longueur_field.value, largeur_field.value
        ]):
            error_text.value = "❌ Veuillez remplir tous les champs obligatoires (*)."
            error_text.visible = True
            page.update()
            return

        try:
            lat = float(lat_field.value.strip())
            lng = float(lng_field.value.strip())
            longueur = float(longueur_field.value.strip())
            largeur = float(largeur_field.value.strip())
            grave_length = float(grave_length_field.value.strip())
            grave_width = float(grave_width_field.value.strip())
            espacement = float(espacement_field.value.strip())
        except ValueError:
            error_text.value = "❌ Valeurs numériques invalides."
            error_text.visible = True
            page.update()
            return

        loading.visible = True
        page.update()

        try:
            if existing_config:
                # ✅ Mise à jour de la config existante
                payload = {
                    "name": name_field.value.strip(),
                    "city": city_field.value,
                    "address": address_field.value.strip(),
                    "latitude": lat,
                    "longitude": lng,
                    "longueur_totale": longueur,
                    "largeur_totale": largeur,
                    "grave_length": grave_length,
                    "grave_width": grave_width,
                    "espacement_caveaux": espacement,
                    "total_area": longueur * largeur,
                }
                auth.api.put(f"/cemetery/cemeteries/{existing_config['id']}/", json=payload)
                message = "✅ Configuration mise à jour avec succès !"
            else:
                # ✅ Création initiale avec une section par défaut (sans allées)
                payload = {
                    "cemetery": {
                        "name": name_field.value.strip(),
                        "city": city_field.value,
                        "address": address_field.value.strip(),
                        "latitude": lat,
                        "longitude": lng,
                        "longueur_totale": longueur,
                        "largeur_totale": largeur,
                        "grave_length": grave_length,
                        "grave_width": grave_width,
                        "espacement_caveaux": espacement,
                        "total_area": longueur * largeur,
                        "non_exploitable_area": 0.0,
                    },
                    "allees": [],  # Pas d'allées (configuration simplifiée)
                    "section_names": ["Section A"]  # Une section par défaut
                }
                auth.api.post("/cemetery/cemeteries/initialize-complete/", json=payload)
                message = "✅ Cimetière configuré avec succès ! Vous pouvez maintenant générer la grille de caveaux."

            loading.visible = False
            success_text.value = message
            success_text.visible = True
            page.update()

            # Redirection vers le dashboard après 1.5 seconde
            import asyncio
            async def redirect():
                await asyncio.sleep(1.5)
                page.go("/dashboard/admin")
            page.run_task(redirect)

        except ApiError as exc:
            loading.visible = False
            error_text.value = f"❌ {exc.message}"
            error_text.visible = True
            page.update()
        except Exception as exc:
            loading.visible = False
            error_text.value = f"❌ Erreur inattendue : {exc}"
            error_text.visible = True
            page.update()

    device = get_device_type(page.width or 1200)
    is_mobile = device == "mobile"

    return ft.View(
        route="/cimetiere/setup",
        controls=[
            ft.Row([
                ft.Text("Configuration du Cimetière", style=heading_style(size=24)), 
                ft.Container(expand=True), 
                ft.ElevatedButton("← Retour au tableau de bord", on_click=lambda _: page.go("/dashboard/admin"))
            ]),
            ft.Container(height=10),
            ft.Text("Remplissez les informations pour configurer votre cimetière.", size=14, color=Colors.NEUTRAL),
            ft.Container(height=20),
            error_text,
            success_text,
            ft.Container(
                content=ft.Column([
                    ft.Row([name_field, city_field], spacing=16),
                    address_field,
                    ft.Divider(),
                    ft.Text("📍 Position GPS", weight=ft.FontWeight.W_600, size=14),
                    ft.Text("Les coordonnées seront auto-remplies quand vous sélectionnez une ville.", size=11, color=Colors.NEUTRAL, italic=True),
                    ft.Row([lat_field, lng_field], spacing=16),
                    ft.Divider(),
                    ft.Text("📐 Dimensions du cimetière", weight=ft.FontWeight.W_600, size=14),
                    ft.Row([longueur_field, largeur_field], spacing=16),
                    ft.Divider(),
                    ft.Text("⚰️ Dimensions des caveaux", weight=ft.FontWeight.W_600, size=14),
                    ft.Row([grave_length_field, grave_width_field, espacement_field], spacing=16),
                    ft.Container(height=20),
                    ft.ElevatedButton(
                        content=ft.Row([
                            ft.Icon(ft.Icons.SAVE, color=Colors.TEXT_ON_DARK),
                            ft.Text("💾 Enregistrer la configuration", color=Colors.TEXT_ON_DARK, weight=ft.FontWeight.BOLD),
                            loading,
                        ], spacing=8),
                        style=ft.ButtonStyle(bgcolor=Colors.PRIMARY),
                        width=320,
                        height=50,
                        on_click=on_save,
                    ),
                    ft.Container(height=10),
                    ft.Text(
                        "💡 Après l'enregistrement, utilisez le bouton \"Générer la grille\" depuis le tableau de bord pour créer les caveaux.",
                        size=11, color=Colors.NEUTRAL, italic=True, text_align=ft.TextAlign.CENTER
                    ),
                ], spacing=12),
                padding=24, 
                bgcolor="#FFFFFF", 
                border_radius=12, 
                width=650 if not is_mobile else None,
                shadow=ft.BoxShadow(spread_radius=0, blur_radius=12, color="#00000010"),
            ),
        ],
        bgcolor=Colors.BACKGROUND, 
        padding=24 if not is_mobile else 16, 
        scroll=ft.ScrollMode.AUTO,
    )