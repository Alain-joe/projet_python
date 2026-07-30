"""
views/reservations/form.py — Formulaire de réservation avec DatePickers.
Compatible Flet 0.86.3.

CORRECTION CRITIQUE : page.open() n'existe pas sur cette build de Flet
('Page' object has no attribute 'open') — remplacé par show_overlay(),
qui gère déjà ce cas de manière défensive (essaie page.open(), retombe
sur l'ancien mécanisme page.overlay + .open=True sinon).

VALIDATION (inchangée) : champs obligatoires, format nom/prénom, email,
téléphone congolais, cohérence des dates.
"""
from __future__ import annotations
import re
import flet as ft
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import asyncio

from core.auth import AuthState, Role
from core.api import ApiError, Endpoints
from core.theme import Colors, get_device_type, heading_style
from core.ui_utils import show_overlay

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
PHONE_RE = re.compile(r'^(04|05|06)\d{7,}$')
NOM_RE = re.compile(r'^[^\d]+$')


def build_reservation_form_view(page: ft.Page, auth: AuthState) -> ft.View:
    if auth.role == Role.AGENT:
        return ft.View(
            route="/reservations/nouvelle",
            controls=[
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.GROUP_OFF, size=64, color=Colors.ERROR),
                        ft.Container(height=20),
                        ft.Text("Action non autorisée", style=heading_style(size=22), color=Colors.ERROR),
                        ft.Container(height=10),
                        ft.Text(
                            "Les réservations de caveaux sont gérées exclusivement par le Secrétariat ou directement par le Client.\n\n"
                            "En tant qu'Agent de terrain, vous pouvez consulter les caveaux via la carte ou confirmer des inhumations.",
                            size=14, color=Colors.NEUTRAL, text_align=ft.TextAlign.CENTER
                        ),
                        ft.Container(height=30),
                        ft.ElevatedButton(
                            content=ft.Row([ft.Icon(ft.Icons.ARROW_BACK, color=Colors.TEXT_ON_DARK), ft.Text("Retour au tableau de bord", color=Colors.TEXT_ON_DARK)]),
                            style=ft.ButtonStyle(bgcolor=Colors.PRIMARY),
                            on_click=lambda _: page.go("/dashboard/agent"),
                        )
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=40, bgcolor="#FFFFFF", border_radius=16, width=500,
                )
            ],
            bgcolor=Colors.BACKGROUND, padding=32, scroll=ft.ScrollMode.AUTO,
        )

    query = parse_qs(urlparse(page.route).query)
    grave_id = query.get("grave_id", [None])[0]

    if not grave_id:
        page.go("/carte")
        return ft.View(route="/reservations/nouvelle", controls=[])

    user_info = auth.user or {}
    today = datetime.now().date()

    date_naissance_picker = ft.DatePicker(
        first_date=datetime(1900, 1, 1),
        last_date=datetime(today.year, today.month, today.day),
        on_change=lambda e: setattr(date_naissance_field, 'value', e.control.value.strftime("%Y-%m-%d") if e.control.value else ""),
    )
    page.overlay.append(date_naissance_picker)

    date_deces_picker = ft.DatePicker(
        first_date=datetime(1900, 1, 1),
        last_date=datetime(today.year, today.month, today.day),
        on_change=lambda e: setattr(date_deces_field, 'value', e.control.value.strftime("%Y-%m-%d") if e.control.value else ""),
    )
    page.overlay.append(date_deces_picker)

    date_prevue_picker = ft.DatePicker(
        first_date=datetime(today.year, today.month, today.day),
        on_change=lambda e: setattr(date_prevue_inhumation_field, 'value', e.control.value.strftime("%Y-%m-%d") if e.control.value else ""),
    )
    page.overlay.append(date_prevue_picker)

    nom_field = ft.TextField(label="Nom *", border_radius=8, expand=True, value=user_info.get("last_name", "").capitalize() if user_info.get("last_name") else "")
    prenom_field = ft.TextField(label="Prénom *", border_radius=8, expand=True, value=user_info.get("first_name", "").capitalize() if user_info.get("first_name") else "")
    email_field = ft.TextField(label="Email *", keyboard_type=ft.KeyboardType.EMAIL, border_radius=8, expand=True, value=user_info.get("email", "").lower() if user_info.get("email") else "")
    telephone_field = ft.TextField(label="Téléphone * (ex: 0612345678)", keyboard_type=ft.KeyboardType.PHONE, border_radius=8, expand=True, value=user_info.get("phone", "") if user_info.get("phone") else "")

    defunt_nom_field = ft.TextField(label="Nom du défunt *", border_radius=8, expand=True)
    defunt_prenom_field = ft.TextField(label="Prénom du défunt *", border_radius=8, expand=True)

    date_naissance_field = ft.TextField(
        label="Date de naissance (AAAA-MM-JJ)",
        read_only=True, border_radius=8, expand=True,
        suffix=ft.Icon(ft.Icons.CALENDAR_TODAY, color=Colors.PRIMARY),
        # ✅ FIX : show_overlay() au lieu de page.open() (inexistant sur cette build)
        on_click=lambda _: show_overlay(page, date_naissance_picker)
    )

    date_deces_field = ft.TextField(
        label="Date de décès (AAAA-MM-JJ) *",
        read_only=True, border_radius=8, expand=True,
        suffix=ft.Icon(ft.Icons.CALENDAR_TODAY, color=Colors.PRIMARY),
        on_click=lambda _: show_overlay(page, date_deces_picker)
    )

    date_prevue_inhumation_field = ft.TextField(
        label="Date prévue d'inhumation (AAAA-MM-JJ) *",
        read_only=True, border_radius=8, expand=True,
        suffix=ft.Icon(ft.Icons.CALENDAR_TODAY, color=Colors.PRIMARY),
        on_click=lambda _: show_overlay(page, date_prevue_picker)
    )

    error_text = ft.Text("", color=Colors.ERROR, size=13, visible=False, weight=ft.FontWeight.W_600)
    success_text = ft.Text("", color=Colors.PRIMARY, size=13, visible=False)
    loading = ft.ProgressRing(visible=False, width=20, height=20)

    submit_button = ft.ElevatedButton(
        content=ft.Row([ft.Icon(ft.Icons.SEND, color=Colors.TEXT_ON_DARK), ft.Text("Soumettre la réservation", color=Colors.TEXT_ON_DARK, weight=ft.FontWeight.BOLD)], spacing=5, alignment=ft.MainAxisAlignment.CENTER),
        style=ft.ButtonStyle(bgcolor=Colors.PRIMARY), width=float("inf"), height=50,
    )

    def show_error(message: str) -> None:
        error_text.value = message
        error_text.visible = bool(message)
        success_text.visible = False
        page.update()

    def show_success(message: str) -> None:
        success_text.value = message
        success_text.visible = bool(message)
        error_text.visible = False
        page.update()

    def set_loading(is_loading: bool) -> None:
        loading.visible = is_loading
        submit_button.disabled = is_loading
        page.update()

    def _parse_date(raw: str) -> datetime.date | None:
        try:
            return datetime.strptime(raw.strip(), "%Y-%m-%d").date()
        except (ValueError, AttributeError):
            return None

    def validate() -> str | None:
        required_fields = [
            (nom_field, "Nom"), (prenom_field, "Prénom"), (email_field, "Email"),
            (telephone_field, "Téléphone"), (defunt_nom_field, "Nom du défunt"),
            (defunt_prenom_field, "Prénom du défunt"),
            (date_deces_field, "Date de décès"), (date_prevue_inhumation_field, "Date prévue d'inhumation"),
        ]
        for field, label in required_fields:
            if not (field.value or "").strip():
                return f"❌ Le champ « {label} » est obligatoire."

        for field, label in [
            (nom_field, "Nom"), (prenom_field, "Prénom"),
            (defunt_nom_field, "Nom du défunt"), (defunt_prenom_field, "Prénom du défunt"),
        ]:
            if not NOM_RE.match(field.value.strip()):
                return f"❌ Le champ « {label} » ne doit pas contenir de chiffres."

        if not EMAIL_RE.match(email_field.value.strip()):
            return "❌ Adresse email invalide. Format attendu : exemple@domaine.com"

        phone_clean = telephone_field.value.strip().replace(" ", "")
        if not PHONE_RE.match(phone_clean):
            return "❌ Numéro de téléphone invalide. Il doit commencer par 04, 05 ou 06 et contenir au moins 9 chiffres (ex: 0612345678)."

        date_deces = _parse_date(date_deces_field.value)
        date_prevue = _parse_date(date_prevue_inhumation_field.value)
        date_naissance = _parse_date(date_naissance_field.value) if date_naissance_field.value else None

        if date_deces is None:
            return "❌ Date de décès invalide."
        if date_deces > today:
            return "❌ La date de décès ne peut pas être dans le futur."

        if date_prevue is None:
            return "❌ Date prévue d'inhumation invalide."
        if date_prevue < today:
            return "❌ La date prévue d'inhumation ne peut pas être antérieure à aujourd'hui."

        if date_deces > date_prevue:
            return "❌ La date de décès ne peut pas être postérieure à la date prévue d'inhumation."

        if date_naissance is not None:
            if date_naissance > today:
                return "❌ La date de naissance ne peut pas être dans le futur."
            if date_naissance >= date_deces:
                return "❌ La date de naissance doit être antérieure à la date de décès."

        return None

    def on_submit_click(_: ft.ControlEvent) -> None:
        error = validate()
        if error:
            show_error(error)
            return

        show_error("")
        set_loading(True)
        try:
            payload = {
                "grave_id": int(grave_id),
                "user_id": user_info.get("id"),
                "deceased_first_name": defunt_prenom_field.value.strip().capitalize(),
                "deceased_last_name": defunt_nom_field.value.strip().capitalize(),
                "deceased_death_date": date_deces_field.value.strip(),
                "deceased_birth_date": date_naissance_field.value.strip() or None,
                "date_prevue_inhumation": date_prevue_inhumation_field.value.strip(),
                "note": f"{prenom_field.value.strip().capitalize()} | {telephone_field.value.strip()} | {email_field.value.strip().lower()}",
            }
            auth.api.post(Endpoints.RESERVATION_MANUAL, json=payload)
        except ApiError as exc:
            set_loading(False)
            show_error(f"❌ {exc.message or 'Impossible de soumettre la réservation.'}")
            return
        except Exception as exc:
            set_loading(False)
            show_error(f"❌ Erreur inattendue : {exc}")
            return

        set_loading(False)
        show_success("✅ Réservation soumise avec succès !")

        target_route = "/dashboard/admin" if auth.role in [Role.ADMIN, Role.SECRETARIAT] else "/dashboard/client"

        async def delayed_redirect():
            try:
                await asyncio.sleep(1.5)
                page.views.clear()
                page.route = target_route
                page.go(target_route)
            except Exception:
                pass

        page.run_task(delayed_redirect)

    submit_button.on_click = on_submit_click

    def field_row(*fields: ft.Control) -> ft.ResponsiveRow:
        cols = 12 // len(fields)
        return ft.ResponsiveRow(
            [ft.Container(f, col={"xs": 12, "sm": 12, "md": cols}) for f in fields],
            spacing=12, run_spacing=8,
        )

    form_column = ft.Column([
        ft.Text("Nouvelle réservation", style=heading_style(size=22)),
        ft.Text(f"Caveau sélectionné : ID {grave_id}", size=13, color=Colors.NEUTRAL, weight=ft.FontWeight.W_600),
        ft.Divider(color=Colors.BORDER),
        ft.Text("Vos coordonnées", style=heading_style(size=16)),
        field_row(nom_field, prenom_field),
        field_row(email_field, telephone_field),
        ft.Container(height=8),
        ft.Text("Informations sur le défunt", style=heading_style(size=16)),
        field_row(defunt_nom_field, defunt_prenom_field),
        field_row(date_naissance_field, date_deces_field),
        ft.Container(height=8),
        date_prevue_inhumation_field,
        ft.Container(height=20),
        error_text, success_text,
        submit_button,
        ft.Container(height=10),
        loading,
    ], spacing=14, scroll=ft.ScrollMode.AUTO)

    window_width = None
    if hasattr(page, "window") and page.window is not None:
        window_width = page.window.width
    if not window_width:
        window_width = getattr(page, "width", None)
    device = get_device_type(window_width or 1200)

    return ft.View(
        route="/reservations/nouvelle",
        controls=[ft.Container(content=form_column, padding=24 if device == "mobile" else 32, bgcolor="#FFFFFF", border_radius=12, width=800 if device != "mobile" else None)],
        bgcolor=Colors.BACKGROUND, padding=16 if device == "mobile" else 32,
    )