"""
views/auth/login.py — Écran de connexion moderne et épuré.
"""

import flet as ft

from core.auth import AuthState
from core.theme import Colors, heading_style


def build_login_view(page: ft.Page, auth: AuthState) -> ft.View:
    # Champs de saisie avec icônes
    username_field = ft.TextField(
        label="Nom d'utilisateur",
        hint_text="Entrez votre nom d'utilisateur",
        prefix_icon=ft.Icons.PERSON_OUTLINED,
        keyboard_type=ft.KeyboardType.EMAIL,
        autofocus=True,
        border_radius=12,
        filled=True,
        bgcolor=Colors.BACKGROUND,
        content_padding=15,
        expand=True,
    )
    
    password_field = ft.TextField(
        label="Mot de passe",
        hint_text="Entrez votre mot de passe",
        prefix_icon=ft.Icons.LOCK_OUTLINE,
        password=True,
        can_reveal_password=True,
        border_radius=12,
        filled=True,
        bgcolor=Colors.BACKGROUND,
        content_padding=15,
        expand=True,
    )
    
    error_text = ft.Text("", color=Colors.ERROR, size=13, visible=False)
    loading = ft.ProgressRing(visible=False, width=20, height=20, stroke_width=2, color=Colors.TEXT_ON_DARK)
    
    # Contenu du bouton (normal vs loading)
    btn_content_normal = ft.Row([
        ft.Icon(ft.Icons.LOGIN, color=Colors.TEXT_ON_DARK),
        ft.Text("Se connecter", color=Colors.TEXT_ON_DARK, weight=ft.FontWeight.BOLD)
    ], alignment=ft.MainAxisAlignment.CENTER, spacing=10)
    
    btn_content_loading = ft.Row([
        ft.ProgressRing(width=20, height=20, stroke_width=2, color=Colors.TEXT_ON_DARK),
        ft.Text("Connexion...", color=Colors.TEXT_ON_DARK, weight=ft.FontWeight.BOLD)
    ], alignment=ft.MainAxisAlignment.CENTER, spacing=10)

    login_button = ft.ElevatedButton(
        content=btn_content_normal,
        width=400,
        height=50,
        style=ft.ButtonStyle(
            bgcolor=Colors.PRIMARY,
            shape=ft.RoundedRectangleBorder(radius=25),
            padding=15,
        ),
    )
    
    def set_loading(is_loading: bool) -> None:
        loading.visible = is_loading
        login_button.disabled = is_loading
        login_button.content = btn_content_loading if is_loading else btn_content_normal
        page.update()

    def show_error(message: str) -> None:
        error_text.value = message
        error_text.visible = bool(message)
        page.update()

    def on_login_click(_: ft.ControlEvent) -> None:
        username = username_field.value.strip() if username_field.value else ""
        password = password_field.value or ""

        if not username or not password:
            show_error("Veuillez remplir tous les champs.")
            return

        show_error("")
        set_loading(True)
        result = auth.login(username, password)
        set_loading(False)

        if not result.success:
            show_error(result.message or "Échec de la connexion. Vérifiez vos identifiants.")
            return

        if result.requires_mfa:
            page.go("/mfa")
        else:
            page.go("/dashboard/client")

    login_button.on_click = on_login_click
    password_field.on_submit = on_login_click

    # Carte de connexion principale
    login_card = ft.Container(
        content=ft.Column(
            [
                ft.Icon(
                    ft.Icons.ACCOUNT_BALANCE,
                    size=60,
                    color=Colors.PRIMARY,
                ),
                ft.Container(height=10),
                ft.Text(
                    "Gestion de Cimetière",
                    size=28,
                    weight=ft.FontWeight.BOLD,
                    color=Colors.TEXT,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(
                    "Connectez-vous pour accéder au système",
                    size=14,
                    color=Colors.NEUTRAL,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(height=30),
                username_field,
                ft.Container(height=15),
                password_field,
                ft.Container(height=10),
                error_text,
                ft.Container(height=20),
                ft.Row(
                    [login_button],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=0,
        ),
        padding=40,
        bgcolor="#FFFFFF",  # ✅ CORRECTION : Utilisation directe de la valeur hexadécimale
        border_radius=20,
        width=450,
        shadow=ft.BoxShadow(
            spread_radius=0,
            blur_radius=20,
            color="#0000001A",  # 10% d'opacité noire
        ),
    )

    return ft.View(
        route="/login",
        controls=[
            ft.Container(
                content=login_card,
                alignment=ft.alignment.Alignment(0, 0),
                expand=True,
            )
        ],
        bgcolor=Colors.BACKGROUND,
        padding=0,
    )