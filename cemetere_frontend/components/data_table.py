"""
components/data_table.py — Tableau générique responsive.
Compatible Flet 0.86.0
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import flet as ft

from core.theme import Colors, get_device_type


@dataclass
class ColumnDef:
    key: str
    label: str
    render: Callable[[Any], ft.Control] | None = None
    primary: bool = False


def _default_cell(value: Any) -> ft.Control:
    return ft.Text(str(value) if value is not None else "—", size=13)


def responsive_data_table(
    page: ft.Page,
    columns: list[ColumnDef],
    rows: list[dict],
    actions: Callable[[dict], list[ft.Control]] | None = None,
    empty_message: str = "Aucune donnée.",
) -> ft.Control:
    if not rows:
        return ft.Text(empty_message, color=Colors.NEUTRAL, italic=True)

    device = get_device_type(page.width or 1200)

    if device != "mobile":
        return _build_table(columns, rows, actions)
    return _build_cards(columns, rows, actions)


def _build_table(
    columns: list[ColumnDef],
    rows: list[dict],
    actions: Callable[[dict], list[ft.Control]] | None,
) -> ft.Control:
    data_columns = [ft.DataColumn(ft.Text(col.label, weight=ft.FontWeight.W_600)) for col in columns]
    if actions:
        data_columns.append(ft.DataColumn(ft.Text("")))

    data_rows = []
    for row in rows:
        cells = []
        for col in columns:
            value = row.get(col.key)
            control = col.render(value) if col.render else _default_cell(value)
            cells.append(ft.DataCell(control))
        if actions:
            cells.append(ft.DataCell(ft.Row(actions(row), spacing=4)))
        data_rows.append(ft.DataRow(cells=cells))

    return ft.Container(
        content=ft.DataTable(
            columns=data_columns,
            rows=data_rows,
            heading_row_color="#F5F3EE",
            border=ft.Border(
                left=ft.BorderSide(1, Colors.BORDER),
                right=ft.BorderSide(1, Colors.BORDER),
                top=ft.BorderSide(1, Colors.BORDER),
                bottom=ft.BorderSide(1, Colors.BORDER),
            ),
            border_radius=8,
            horizontal_lines=ft.border.BorderSide(1, Colors.BORDER),
        ),
        padding=ft.padding.only(bottom=8),
    )


def _build_cards(
    columns: list[ColumnDef],
    rows: list[dict],
    actions: Callable[[dict], list[ft.Control]] | None,
) -> ft.Control:
    primary_cols = [c for c in columns if c.primary] or columns[:1]
    detail_cols = [c for c in columns if c not in primary_cols]

    cards = []
    for row in rows:
        title_controls = []
        for col in primary_cols:
            value = row.get(col.key)
            control = col.render(value) if col.render else _default_cell(value)
            title_controls.append(control)

        detail_rows = []
        for col in detail_cols:
            value = row.get(col.key)
            control = col.render(value) if col.render else _default_cell(value)
            detail_rows.append(
                ft.Row(
                    [ft.Text(col.label, size=11, color=Colors.NEUTRAL), control],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                )
            )

        card_children = [ft.Row(title_controls, spacing=8)] + detail_rows
        if actions:
            card_children.append(ft.Row(actions(row), spacing=8, wrap=True))

        cards.append(
            ft.Container(
                content=ft.Column(card_children, spacing=6),
                padding=14,
                bgcolor="#FFFFFF",
                border_radius=8,
                border=ft.Border(
                    left=ft.BorderSide(1, Colors.BORDER),
                    right=ft.BorderSide(1, Colors.BORDER),
                    top=ft.BorderSide(1, Colors.BORDER),
                    bottom=ft.BorderSide(1, Colors.BORDER),
                ),
            )
        )

    return ft.Column(cards, spacing=10)