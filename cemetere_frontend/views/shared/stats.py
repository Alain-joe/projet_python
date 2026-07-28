"""
views/shared/stats.py — Composants KPI réutilisables.
Compatible Flet 0.86.0
"""

from __future__ import annotations

import flet as ft

from core.theme import Colors, FONT_DISPLAY


def kpi_card(
    label: str,
    value: str,
    icon: str,
    accent: str = Colors.PRIMARY,
    subtitle: str | None = None,
) -> ft.Control:
    """Carte KPI compacte."""
    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Container(
                            content=ft.Icon(icon, color=Colors.TEXT_ON_DARK, size=18),
                            bgcolor=accent,
                            width=32,
                            height=32,
                            border_radius=8,
                            alignment=ft.alignment.Alignment(0, 0),
                        ),
                        ft.Text(label, size=13, color=Colors.NEUTRAL),
                    ],
                    spacing=10,
                ),
                ft.Text(
                    value,
                    size=28,
                    font_family=FONT_DISPLAY,
                    weight=ft.FontWeight.W_600,
                    color=Colors.TEXT,
                ),
                ft.Text(subtitle, size=11, color=Colors.NEUTRAL) if subtitle else ft.Container(height=0),
            ],
            spacing=6,
        ),
        padding=18,
        bgcolor="#FFFFFF",
        border_radius=10,
        border=ft.Border(
            left=ft.BorderSide(1, Colors.BORDER),
            right=ft.BorderSide(1, Colors.BORDER),
            top=ft.BorderSide(1, Colors.BORDER),
            bottom=ft.BorderSide(1, Colors.BORDER),
        ),
    )


def kpi_row_placeholder(count: int = 4) -> ft.ResponsiveRow:
    """Squelette de chargement."""
    return ft.ResponsiveRow(
        [
            ft.Container(
                content=ft.Container(
                    bgcolor=Colors.BORDER,
                    border_radius=10,
                    height=110,
                ),
                col={"sm": 12, "md": 6, "lg": 12 // count},
            )
            for _ in range(count)
        ],
        spacing=16,
        run_spacing=16,
    )


def stat_line(label: str, value: str) -> ft.Row:
    """Ligne simple label/valeur."""
    return ft.Row(
        [
            ft.Text(label, color=Colors.NEUTRAL, size=13),
            ft.Text(value, weight=ft.FontWeight.W_600, size=13),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )