"""
views/auth/login.py — Écran de connexion moderne et épuré.
CORRECTION : Mise en page responsive — la carte et les champs étaient en
largeur fixe (450px / 400px), ce qui débordait sur un écran de téléphone
(souvent 360-390px de large). Largeur désormais calculée selon le device.
"""

import flet as ft

from core.auth import AuthState
from core.theme import Colors, heading_style
from views.shared.navigation import get_page_width, get_device_type


def build_login_view(page: ft.Page, auth: AuthState) -> ft.View:
    device = get_device_type(get_page_width(page))
    is_mobile = device == "mobile"

    card_width = None if is_mobile else 450
    field_width = None if is_mobile else 400
    button_width = None if is_mobile else 400

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

    btn_content_normal = ft.Row([
        ft.Icon(ft.Icons.LOGIN, color=Colors.TEXT_ON_DARK),
        ft.Text("Se connecter", color=Colors.TEXT_ON_DARK, weight=ft.FontWeight.BOLD)
    ], alignment=ft.MainAxisAlignment.CENTER, spacing=10)

    btn_content_loading = ft.Row([
        ft.ProgressRing(width=20, height=20, stroke_width=2, color=Colors.TEXT_ON_DARK),
        ft.Text("Connexion...", color=Colors.TEXT_ON_DARK, weight=ft.FontWeight.BOLD)
    ], alignment=ft.MainAxisAlignment.CENTER, spacing=10)

    # ✅ CORRECTION : width=400 fixe -> button_width (None sur mobile = pleine largeur du parent)
    login_button = ft.ElevatedButton(
        content=btn_content_normal,
        width=button_width,
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

    # ✅ CORRECTION : width=450 fixe -> card_width (None sur mobile), padding réduit
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
                    size=24 if is_mobile else 28,
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
                    expand=is_mobile,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=0,
        ),
        padding=20 if is_mobile else 40,
        bgcolor="#FFFFFF",
        border_radius=20,
        width=card_width,
        shadow=ft.BoxShadow(
            spread_radius=0,
            blur_radius=20,
            color="#0000001A",
        ),
    )

    return ft.View(
        route="/login",
        controls=[
            ft.Container(
                content=login_card,
                alignment=ft.alignment.Alignment(0, 0),
                expand=True,
                # ✅ Marge horizontale sur mobile pour éviter que la carte touche les bords
                padding=ft.Padding(left=16, right=16, top=16, bottom=16) if is_mobile else 0,
            )
        ],
        bgcolor=Colors.BACKGROUND,
        padding=0,
        scroll=ft.ScrollMode.AUTO,
    )