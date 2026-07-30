"""
views/auth/register.py — Page d'inscription publique (Client).
Compatible Flet 0.86.3
Appelle l'endpoint POST /api/users/register/ du backend.
CORRECTION : Remplacement de helper_text par hint_text (compatible Flet 0.86.3).
"""
from __future__ import annotations
import flet as ft
from core.theme import Colors, get_device_type, heading_style
from core.api import ApiError


def build_register_view(page: ft.Page, auth) -> ft.View:
    """Page d'inscription publique pour les clients."""
    
    width = getattr(page, 'window', page).width if hasattr(page, 'window') else (getattr(page, 'width', 1200) or 1200)
    device = get_device_type(width)
    is_mobile = device == "mobile"

    # Champs du formulaire
    first_name_field = ft.TextField(label="Prénom *", border_radius=8, expand=True)
    last_name_field = ft.TextField(label="Nom *", border_radius=8, expand=True)
    email_field = ft.TextField(label="Email *", keyboard_type=ft.KeyboardType.EMAIL, border_radius=8, expand=True)
    phone_field = ft.TextField(label="Téléphone (06/05/04...)", keyboard_type=ft.KeyboardType.PHONE, border_radius=8, expand=True)
    
    # ✅ CORRECTION : hint_text au lieu de helper_text
    username_field = ft.TextField(label="Nom d'utilisateur *", border_radius=8, expand=True, hint_text="4 à 30 caractères alphanumériques")
    password_field = ft.TextField(label="Mot de passe *", password=True, can_reveal_password=True, border_radius=8, expand=True, hint_text="Min. 8 car. : 1 maj, 1 min, 1 chiffre, 1 spécial")
    confirm_field = ft.TextField(label="Confirmer le mot de passe *", password=True, can_reveal_password=True, border_radius=8, expand=True)

    error_text = ft.Text("", color=Colors.ERROR, size=13, visible=False)
    success_text = ft.Text("", color=Colors.PRIMARY, size=13, visible=False)
    loading = ft.ProgressRing(visible=False, width=24, height=24)

    def on_register(e):
        error_text.visible = False
        success_text.visible = False

        # Validations
        if not all([
            first_name_field.value, last_name_field.value,
            email_field.value, username_field.value,
            password_field.value, confirm_field.value
        ]):
            error_text.value = "❌ Tous les champs marqués * sont obligatoires."
            error_text.visible = True
            page.update()
            return

        if password_field.value != confirm_field.value:
            error_text.value = "❌ Les mots de passe ne correspondent pas."
            error_text.visible = True
            page.update()
            return

        if len(password_field.value) < 8:
            error_text.value = "❌ Le mot de passe doit contenir au moins 8 caractères."
            error_text.visible = True
            page.update()
            return

        loading.visible = True
        page.update()

        try:
            payload = {
                "username": username_field.value.strip().lower(),
                "first_name": first_name_field.value.strip().capitalize(),
                "last_name": last_name_field.value.strip().capitalize(),
                "email": email_field.value.strip().lower(),
                "phone": phone_field.value.strip() or "",
                "password": password_field.value,
            }
            
            # Appel à l'endpoint backend
            from core.api import ApiClient, TokenProvider
            client = ApiClient(TokenProvider())
            response = client.post("/users/register/", json=payload)

            loading.visible = False
            success_text.value = f"✅ Compte créé avec succès ! Identifiant : {response.get('username')}. Redirection vers la connexion..."
            success_text.visible = True
            page.update()

            # Redirection vers la connexion après 2 secondes
            import asyncio
            async def redirect():
                await asyncio.sleep(2)
                page.go("/login")
            page.run_task(redirect)

        except ApiError as exc:
            loading.visible = False
            error_text.value = f"❌ {exc.message}"
            error_text.visible = True
            page.update()
        except Exception as exc:
            loading.visible = False
            error_text.value = f"❌ Erreur : {exc}"
            error_text.visible = True
            page.update()

    # Construction du formulaire
    form_content = ft.Column([
        ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: page.go("/welcome")),
        ft.Container(height=10),
        ft.Icon(ft.Icons.PERSON_ADD, size=48, color=Colors.PRIMARY),
        ft.Text("Créer un compte client", style=heading_style(size=22)),
        ft.Text("Remplissez le formulaire pour créer votre espace personnel", size=13, color=Colors.NEUTRAL),
        ft.Container(height=20),
        ft.Row([first_name_field, last_name_field], spacing=12),
        ft.Container(height=10),
        email_field,
        ft.Container(height=10),
        phone_field,
        ft.Container(height=10),
        username_field,
        ft.Container(height=10),
        password_field,
        ft.Container(height=10),
        confirm_field,
        ft.Container(height=20),
        error_text,
        success_text,
        ft.ElevatedButton(
            content=ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE, color=Colors.TEXT_ON_DARK),
                ft.Text("Crréer mon compte", color=Colors.TEXT_ON_DARK, weight=ft.FontWeight.BOLD),
                loading,
            ], spacing=8),
            style=ft.ButtonStyle(bgcolor=Colors.PRIMARY),
            width=float("inf"),
            height=50,
            on_click=on_register,
        ),
        ft.Container(height=16),
        ft.Row([
            ft.Text("Déjà un compte ?", size=13, color=Colors.NEUTRAL),
            ft.TextButton("Se connecter", on_click=lambda _: page.go("/login")),
        ], alignment=ft.MainAxisAlignment.CENTER),
    ], spacing=0, scroll=ft.ScrollMode.AUTO)

    return ft.View(
        route="/register",
        controls=[
            ft.Container(
                content=form_content,
                padding=24 if not is_mobile else 16,
                bgcolor="#FFFFFF",
                border_radius=16 if not is_mobile else 0,
                width=600 if not is_mobile else None,
                shadow=ft.BoxShadow(spread_radius=0, blur_radius=16, color="#0000000F") if not is_mobile else None,
            ),
        ],
        bgcolor=Colors.BACKGROUND,
        padding=16 if is_mobile else 32,
        scroll=ft.ScrollMode.AUTO,
        vertical_alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )