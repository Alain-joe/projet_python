"""
components/grave_marker.py — Élément signature de l'app : une petite
"stèle" (rectangle vertical arrondi) colorée selon le statut du caveau.

Réutilisé partout où un caveau est représenté :
  - views/map/view.py       -> marker sur la carte SIG (2.3)
  - components/data_table.py -> puce de statut dans les tableaux
  - views/dashboard/*.py    -> légende, listes de réservations

Un seul composant = un seul endroit à modifier si le design du statut
doit changer un jour.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import flet as ft

from core.theme import Colors, FONT_MONO, status_color


# ✅ CORRIGÉ : Clés alignées sur le backend (anglais) pour cohérence avec theme.py
STATUS_LABELS = {
    "available": "Disponible",
    "reserved": "Réservé",
    "occupied": "Occupé",
    "non_exploitable": "Non exploitable",
}


@dataclass
class GraveMarkerData:
    grave_id: int
    numero: str  # identifiant du caveau, ex: "A-014"
    status: str  # "available" | "reserved" | "occupied" | "non_exploitable"


def _status_label(status: str) -> str:
    return STATUS_LABELS.get((status or "").lower(), "Statut inconnu")


def grave_marker(
    data: GraveMarkerData,
    size: str = "medium",  # "small" (tableau) | "medium" (liste) | "large" (carte)
    show_label: bool = True,
    on_click: Callable[[GraveMarkerData], None] | None = None,
) -> ft.Control:
    """
    Construit la "stèle" miniature. Utiliser show_label=False pour un usage
    dense (ex: grille de caveaux avec des centaines d'items) et n'afficher
    le numéro qu'au survol/tap via un Tooltip.
    """
    dims = {
        "small": {"w": 14, "h": 18, "radius": 3, "font": 0},
        "medium": {"w": 22, "h": 30, "radius": 4, "font": 11},
        "large": {"w": 30, "h": 42, "radius": 6, "font": 13},
    }[size]

    color = status_color(data.status)

    stele = ft.Container(
        width=dims["w"],
        height=dims["h"],
        bgcolor=color,
        border_radius=ft.border_radius.only(
            top_left=dims["radius"],
            top_right=dims["radius"],
            bottom_left=1,
            bottom_right=1,
        ),
        border=ft.border.all(1, Colors.TEXT),
        tooltip=f"{data.numero} — {_status_label(data.status)}",
        ink=on_click is not None,
        on_click=(lambda _: on_click(data)) if on_click else None,
    )

    if not show_label:
        return stele

    label = ft.Text(
        data.numero,
        size=dims["font"] or 10,
        font_family=FONT_MONO,
        color=Colors.TEXT,
    )

    return ft.Column(
        [stele, label],
        spacing=2,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        tight=True,
    )


def status_legend() -> ft.Control:
    """Légende du code couleur, à afficher sur la carte et les dashboards
    (le cahier définit explicitement ces 4 états, section 2.3)."""
    items = []
    for status, label in STATUS_LABELS.items():
        items.append(
            ft.Row(
                [
                    ft.Container(
                        width=12,
                        height=12,
                        bgcolor=status_color(status),
                        border_radius=3,
                        border=ft.border.all(1, Colors.TEXT),
                    ),
                    ft.Text(label, size=12, color=Colors.TEXT),
                ],
                spacing=6,
            )
        )
    return ft.Row(items, spacing=16, wrap=True)