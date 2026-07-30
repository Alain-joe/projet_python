"""
views/inhumations/confirm.py — Formulaire de confirmation d'inhumation pour l'Agent.
Compatible Flet 0.86.3.

CORRECTION CRITIQUE : page.open() n'existe pas sur cette build de Flet
('Page' object has no attribute 'open') — remplacé par show_overlay(),
défensif (essaie page.open(), retombe sur page.overlay + .open=True
sinon).

CORRECTION AJOUTÉE :
- observations_field : keyboard_type=TEXT forcé explicitement (même
  précaution que sur le formulaire d'exhumation, pour éviter un clavier
  numérique par défaut sur un champ multiline).
- _friendly_error() : traduction en français des messages d'erreur bruts
  renvoyés par le backend, affichés à la place du texte anglais brut.
"""
from __future__ import annotations
import asyncio
import flet as ft
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta

from core.auth import AuthState, Role
from core.api import ApiError, Endpoints
from core.theme import Colors, get_device_type, heading_style
from core.ui_utils import show_overlay


# ==============================================================================
# TRADUCTION DES ERREURS BACKEND (fallback si le message est brut/anglais)
# ==============================================================================
_ERROR_TRANSLATIONS = {
    "field required": "Ce champ est obligatoire.",
    "this field is required": "Ce champ est obligatoire.",
    "none is not an allowed value": "Ce champ ne peut pas être vide.",
    "value is not a valid integer": "Une valeur numérique est attendue.",
    "value is not a valid date": "Format de date invalide.",
    "value is not a valid datetime": "Format de date/heure invalide.",
    "ensure this value has at least": "Le texte saisi est trop court.",
    "ensure this value has at most": "Le texte saisi est trop long.",
    "string too short": "Le texte saisi est trop court.",
    "string too long": "Le texte saisi est trop long.",
    "not found": "Élément introuvable.",
    "invalid": "Valeur invalide.",
}


def _friendly_error(exc) -> str:
    """
    Traduit un message d'erreur backend (souvent en anglais, brut) vers un
    message générique en français compréhensible. Utilisé en dernier
    recours, quand la validation locale n'a rien détecté mais que le
    serveur refuse quand même la requête.
    """
    raw = getattr(exc, "message", None) or str(exc)
    raw_lower = raw.lower()

    for needle, translation in _ERROR_TRANSLATIONS.items():
        if needle in raw_lower:
            return translation

    if any(w in raw_lower for w in ["veuillez", "obligatoire", "invalide", "erreur", "échec"]):
        return raw

    return "Une erreur est survenue lors du traitement de la demande. Veuillez réessayer."


def build_inhumation_confirm_view(page: ft.Page, auth: AuthState) -> ft.View:
    query = parse_qs(urlparse(page.route).query)
    reservation_id = query.get("reservation_id", [None])[0]

    if not reservation_id:
        page.go("/inhumations")
        return ft.View(route="/inhumations/confirm", controls=[])

    loading = ft.ProgressRing(visible=True, width=40, height=40)
    error_text = ft.Text("", color=Colors.ERROR, size=13, visible=False, weight=ft.FontWeight.W_600)

    reservation_data = {}

    date_reelle_picker = ft.DatePicker(
        first_date=datetime.now() - timedelta(days=3650),
        last_date=datetime.now(),
        on_change=lambda e: setattr(date_reelle_field, 'value', e.control.value.strftime("%Y-%m-%d") if e.control.value else ""),
    )
    page.overlay.append(date_reelle_picker)

    time_picker = ft.TimePicker(
        on_change=lambda e: setattr(heure_field, 'value', e.control.value.strftime("%H:%M") if e.control.value else ""),
    )
    page.overlay.append(time_picker)

    date_reelle_field = ft.TextField(
        label="Date réelle d'inhumation (AAAA-MM-JJ) *",
        read_only=True,
        border_radius=8,
        suffix=ft.Icon(ft.Icons.CALENDAR_TODAY, color=Colors.PRIMARY),
        # ✅ FIX : show_overlay() au lieu de page.open() (inexistant sur cette build)
        on_click=lambda _: show_overlay(page, date_reelle_picker)
    )

    heure_field = ft.TextField(
        label="Heure d'inhumation (HH:MM) *",
        read_only=True,
        border_radius=8,
        suffix=ft.Icon(ft.Icons.ACCESS_TIME, color=Colors.PRIMARY),
        on_click=lambda _: show_overlay(page, time_picker)
    )

    observations_field = ft.TextField(
        label="Observations (optionnel)",
        multiline=True,
        min_lines=3,
        border_radius=8,
        keyboard_type=ft.KeyboardType.TEXT,  # ✅ CORRECTION : forcé explicitement
    )

    info_container = ft.Container(visible=False)

    def show_error(message: str) -> None:
        error_text.value = message
        error_text.visible = True
        loading.visible = False
        page.update()

    def load_reservation():
        loading.visible, error_text.visible = True, False
        page.update()
        try:
            data = auth.api.get(f"/reservations/{reservation_id}/")
            reservation_data.update(data)

            res_date_str = data.get("reservation_date", "")[:10]
            if res_date_str:
                try:
                    res_date = datetime.strptime(res_date_str, "%Y-%m-%d").date()
                    date_reelle_picker.first_date = datetime(res_date.year, res_date.month, res_date.day)
                except ValueError:
                    pass

            info_container.content = ft.Column([
                ft.Text(f"Caveau : {data.get('grave_code', 'N/A')}", weight=ft.FontWeight.W_600, size=16),
                ft.Text(f"Défunt : {data.get('deceased_last_name', '')} {data.get('deceased_first_name', '')}", size=14, color=Colors.NEUTRAL),
                ft.Text(f"Date prévue : {data.get('date_prevue_inhumation', 'N/A')}", size=13, color=Colors.NEUTRAL),
            ], spacing=8)
            info_container.visible = True

        except ApiError as exc:
            # ✅ CORRECTION : message backend traduit en français
            error_text.value = f"Erreur : {_friendly_error(exc)}"
            error_text.visible = True
        finally:
            loading.visible = False
            page.update()

    def on_confirm_click(_: ft.ControlEvent):
        if not date_reelle_field.value or not heure_field.value:
            show_error("❌ La date et l'heure réelles sont obligatoires.")
            return

        error_text.visible = False
        loading.visible = True
        page.update()

        try:
            payload = {
                "date_inhumation": date_reelle_field.value,      # ✅ juste la date : "2026-07-29"
                "heure_inhumation": heure_field.value,            # ✅ l'heure séparément : "14:30"
                "observations": observations_field.value.strip()
            }
            auth.api.put(f"/reservations/{reservation_id}/confirmer-inhumation", json=payload)

            show_overlay(page, ft.SnackBar(
                content=ft.Text("✅ Inhumation confirmée avec succès. Caveau marqué comme occupé.", color=Colors.TEXT_ON_DARK),
                bgcolor="#496042"
            ))
            loading.visible = False
            page.update()

            async def redirect():
                await asyncio.sleep(1.5)
                page.go("/inhumations")
            page.run_task(redirect)

        except ApiError as exc:
            # ✅ CORRECTION : message backend traduit en français
            show_error(f"❌ Échec : {_friendly_error(exc)}")
        except Exception:
            show_error("❌ Une erreur inattendue est survenue. Veuillez réessayer.")

    load_reservation()

    width = getattr(page, 'window', page).width if hasattr(page, 'window') else (getattr(page, 'width', 1200) or 1200)
    device = get_device_type(width)

    return ft.View(
        route="/inhumations/confirm",
        controls=[
            ft.Row([
                ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: page.go("/inhumations")),
                ft.Text("Confirmer l'inhumation", style=heading_style(size=22)),
            ]),
            ft.Container(height=10),
            loading,
            error_text,
            ft.Container(
                content=ft.Column([
                    info_container,
                    ft.Divider(height=20, color=Colors.BORDER),
                    ft.Text("Détails de l'opération", style=heading_style(size=16)),
                    ft.Container(height=10),
                    date_reelle_field,
                    ft.Container(height=10),
                    heure_field,
                    ft.Container(height=10),
                    observations_field,
                    ft.Container(height=20),
                    ft.ElevatedButton(
                        content=ft.Row([ft.Icon(ft.Icons.CHECK_CIRCLE, color=Colors.TEXT_ON_DARK), ft.Text("Confirmer l'inhumation", color=Colors.TEXT_ON_DARK, weight=ft.FontWeight.BOLD)], spacing=8),
                        style=ft.ButtonStyle(bgcolor="#496042"),
                        width=float("inf"),
                        height=50,
                        on_click=on_confirm_click,
                    )
                ], spacing=0),
                padding=24, bgcolor="#FFFFFF", border_radius=12, width=600 if device != "mobile" else None,
            ),
        ],
        bgcolor=Colors.BACKGROUND,
        padding=16 if device == "mobile" else 32,
    )