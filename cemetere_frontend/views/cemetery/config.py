"""
views/cemetery/config.py — Configuration du cimetière (Admin uniquement).
Compatible Flet 0.86.0

CORRECTIONS APPLIQUÉES :
- BUG CRITIQUE : float(champ.value) était appelé AVANT le bloc try,
  donc une valeur non numérique (ex: "abc") faisait planter la fonction
  sans message d'erreur et laissait submit_loading bloqué indéfiniment.
  Corrigé : validation explicite AVANT toute conversion, avec message
  précis, le try ne contient plus que l'appel réseau.
- Ajout de la validation : champs obligatoires (nom, ville), superficie
  et dimensions doivent être des nombres strictement positifs dans une
  plage raisonnable.
- page.window.width sécurisé avec repli 1200.
"""
from __future__ import annotations
import flet as ft
from core.auth import AuthState
from core.api import ApiError, Endpoints
from core.theme import Colors, get_device_type, heading_style


def build_cemetery_config_view(page: ft.Page, auth: AuthState) -> ft.View:
    config_data = {}
    loading = ft.ProgressRing(visible=True)
    error_text = ft.Text("", color=Colors.ERROR, size=13, visible=False, weight=ft.FontWeight.W_600)
    success_text = ft.Text("", color=Colors.PRIMARY, size=13, visible=False)
    submit_loading = ft.ProgressRing(visible=False, width=20, height=20)

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
            data = auth.api.get(Endpoints.CEMETERY_CONFIG)
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

    def _parse_positive_float(raw: str, label: str, min_val: float, max_val: float) -> tuple[float | None, str | None]:
        raw = (raw or "").strip()
        if not raw:
            return None, f"❌ Le champ « {label} » est obligatoire."
        try:
            value = float(raw.replace(",", "."))
        except ValueError:
            return None, f"❌ Le champ « {label} » doit être un nombre valide (ex: 2.5)."
        if value <= 0:
            return None, f"❌ Le champ « {label} » doit être strictement supérieur à 0."
        if value < min_val or value > max_val:
            return None, f"❌ Le champ « {label} » doit être compris entre {min_val} et {max_val}."
        return value, None

    def validate() -> tuple[dict | None, str | None]:
        name = (name_field.value or "").strip()
        if not name:
            return None, "❌ Le nom du cimetière est obligatoire."

        city = (city_field.value or "").strip()
        if not city:
            return None, "❌ La ville est obligatoire."

        total_area, err = _parse_positive_float(total_area_field.value, "Superficie totale (m²)", 1, 10_000_000)
        if err:
            return None, err

        grave_length, err = _parse_positive_float(grave_length_field.value, "Longueur standard caveau (m)", 0.5, 10)
        if err:
            return None, err

        grave_width, err = _parse_positive_float(grave_width_field.value, "Largeur standard caveau (m)", 0.5, 5)
        if err:
            return None, err

        payload = {
            "name": name,
            "city": city,
            "address": (address_field.value or "").strip(),
            "total_area": total_area,
            "grave_length": grave_length,
            "grave_width": grave_width,
        }
        return payload, None

    def save_config(e) -> None:
        error_text.visible = False
        success_text.visible = False
        page.update()

        # ✅ FIX : toute la validation/conversion se fait AVANT d'afficher
        # le spinner et AVANT le bloc try — plus aucun risque de crash
        # silencieux sur une valeur non numérique.
        payload, error = validate()
        if error:
            error_text.value = error
            error_text.visible = True
            page.update()
            return

        submit_loading.visible = True
        page.update()

        try:
            auth.api.put(Endpoints.CEMETERY_CONFIG, json=payload)
            success_text.value = "✅ Configuration enregistrée avec succès."
            success_text.visible = True
        except ApiError as exc:
            error_text.value = f"❌ Échec : {exc.message}"
            error_text.visible = True
        except Exception as exc:
            error_text.value = f"❌ Erreur inattendue : {exc}"
            error_text.visible = True
        finally:
            submit_loading.visible = False
            page.update()

    load_config()

    window_width = None
    if hasattr(page, "window") and page.window is not None:
        window_width = page.window.width
    if not window_width:
        window_width = getattr(page, "width", None)
    device = get_device_type(window_width or 1200)

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