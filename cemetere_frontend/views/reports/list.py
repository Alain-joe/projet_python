"""
views/reports/list.py — Rapports et Statistiques.
Compatible Flet 0.86.0
"""
from __future__ import annotations
import os
import csv
import flet as ft
from datetime import datetime
from core.auth import AuthState
from core.theme import Colors, get_device_type, heading_style
from core.ui_utils import show_overlay


def _snack(page: ft.Page, message: str, bgcolor: str, duration: int = 3500) -> None:
    show_overlay(page, ft.SnackBar(content=ft.Text(message, size=13), bgcolor=bgcolor, duration=duration))


def _section_title(icon: str, text: str) -> ft.Row:
    return ft.Row(
        [
            ft.Container(
                content=ft.Icon(icon, size=18, color=Colors.TEXT_ON_DARK),
                bgcolor=Colors.PRIMARY,
                padding=8,
                border_radius=10,
            ),
            ft.Text(text, style=heading_style(size=18)),
        ],
        spacing=12,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def _card(content: ft.Control) -> ft.Container:
    # CORRECTION : si le contenu est un DataTable, on l'enveloppe dans un
    # Row scrollable horizontalement -> évite qu'elle se peigne en
    # gris/vide quand sa largeur de contenu dépasse celle du parent.
    wrapped = ft.Row([content], scroll=ft.ScrollMode.AUTO) if isinstance(content, ft.DataTable) else content
    return ft.Container(
        content=wrapped,
        padding=20,
        bgcolor="#FFFFFF",
        border_radius=16,
        border=ft.Border.all(1, Colors.BORDER),
        shadow=ft.BoxShadow(spread_radius=0, blur_radius=14, color="#0000000D"),
    )


def build_reports_view(page: ft.Page, auth: AuthState) -> ft.View:
    revenue_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Mois", weight=ft.FontWeight.BOLD, size=14)),
            ft.DataColumn(ft.Text("Revenu (FCFA)", weight=ft.FontWeight.BOLD, size=14, text_align=ft.TextAlign.RIGHT)),
        ],
        rows=[],
        column_spacing=20,
        data_row_max_height=45,
        border=ft.Border.all(1, Colors.BORDER),
        heading_row_height=45,
        heading_row_color="#F5F3EE",
        show_checkbox_column=False,
    )

    sections_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Section", weight=ft.FontWeight.BOLD, size=14)),
            ft.DataColumn(ft.Text("Total Caveaux", weight=ft.FontWeight.BOLD, size=14, text_align=ft.TextAlign.CENTER)),
            ft.DataColumn(ft.Text("Occupés", weight=ft.FontWeight.BOLD, size=14, text_align=ft.TextAlign.CENTER)),
            ft.DataColumn(ft.Text("Taux d'occupation", weight=ft.FontWeight.BOLD, size=14, text_align=ft.TextAlign.RIGHT)),
        ],
        rows=[],
        column_spacing=15,
        data_row_max_height=45,
        border=ft.Border.all(1, Colors.BORDER),
        heading_row_height=45,
        heading_row_color="#F5F3EE",
        show_checkbox_column=False,
    )

    def _load_data() -> None:
        loading.visible = True
        error_text.visible = False
        page.update()

        try:
            data = auth.api.get("/reports/dashboard")

            if isinstance(data, dict):
                rev_data = data.get("monthly_revenue", [])
                revenue_table.rows.clear()

                for item in rev_data:
                    month_str = str(item.get("month", "N/A"))[:7]
                    try:
                        dt = datetime.strptime(month_str, "%Y-%m")
                        month_name = dt.strftime("%B %Y").capitalize()
                    except ValueError:
                        month_name = month_str

                    total = float(item.get("total", item.get("amount", 0)))
                    revenue_table.rows.append(
                        ft.DataRow(cells=[
                            ft.DataCell(ft.Text(month_name, size=13)),
                            ft.DataCell(ft.Text(f"{total:,.0f}".replace(",", " "), size=13, text_align=ft.TextAlign.RIGHT)),
                        ])
                    )

                sec_data = data.get("sections", data.get("sections_stats", []))
                sections_table.rows.clear()

                for sec in sec_data:
                    name = sec.get("name", "N/A")
                    total = int(sec.get("total", sec.get("total_graves", 0)))
                    occupied = int(sec.get("occupied", sec.get("occupied_graves", 0)))
                    rate = sec.get("rate", (occupied / total * 100) if total > 0 else 0.0)

                    sections_table.rows.append(
                        ft.DataRow(cells=[
                            ft.DataCell(ft.Text(name, size=13)),
                            ft.DataCell(ft.Text(str(total), size=13, text_align=ft.TextAlign.CENTER)),
                            ft.DataCell(ft.Text(str(occupied), size=13, text_align=ft.TextAlign.CENTER)),
                            ft.DataCell(ft.Text(f"{rate:.1f} %", size=13, text_align=ft.TextAlign.RIGHT)),
                        ])
                    )

                if not revenue_table.rows and not sections_table.rows:
                    error_text.value = "Aucune donnée disponible dans les rapports."
                    error_text.visible = True
            else:
                error_text.value = "Format de réponse inattendu du serveur."
                error_text.visible = True

            # CORRECTION : diagnostic pour confirmer que les données
            # arrivent bien jusqu'aux DataTable.
            print(f"🔍 REPORTS : revenus={len(revenue_table.rows)} lignes | sections={len(sections_table.rows)} lignes")

        except Exception as exc:
            error_text.value = f"Erreur de chargement des rapports : {exc}"
            error_text.visible = True
        finally:
            loading.visible = False
            page.update()

    def export_to_csv(data_type: str) -> None:
        try:
            user_profile = os.environ.get("USERPROFILE", os.path.expanduser("~"))
            export_dir = os.path.join(user_profile, "Documents", "Cimetiere")
            os.makedirs(export_dir, exist_ok=True)

            if data_type == "revenue" and not revenue_table.rows:
                _snack(page, "⚠️ Aucune donnée à exporter pour les revenus", Colors.WARNING)
                return

            if data_type == "sections" and not sections_table.rows:
                _snack(page, "⚠️ Aucune donnée à exporter pour l'occupation", Colors.WARNING)
                return

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if data_type == "revenue":
                filename = f"Revenus_Mensuels_{timestamp}.csv"
                filepath = os.path.join(export_dir, filename)

                with open(filepath, mode='w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f, delimiter=';')
                    writer.writerow(["Mois", "Revenu (FCFA)"])
                    for row in revenue_table.rows:
                        mois = row.cells[0].content.value
                        revenu = row.cells[1].content.value
                        writer.writerow([mois, revenu])
            else:
                filename = f"Occupation_Sections_{timestamp}.csv"
                filepath = os.path.join(export_dir, filename)

                with open(filepath, mode='w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f, delimiter=';')
                    writer.writerow(["Section", "Total Caveaux", "Occupés", "Taux d'occupation"])
                    for row in sections_table.rows:
                        sec = row.cells[0].content.value
                        total = row.cells[1].content.value
                        occ = row.cells[2].content.value
                        taux = row.cells[3].content.value
                        writer.writerow([sec, total, occ, taux])

            _snack(page, f"✅ Export réussi ! Fichier : {filepath}", Colors.PRIMARY, duration=5000)

        except Exception as exc:
            _snack(page, f"❌ Erreur lors de l'export : {exc}", Colors.ERROR, duration=4000)

    loading = ft.ProgressRing(visible=True)
    error_text = ft.Text("", color=Colors.ERROR, size=13, visible=False)

    _load_data()
    device = get_device_type(page.window.width or 1200)

    return ft.View(
        route="/reports",
        controls=[
            ft.Text("Rapports et Statistiques", style=heading_style(size=22)),
            ft.Container(height=4),
            ft.Text("Vue d'ensemble des revenus et de l'occupation du cimetière.", size=13, color=Colors.NEUTRAL),
            ft.Container(height=16),
            error_text,
            loading,

            _section_title(ft.Icons.PAYMENTS, "Revenus Mensuels"),
            ft.Container(height=12),
            _card(revenue_table),
            ft.Container(height=15),
            ft.ElevatedButton(
                content=ft.Row(
                    [ft.Icon(ft.Icons.DOWNLOAD, size=18, color=Colors.TEXT_ON_DARK), ft.Text("Exporter les revenus en CSV", color=Colors.TEXT_ON_DARK, weight=ft.FontWeight.W_600)],
                    spacing=8, tight=True,
                ),
                style=ft.ButtonStyle(bgcolor=Colors.PRIMARY, shape=ft.RoundedRectangleBorder(radius=12)),
                height=46,
                on_click=lambda _: export_to_csv("revenue"),
            ),

            ft.Container(height=32),
            ft.Divider(height=1, color=Colors.BORDER),
            ft.Container(height=16),

            _section_title(ft.Icons.PIE_CHART, "Occupation par Section"),
            ft.Container(height=12),
            _card(sections_table),
            ft.Container(height=15),
            ft.ElevatedButton(
                content=ft.Row(
                    [ft.Icon(ft.Icons.DOWNLOAD, size=18, color=Colors.TEXT_ON_DARK), ft.Text("Exporter l'occupation en CSV", color=Colors.TEXT_ON_DARK, weight=ft.FontWeight.W_600)],
                    spacing=8, tight=True,
                ),
                style=ft.ButtonStyle(bgcolor=Colors.PRIMARY, shape=ft.RoundedRectangleBorder(radius=12)),
                height=46,
                on_click=lambda _: export_to_csv("sections"),
            ),
        ],
        bgcolor=Colors.BACKGROUND,
        padding=16 if device == "mobile" else 32,
    )