"""
views/users/create.py — Page de création d'utilisateur avec validations strictes.
Compatible Flet 0.86.3. Responsive et conforme CDC.
"""
from __future__ import annotations
import flet as ft
from datetime import datetime
import re
from core.auth import AuthState, Role
from core.api import ApiError
from core.theme import Colors, get_device_type, heading_style


def build_user_create_view(page: ft.Page, auth: AuthState) -> ft.View:
    # --- CHAMPS DU FORMULAIRE ---
    username_field = ft.TextField(
        label="Nom d'utilisateur (optionnel - auto-généré si vide)",
        prefix_icon=ft.Icons.PERSON_OUTLINE, border_radius=8,
        helper_text="4 à 30 caractères, lettres, chiffres, _ uniquement"
    )
    
    first_name_field = ft.TextField(
        label="Prénom *", prefix_icon=ft.Icons.BADGE, border_radius=8,
        helper_text="Lettres, espaces, tirets, apostrophes"
    )
    
    last_name_field = ft.TextField(
        label="Nom *", prefix_icon=ft.Icons.BADGE, border_radius=8,
        helper_text="Lettres, espaces, tirets, apostrophes"
    )
    
    email_field = ft.TextField(
        label="Email *", prefix_icon=ft.Icons.EMAIL, 
        keyboard_type=ft.KeyboardType.EMAIL, border_radius=8,
        helper_text="exemple@domaine.com"
    )
    
    phone_field = ft.TextField(
        label="Téléphone *", prefix_icon=ft.Icons.PHONE, 
        keyboard_type=ft.KeyboardType.PHONE, border_radius=8,
        helper_text="9 chiffres (ex: 061234567)"
    )

    sex_field = ft.Dropdown(
        label="Sexe", value="N", border_radius=8,
        options=[
            ft.dropdown.Option("M", "Masculin"),
            ft.dropdown.Option("F", "Féminin"),
            ft.dropdown.Option("O", "Autre"),
            ft.dropdown.Option("N", "Non renseigné"),
        ],
    )

    birth_date_field = ft.TextField(
        label="Date de naissance *", read_only=True, border_radius=8,
        hint_text="AAAA-MM-JJ", prefix_icon=ft.Icons.CALENDAR_MONTH,
        suffix=ft.Icon(ft.Icons.CALENDAR_TODAY, color=Colors.PRIMARY),
        helper_text="L'utilisateur doit avoir au moins 16 ans"
    )

    birth_date_picker = ft.DatePicker(
        first_date=datetime(1900, 1, 1),
        last_date=datetime.now(),
        on_change=lambda e: setattr(birth_date_field, 'value', e.control.value.strftime("%Y-%m-%d") if e.control.value else ""),
    )
    page.overlay.append(birth_date_picker)

    def show_date_picker(e):
        birth_date_picker.pick_date()
    birth_date_field.on_click = show_date_picker

    role_field = ft.Dropdown(
        label="Rôle *", value="client", border_radius=8,
        options=[
            ft.dropdown.Option("admin", "Administrateur"),
            ft.dropdown.Option("secretariat", "Secrétariat"),
            ft.dropdown.Option("agent", "Agent de terrain"),
            ft.dropdown.Option("client", "Client"),
        ],
    )
    
    password_field = ft.TextField(
        label="Mot de passe (optionnel - auto-généré si vide)", 
        prefix_icon=ft.Icons.LOCK, password=True, can_reveal_password=True, border_radius=8,
        helper_text="Min 8 car., 1 maj, 1 min, 1 chiffre, 1 spécial"
    )
    
    confirm_password_field = ft.TextField(
        label="Confirmer le mot de passe", 
        prefix_icon=ft.Icons.LOCK, password=True, can_reveal_password=True, border_radius=8
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
        label="Adresse (optionnel)", prefix_icon=ft.Icons.LOCATION_ON, 
        border_radius=8, multiline=True, min_lines=2,
        helper_text="5 à 200 caractères"
    )

    error_text = ft.Text("", color=Colors.ERROR, size=13, visible=False)
    loading = ft.ProgressRing(visible=False, width=20, height=20)

    # --- VALIDATION ---
    def validate_form() -> str | None:
        # Champs obligatoires
        if not first_name_field.value.strip():
            return "Le prénom est obligatoire."
        if not last_name_field.value.strip():
            return "Le nom est obligatoire."
        if not email_field.value.strip():
            return "L'email est obligatoire."
        if not birth_date_field.value.strip():
            return "La date de naissance est obligatoire."

        # Validation regex
        if not re.match(r"^[a-zA-ZÀ-ÿ\s\-']{2,50}$", first_name_field.value.strip()):
            return "Prénom invalide (2-50 caractères, lettres uniquement)."
        if not re.match(r"^[a-zA-ZÀ-ÿ\s\-']{2,50}$", last_name_field.value.strip()):
            return "Nom invalide (2-50 caractères, lettres uniquement)."
        if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email_field.value.strip()):
            return "Format d'email invalide."
        if not re.match(r"^(04|05|06)\d{7}$", phone_field.value.strip()):
            return "Téléphone invalide (9 chiffres, commence par 04, 05 ou 06)."

        # Validation mot de passe
        if password_field.value or confirm_password_field.value:
            pwd = password_field.value
            if len(pwd) < 8 or not re.search(r"[A-Z]", pwd) or not re.search(r"[a-z]", pwd) or not re.search(r"\d", pwd) or not re.search(r"[!@#$%^&*(),.?\":{}|<>]", pwd):
                return "Le mot de passe ne respecte pas les critères de sécurité (min 8 car., 1 maj, 1 min, 1 chiffre, 1 spécial)."
            if pwd != confirm_password_field.value:
                return "Les mots de passe ne correspondent pas."

        # Validation username si fourni
        if username_field.value.strip():
            if not re.match(r"^[a-zA-Z0-9_]{4,30}$", username_field.value.strip()):
                return "Nom d'utilisateur invalide (4-30 caractères alphanumériques ou _)."

        return None

    def on_add(e):
        error = validate_form()
        if error:
            error_text.value = f"❌ {error}"
            error_text.visible = True
            page.update()
            return

        error_text.visible = False
        loading.visible = True
        page.update()

        try:
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
            response = auth.api.create_internal_user(payload)
            
            username = response.get("username", "N/A") if isinstance(response, dict) else "N/A"
            temp_pwd = response.get("temporary_password") if isinstance(response, dict) else None
            
            msg = f"✅ Utilisateur créé avec succès — identifiant : {username}"
            if temp_pwd:
                msg += f" — mot de passe temporaire : {temp_pwd}"
            
            sb = ft.SnackBar(
                content=ft.Text(msg, color=Colors.TEXT_ON_DARK),
                bgcolor="#496042",
                duration=5000,
            )
            page.snack_bar = sb
            sb.open = True
            page.update()
            
            import asyncio
            async def redirect():
                await asyncio.sleep(2)
                page.go("/users")
            page.run_task(redirect)
            
        except ApiError as exc:
            loading.visible = False
            error_text.value = f"❌ Échec : {exc.message}"
            error_text.visible = True
            page.update()

    submit_button = ft.ElevatedButton(
        content=ft.Row([
            ft.Icon(ft.Icons.PERSON_ADD, color=Colors.TEXT_ON_DARK, size=18), 
            ft.Text("Créer l'utilisateur", color=Colors.TEXT_ON_DARK, weight=ft.FontWeight.BOLD)
        ], spacing=8, alignment=ft.MainAxisAlignment.CENTER),
        style=ft.ButtonStyle(bgcolor=Colors.PRIMARY),
        width=float("inf"),
        height=50,
        on_click=on_add
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
                ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: page.go("/users")),
                ft.Text("Nouvel Utilisateur", style=heading_style(size=22)),
            ]),
            ft.Container(height=10),
            ft.Text(
                "Créez un compte pour un utilisateur. Les champs marqués * sont obligatoires.",
                size=13, color=Colors.NEUTRAL,
            ),
            ft.Container(height=20),
            ft.Container(
                content=ft.Column([
                    ft.Text("Informations du compte", style=heading_style(size=16)),
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
                padding=24, bgcolor="#FFFFFF", border_radius=12, width=800 if device != "mobile" else None,
            ),
        ],
        bgcolor=Colors.BACKGROUND,
        padding=16 if device == "mobile" else 32,
    )