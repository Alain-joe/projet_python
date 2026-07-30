"""
views/users/create.py — Page de création d'utilisateur (secrétariat + admin).
Compatible Flet 0.86.3

CORRECTIONS APPLIQUÉES :
- BUG CRITIQUE : loading.visible ne repassait jamais à False en cas de
  succès ou d'erreur logique du serveur (seuls les except le faisaient) →
  le spinner restait affiché indéfiniment. Corrigé : loading.visible =
  False systématiquement, dans tous les chemins (succès, erreur logique,
  exception).
- Ajout de la validation du FORMAT nom/prénom (lettres, espaces, tirets,
  accents uniquement — aucun chiffre), qui était promise par le label
  mais jamais vérifiée.
- Ajout de la validation de longueur de l'adresse (5 à 200 caractères),
  promise par le label mais jamais vérifiée.
- Message d'erreur logique du serveur (réponse {"error": ...} sans
  exception) désormais aussi affiché dans error_text, en plus du
  SnackBar existant — cohérent avec le reste de l'app, et visible même
  si le SnackBar est raté.
"""
from __future__ import annotations
import flet as ft
from datetime import datetime
import re
from core.auth import AuthState, Role
from core.api import ApiError
from core.theme import Colors, get_device_type, heading_style

NOM_RE = re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿ\s\-]+$")  # lettres, espaces, tirets, accents


def build_user_create_view(page: ft.Page, auth: AuthState) -> ft.View:

    def show_snack(message: str, error: bool = False):
        page.snack_bar = ft.SnackBar(
            content=ft.Row([
                ft.Icon(ft.Icons.ERROR if error else ft.Icons.CHECK_CIRCLE, color=ft.Colors.WHITE),
                ft.Text(message, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD)
            ]),
            bgcolor=ft.Colors.RED_700 if error else ft.Colors.GREEN_700,
            behavior=ft.SnackBarBehavior.FLOATING,
        )
        page.snack_bar.open = True
        page.update()

    def go_back(e):
        target = "/dashboard/admin" if auth.role and auth.role.value == "admin" else "/dashboard/secretariat"
        page.go(target)

    username_field = ft.TextField(
        label="Nom d'utilisateur (optionnel, auto-généré sinon)",
        prefix_icon=ft.Icons.PERSON_OUTLINE, border_radius=8,
    )

    first_name_field = ft.TextField(
        label="Prénom * (Lettres, espaces, tirets)",
        expand=True, prefix_icon=ft.Icons.BADGE, border_radius=8
    )

    last_name_field = ft.TextField(
        label="Nom * (Lettres, espaces, tirets)",
        expand=True, prefix_icon=ft.Icons.BADGE, border_radius=8
    )

    email_field = ft.TextField(
        label="Email * (ex: nom@domaine.com)",
        expand=True, keyboard_type=ft.KeyboardType.EMAIL, prefix_icon=ft.Icons.EMAIL, border_radius=8
    )

    phone_field = ft.TextField(
        label="Téléphone * (9 chiffres, ex: 061234567)",
        expand=True, keyboard_type=ft.KeyboardType.PHONE, prefix_icon=ft.Icons.PHONE, border_radius=8
    )

    sex_field = ft.Dropdown(
        label="Sexe", value="N", expand=True, border_radius=8,
        options=[
            ft.dropdown.Option("M", "Masculin"),
            ft.dropdown.Option("F", "Féminin"),
            ft.dropdown.Option("O", "Autre"),
            ft.dropdown.Option("N", "Non renseigné"),
        ],
    )

    birth_date_field = ft.TextField(
        label="Date de naissance * (AAAA-MM-JJ)",
        expand=True, read_only=True, border_radius=8,
        prefix_icon=ft.Icons.CALENDAR_MONTH,
        suffix=ft.Icon(ft.Icons.CALENDAR_TODAY, color=Colors.PRIMARY),
    )

    birth_date_picker = ft.DatePicker(
        first_date=datetime(1900, 1, 1),
        last_date=datetime.now(),
        on_change=lambda e: setattr(birth_date_field, 'value', e.control.value.strftime("%Y-%m-%d") if e.control.value else ""),
    )
    page.overlay.append(birth_date_picker)

    def show_date_picker(e):
        birth_date_picker.open = True
        page.update()

    birth_date_field.on_click = show_date_picker

    role_field = ft.Dropdown(
        label="Rôle *", value="client", expand=True, border_radius=8,
        options=[
            ft.dropdown.Option("admin", "Administrateur"),
            ft.dropdown.Option("secretariat", "Secrétariat"),
            ft.dropdown.Option("agent", "Agent de terrain"),
            ft.dropdown.Option("client", "Client"),
        ],
    )

    password_field = ft.TextField(
        label="Mot de passe (optionnel, auto-généré sinon)",
        expand=True, password=True, can_reveal_password=True, prefix_icon=ft.Icons.LOCK, border_radius=8,
    )

    confirm_password_field = ft.TextField(
        label="Confirmer le mot de passe",
        expand=True, password=True, can_reveal_password=True, prefix_icon=ft.Icons.LOCK, border_radius=8,
    )

    city_dropdown = ft.Dropdown(
        label="Ville (optionnel)", border_radius=8,
        options=[
            ft.dropdown.Option("Pointe-Noire", "Pointe-Noire"),
            ft.dropdown.Option("Brazzaville", "Brazzaville"),
            ft.dropdown.Option("Dolisie", "Dolisie"),
            ft.dropdown.Option("Ouesso", "Ouesso"),
            ft.dropdown.Option("Nkayi", "Nkayi"),
        ],
    )

    address_field = ft.TextField(
        label="Adresse (optionnel, 5 à 200 caractères)",
        prefix_icon=ft.Icons.LOCATION_ON, border_radius=8, multiline=True, min_lines=2
    )

    error_text = ft.Text("", color=Colors.ERROR, size=13, visible=False, weight=ft.FontWeight.W_600)
    loading = ft.ProgressRing(visible=False, width=20, height=20)

    def clear_form():
        for f in (username_field, first_name_field, last_name_field, email_field,
                  phone_field, birth_date_field, password_field, confirm_password_field, address_field):
            f.value = ""
            f.error_text = None
        sex_field.value = "N"
        role_field.value = "client"
        city_dropdown.value = None
        page.update()

    def validate() -> bool:
        valid = True
        required = [
            (first_name_field, "Le prénom est obligatoire."),
            (last_name_field, "Le nom est obligatoire."),
            (email_field, "L'email est obligatoire."),
            (birth_date_field, "La date de naissance est obligatoire."),
        ]
        for field, msg in required:
            if not field.value or not field.value.strip():
                field.error_text = msg
                valid = False
            else:
                field.error_text = None

        # ✅ NOUVEAU : format nom/prénom (lettres, espaces, tirets uniquement)
        if first_name_field.value and first_name_field.value.strip():
            if not NOM_RE.match(first_name_field.value.strip()):
                first_name_field.error_text = "Uniquement lettres, espaces et tirets (aucun chiffre)."
                valid = False

        if last_name_field.value and last_name_field.value.strip():
            if not NOM_RE.match(last_name_field.value.strip()):
                last_name_field.error_text = "Uniquement lettres, espaces et tirets (aucun chiffre)."
                valid = False

        if email_field.value and email_field.value.strip() and "@" not in email_field.value:
            email_field.error_text = "Format d'email invalide."
            valid = False

        if phone_field.value and phone_field.value.strip():
            if not re.match(r"^(04|05|06)\d{7}$", phone_field.value.strip()):
                phone_field.error_text = "Téléphone invalide (9 chiffres, commence par 04, 05 ou 06)."
                valid = False
            else:
                phone_field.error_text = None

        if password_field.value or confirm_password_field.value:
            if password_field.value != confirm_password_field.value:
                confirm_password_field.error_text = "Les mots de passe ne correspondent pas."
                valid = False
            else:
                confirm_password_field.error_text = None

            pwd = password_field.value
            if pwd and (len(pwd) < 8 or not re.search(r"[A-Z]", pwd) or not re.search(r"[a-z]", pwd) or not re.search(r"\d", pwd) or not re.search(r"[!@#$%^&*(),.?\":{}|<>]", pwd)):
                password_field.error_text = "Min 8 car., 1 maj, 1 min, 1 chiffre, 1 spécial."
                valid = False
            else:
                password_field.error_text = None
        else:
            password_field.error_text = None
            confirm_password_field.error_text = None

        if username_field.value and username_field.value.strip():
            if not re.match(r"^[a-zA-Z0-9_]{4,30}$", username_field.value.strip()):
                username_field.error_text = "4 à 30 caractères alphanumériques ou _ uniquement."
                valid = False
            else:
                username_field.error_text = None

        # ✅ NOUVEAU : longueur de l'adresse (5 à 200 caractères), si renseignée
        if address_field.value and address_field.value.strip():
            addr_len = len(address_field.value.strip())
            if addr_len < 5 or addr_len > 200:
                address_field.error_text = "L'adresse doit contenir entre 5 et 200 caractères."
                valid = False
            else:
                address_field.error_text = None
        else:
            address_field.error_text = None

        page.update()
        return valid

    def on_add(e):
        if not validate():
            return

        loading.visible = True
        error_text.visible = False
        page.update()

        payload = {
            "username": username_field.value.strip().lower() if username_field.value.strip() else None,
            "first_name": first_name_field.value.strip().title(),
            "last_name": last_name_field.value.strip().title(),
            "email": email_field.value.strip().lower(),
            "phone": phone_field.value.strip(),
            "sex": sex_field.value,
            "birth_date": birth_date_field.value.strip() or None,
            "role": role_field.value,
            "password": password_field.value or None,
            "address": address_field.value.strip().title() if address_field.value.strip() else None,
            "city": city_dropdown.value,
        }

        try:
            response = auth.api.create_internal_user(payload)
            if response is True or response is None or (isinstance(response, dict) and "error" not in response):
                username = response.get("username", "N/A") if isinstance(response, dict) else "N/A"
                temp_pwd = response.get("temporary_password") if isinstance(response, dict) else None
                msg = f"✅ Utilisateur créé avec succès — identifiant : {username}"
                if temp_pwd:
                    msg += f" — mot de passe : {temp_pwd}"
                show_snack(msg)
                clear_form()
                # ✅ FIX : réinitialiser le chargement après un succès
                loading.visible = False
                page.update()
            else:
                err = response.get("error", "Erreur inconnue") if isinstance(response, dict) else str(response)
                show_snack(f"Erreur : {err}", True)
                # ✅ FIX : afficher aussi dans error_text (plus fiable que le
                # SnackBar seul) ET réinitialiser le chargement.
                error_text.value = f"❌ {err}"
                error_text.visible = True
                loading.visible = False
                page.update()
        except ApiError as exc:
            error_text.value = f"❌ Échec : {exc.message}"
            error_text.visible = True
            loading.visible = False
            page.update()
        except Exception as exc:
            error_text.value = f"❌ Erreur de connexion : {exc}"
            error_text.visible = True
            loading.visible = False
            page.update()

    submit_button = ft.ElevatedButton(
        content=ft.Row(
            [ft.Icon(ft.Icons.PERSON_ADD, color=ft.Colors.WHITE, size=19),
             ft.Text("Créer l'utilisateur", color=ft.Colors.WHITE, weight=ft.FontWeight.W_600, size=14)],
            spacing=8, alignment=ft.MainAxisAlignment.CENTER,
        ),
        style=ft.ButtonStyle(bgcolor=Colors.PRIMARY, shape=ft.RoundedRectangleBorder(radius=10)),
        height=46, width=float("inf"),
        on_click=on_add,
    )

    def field_row(*fields: ft.Control) -> ft.ResponsiveRow:
        cols = 12 // len(fields)
        return ft.ResponsiveRow(
            [ft.Container(f, col={"xs": 12, "sm": 12, "md": cols}) for f in fields],
            spacing=12, run_spacing=8,
        )

    width = getattr(page, 'window', page).width if hasattr(page, 'window') else (getattr(page, 'width', 1200) or 1200)
    device = get_device_type(width)

    return ft.View(
        route="/users/nouveau",
        controls=[
            ft.Row([
                ft.IconButton(icon=ft.Icons.ARROW_BACK, tooltip="Retour", on_click=go_back),
                ft.Text("Nouvel utilisateur", style=heading_style(size=22)),
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Container(height=10),
            ft.Text(
                "Créez un compte pour un utilisateur. Les champs marqués * sont obligatoires.",
                size=13, color=Colors.NEUTRAL,
            ),
            ft.Container(height=20),
            ft.Container(
                content=ft.Column([
                    username_field,
                    field_row(first_name_field, last_name_field),
                    field_row(email_field, phone_field),
                    field_row(sex_field, birth_date_field),
                    role_field,
                    ft.Container(height=8),
                    ft.Text("Sécurité", style=heading_style(size=16)),
                    field_row(password_field, confirm_password_field),
                    ft.Container(height=8),
                    ft.Text("Localisation (Optionnel)", style=heading_style(size=16)),
                    city_dropdown,
                    address_field,
                    ft.Container(height=20),
                    error_text,
                    submit_button,
                    ft.Container(height=10),
                    loading,
                ], spacing=14, scroll=ft.ScrollMode.AUTO),
                padding=24, bgcolor="#FFFFFF", border_radius=14,
                shadow=ft.BoxShadow(spread_radius=0, blur_radius=10, color="#00000014"),
                width=800 if device != "mobile" else None,
            ),
        ],
        bgcolor=Colors.BACKGROUND,
        padding=16 if device == "mobile" else 32,
        scroll=ft.ScrollMode.AUTO,
    )