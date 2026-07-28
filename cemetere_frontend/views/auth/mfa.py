"""
views/auth/mfa.py — Saisie du code OTP reçu par email.
Design moderne et épuré (cohérent avec login.py).
"""

import flet as ft

from core.auth import AuthState, Role
from core.theme import Colors, heading_style


def build_mfa_view(page: ft.Page, auth: AuthState) -> ft.View:
    # Vérification de sécurité
    if auth._pending_user_id is None and not auth.is_authenticated:
        page.go("/login")
        return ft.View(route="/mfa", controls=[])

    # Champ de saisie du code
    code_field = ft.TextField(
        label="Code à 6 chiffres",
        hint_text="Entrez le code reçu par email",
        prefix_icon=ft.Icons.NUMBERS,
        keyboard_type=ft.KeyboardType.NUMBER,
        autofocus=True,
        max_length=6,
        text_align=ft.TextAlign.CENTER,
        border_radius=12,
        filled=True,
        bgcolor=Colors.BACKGROUND,
        content_padding=15,
        expand=True,
    )
    
    error_text = ft.Text("", color=Colors.ERROR, size=13, visible=False)
    
    # Contenu du bouton (normal vs loading)
    btn_content_normal = ft.Row([
        ft.Icon(ft.Icons.CHECK, color=Colors.TEXT_ON_DARK),
        ft.Text("Valider", color=Colors.TEXT_ON_DARK, weight=ft.FontWeight.BOLD)
    ], alignment=ft.MainAxisAlignment.CENTER, spacing=10)
    
    btn_content_loading = ft.Row([
        ft.ProgressRing(width=20, height=20, stroke_width=2, color=Colors.TEXT_ON_DARK),
        ft.Text("Vérification...", color=Colors.TEXT_ON_DARK, weight=ft.FontWeight.BOLD)
    ], alignment=ft.MainAxisAlignment.CENTER, spacing=10)

    verify_button = ft.ElevatedButton(
        content=btn_content_normal,
        width=400,
        height=50,
        style=ft.ButtonStyle(
            bgcolor=Colors.PRIMARY,
            shape=ft.RoundedRectangleBorder(radius=25),
            padding=15,
        ),
    )
    
    # Bouton renvoyer le code
    resend_button = ft.TextButton(
        content=ft.Row([
            ft.Icon(ft.Icons.EMAIL, size=16, color=Colors.PRIMARY),
            ft.Text("Renvoyer le code", color=Colors.PRIMARY)
        ], spacing=5),
    )

    def set_loading(is_loading: bool) -> None:
        verify_button.disabled = is_loading
        resend_button.disabled = is_loading
        verify_button.content = btn_content_loading if is_loading else btn_content_normal
        page.update()

    def show_error(message: str) -> None:
        error_text.value = message
        error_text.visible = bool(message)
        page.update()

    def redirect_after_success() -> None:
        mapping = {
            Role.ADMIN: "/dashboard/admin",
            Role.SECRETARIAT: "/dashboard/admin",
            Role.AGENT: "/dashboard/agent",
            Role.CLIENT: "/dashboard/client",
        }
        page.go(mapping.get(auth.role, "/dashboard/client"))

    def on_verify_click(_: ft.ControlEvent) -> None:
        code = (code_field.value or "").strip()
        if not code or len(code) != 6:
            show_error("Veuillez saisir le code à 6 chiffres.")
            return

        show_error("")
        set_loading(True)
        result = auth.verify_mfa(code)
        set_loading(False)

        if not result.success:
            show_error(result.message or "Code invalide ou expiré.")
            code_field.value = ""
            page.update()
            return

        redirect_after_success()

    def on_resend_click(_: ft.ControlEvent) -> None:
        # Simulation d'envoi (à connecter au backend plus tard)
        show_error("Un nouveau code vous a été envoyé par email.")
        code_field.value = ""

    verify_button.on_click = on_verify_click
    code_field.on_submit = on_verify_click
    resend_button.on_click = on_resend_click

    # Carte de vérification MFA
    mfa_card = ft.Container(
        content=ft.Column(
            [
                ft.Icon(
                    ft.Icons.SHIELD_OUTLINED,
                    size=60,
                    color=Colors.PRIMARY,
                ),
                ft.Container(height=10),
                ft.Text(
                    "Vérification en deux étapes",
                    size=28,
                    weight=ft.FontWeight.BOLD,
                    color=Colors.TEXT,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(
                    "Un code à 6 chiffres vient de vous être envoyé par email.",
                    size=14,
                    color=Colors.NEUTRAL,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(height=30),
                code_field,
                ft.Container(height=10),
                error_text,
                ft.Container(height=20),
                ft.Row(
                    [verify_button],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                ft.Container(height=15),
                ft.Row(
                    [resend_button],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=0,
        ),
        padding=40,
        bgcolor="#FFFFFF",  # ✅ CORRECTION : Valeur hexadécimale directe
        border_radius=20,
        width=450,
        shadow=ft.BoxShadow(
            spread_radius=0,
            blur_radius=20,
            color="#0000001A",  # 10% d'opacité noire
        ),
    )

    return ft.View(
        route="/mfa",
        controls=[
            ft.Container(
                content=mfa_card,
                alignment=ft.alignment.Alignment(0, 0),
                expand=True,
            )
        ],
        bgcolor=Colors.BACKGROUND,
        padding=0,
    )