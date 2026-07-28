"""
core/theme.py — Thème global, couleurs, breakpoints, polices et utilitaires de mise en page.
Compatible Flet 0.86.0
"""

from __future__ import annotations

import flet as ft


# ==============================================================================
# PALETTE DE COULEURS (cohérente avec la maquette Cimetière Connect)
# ==============================================================================
class Colors:
    PRIMARY = "#496042"          # Vert cimetière
    SECONDARY = "#8B6B3F"        # Marron terre
    ACCENT = "#2E7D9A"           # Bleu institutionnel
    BACKGROUND = "#F5F3EE"       # Beige clair (fond général)
    SURFACE = "#FFFFFF"          # Blanc (cartes, sidebar)
    BORDER = "#E5E2D9"           # Beige moyen (bordures)
    TEXT = "#1A2B4C"             # Bleu très foncé (texte principal)
    TEXT_ON_DARK = "#FFFFFF"     # Blanc sur fond sombre
    NEUTRAL = "#6B7280"          # Gris neutre (textes secondaires)
    ERROR = "#C62828"            # Rouge erreur
    SUCCESS = "#2E7D32"          # Vert succès
    WARNING = "#F9A825"          # Orange avertissement


# ==============================================================================
# ✅ POLICES GLOBALES (constantes attendues par les vues)
# ==============================================================================
FONT_DISPLAY = "Segoe UI"        # Police principale (titres, KPI, dashboard)
FONT_BODY = "Segoe UI"           # Police corps de texte
FONT_MONO = "Consolas"           # Police monospace (codes, IDs de caveaux)


# ==============================================================================
# BREAKPOINTS RESPONSIVE
# ==============================================================================
class Breakpoints:
    MOBILE_MAX = 768      # <= 767px = mobile
    TABLET_MAX = 1199     # 768-1199px = tablette
    # >= 1200px = desktop


# ==============================================================================
# UTILITAIRES DE MISE EN PAGE
# ==============================================================================

def get_device_type(width: float | int | None) -> str:
    """Détermine le type d'appareil à partir de la largeur."""
    width = width or 1200
    if width < Breakpoints.MOBILE_MAX:
        return "mobile"
    if width < Breakpoints.TABLET_MAX:
        return "tablet"
    return "desktop"


def heading_style(size: int = 20, color: str = Colors.TEXT) -> ft.TextStyle:
    """Style standard pour les titres."""
    return ft.TextStyle(
        size=size,
        weight=ft.FontWeight.W_700,
        color=color,
        font_family=FONT_DISPLAY,
    )


def card_style() -> dict:
    """Style réutilisable pour les cartes (conteneurs blancs)."""
    return {
        "bgcolor": Colors.SURFACE,
        "border_radius": 12,
        "padding": 20,
        "shadow": ft.BoxShadow(spread_radius=0, blur_radius=8, color="#00000012"),
    }


def primary_button(text: str, icon: str | None = None, on_click=None) -> ft.ElevatedButton:
    """Bouton primaire standardisé."""
    content = ft.Row(
        [
            ft.Icon(icon, color=Colors.TEXT_ON_DARK, size=18) if icon else None,
            ft.Text(text, color=Colors.TEXT_ON_DARK, weight=ft.FontWeight.W_600, font_family=FONT_DISPLAY),
        ],
        spacing=8,
        alignment=ft.MainAxisAlignment.CENTER,
    )
    return ft.ElevatedButton(
        content=content,
        style=ft.ButtonStyle(bgcolor=Colors.PRIMARY),
        on_click=on_click,
    )


def secondary_button(text: str, icon: str | None = None, on_click=None) -> ft.TextButton:
    """Bouton secondaire standardisé."""
    content = ft.Row(
        [
            ft.Icon(icon, color=Colors.PRIMARY, size=18) if icon else None,
            ft.Text(text, color=Colors.PRIMARY, font_family=FONT_DISPLAY),
        ],
        spacing=8,
        alignment=ft.MainAxisAlignment.CENTER,
    )
    return ft.TextButton(content=content, on_click=on_click)


# ==============================================================================
# COULEUR SELON STATUT MÉTIER
# ==============================================================================

def status_color(status: str) -> str:
    """Retourne une couleur selon un statut métier."""
    status = str(status).lower()
    colors = {
        # Tombes / Caveaux
        "available": Colors.SUCCESS, "libre": Colors.SUCCESS, "free": Colors.SUCCESS,
        "occupied": Colors.ERROR, "occupée": Colors.ERROR, "occupe": Colors.ERROR,
        "reserved": Colors.WARNING, "réservée": Colors.WARNING, "reserve": Colors.WARNING,
        "non_exploitable": Colors.NEUTRAL, "non exploitable": Colors.NEUTRAL,
        # Réservations
        "pending": Colors.WARNING, "confirmed": Colors.SUCCESS, "cancelled": Colors.NEUTRAL, "annule": Colors.NEUTRAL,
        # Paiements / Factures
        "paid": Colors.SUCCESS, "payée": Colors.SUCCESS, "unpaid": Colors.ERROR, "impayée": Colors.ERROR, "overdue": Colors.ERROR,
        # Concessions
        "active": Colors.SUCCESS, "expired": Colors.ERROR, "resiliee": Colors.NEUTRAL,
        # Exhumations
        "approved": Colors.SUCCESS, "rejected": Colors.ERROR, "completed": Colors.SUCCESS,
        # Utilisateurs
        "inactive": Colors.NEUTRAL,
        # Alertes
        "critical": Colors.ERROR, "warning": Colors.WARNING, "info": Colors.ACCENT,
    }
    return colors.get(status, Colors.NEUTRAL)


# ==============================================================================
# APPLICATION DU THÈME GLOBAL (Compatible Flet 0.86.0)
# ==============================================================================

def apply_theme(page: ft.Page, dark: bool = False) -> None:
    """Applique le thème global à l'application Flet au démarrage."""
    page.theme_mode = ft.ThemeMode.DARK if dark else ft.ThemeMode.LIGHT

    if dark:
        page.theme = ft.Theme(
            color_scheme=ft.ColorScheme(
                primary=Colors.PRIMARY,
                secondary=Colors.SECONDARY,
                tertiary=Colors.ACCENT,
                on_primary=Colors.TEXT_ON_DARK,
                on_secondary=Colors.TEXT_ON_DARK,
                error=Colors.ERROR,
            ),
            text_theme=ft.TextTheme(
                body_medium=ft.TextStyle(font_family=FONT_DISPLAY, size=14, color="#FFFFFF"),
                title_large=ft.TextStyle(font_family=FONT_DISPLAY, size=22, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                title_medium=ft.TextStyle(font_family=FONT_DISPLAY, size=18, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
            ),
        )
        page.bgcolor = "#121212"
        page.window.bgcolor = "#121212"
    else:
        page.theme = ft.Theme(
            color_scheme=ft.ColorScheme(
                primary=Colors.PRIMARY,
                secondary=Colors.SECONDARY,
                tertiary=Colors.ACCENT,
                on_primary=Colors.TEXT_ON_DARK,
                on_secondary=Colors.TEXT_ON_DARK,
                error=Colors.ERROR,
            ),
            text_theme=ft.TextTheme(
                body_medium=ft.TextStyle(font_family=FONT_DISPLAY, size=14, color=Colors.TEXT),
                title_large=ft.TextStyle(font_family=FONT_DISPLAY, size=22, weight=ft.FontWeight.BOLD, color=Colors.TEXT),
                title_medium=ft.TextStyle(font_family=FONT_DISPLAY, size=18, weight=ft.FontWeight.BOLD, color=Colors.TEXT),
            ),
            page_transitions=ft.PageTransitionsTheme(
                android=ft.PageTransitionTheme.OPEN_UPWARDS,
                ios=ft.PageTransitionTheme.CUPERTINO,
                macos=ft.PageTransitionTheme.FADE_UPWARDS,
                windows=ft.PageTransitionTheme.OPEN_UPWARDS,
                linux=ft.PageTransitionTheme.ZOOM,
            ),
        )
        page.bgcolor = Colors.BACKGROUND
        page.window.bgcolor = Colors.BACKGROUND

    page.padding = 0
    page.spacing = 0