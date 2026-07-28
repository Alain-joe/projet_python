"""
views/reports/logs.py — Journal d'Audit (Logs).
Compatible Flet 0.86.0

CORRECTION APPLIQUÉE :
- Retrait de wrap=True sur le Row des filtres (search_field,
  days_dropdown, action_dropdown, module_dropdown, bouton
  Appliquer) : search_field a expand=True, ce qui est incompatible
  avec wrap=True sur Flutter (le Row devient un Wrap qui ne sait pas
  gérer un enfant expand) -> rendu invisible sans exception Python.
  Même cause que le bug corrigé dans views/reservations/list.py.
"""
from __future__ import annotations
import os
import csv
import flet as ft
from datetime import datetime
from core.auth import AuthState
from core.theme import Colors, get_device_type, heading_style
from core.ui_utils import show_overlay

ACTION_LABELS = {
    "create": "Création",
    "update": "Modification",
    "delete": "Suppression",
    "login": "Connexion",
    "status_change": "Changement de statut",
    "reject": "Rejet",
    "approve": "Approbation",
}

MODULE_LABELS = {
    "User": "Utilisateur",
    "Reservation": "Réservation",
    "Concession": "Concession",
    "Exhumation": "Exhumation",
    "Inhumation": "Inhumation",
    "Facture": "Finance",
    "Grave": "Caveau",
}


def build_audit_logs_view(page: ft.Page, auth: AuthState) -> ft.View:
    logs = []
    loading = ft.ProgressRing(visible=True)
    error_text = ft.Text("", color=Colors.ERROR, size=13, visible=False)
    empty_text = ft.Text("Aucun log trouvé pour ces critères.", color=Colors.NEUTRAL, italic=True, visible=False)

    logs_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Date", weight=ft.FontWeight.BOLD, size=13)),
            ft.DataColumn(ft.Text("Utilisateur", weight=ft.FontWeight.BOLD, size=13)),
            ft.DataColumn(ft.Text("Action", weight=ft.FontWeight.BOLD, size=13)),
            ft.DataColumn(ft.Text("Module", weight=ft.FontWeight.BOLD, size=13)),
            ft.DataColumn(ft.Text("Détails", weight=ft.FontWeight.BOLD, size=13)),
        ],
        rows=[],
        column_spacing=15,
        data_row_max_height=45,
        border=ft.Border.all(1, Colors.BORDER),
        heading_row_height=45,
        heading_row_color="#F5F3EE",
        show_checkbox_column=False,
    )

    search_field = ft.TextField(
        hint_text="Rechercher (utilisateur, détails...)",
        prefix_icon=ft.Icons.SEARCH,
        expand=True,
        border_radius=8,
        on_submit=lambda _: apply_filters(),
    )

    days_dropdown = ft.Dropdown(
        label="Période",
        value="30",
        options=[
            ft.DropdownOption("1", "Aujourd'hui"),
            ft.DropdownOption("7", "7 derniers jours"),
            ft.DropdownOption("30", "30 derniers jours"),
            ft.DropdownOption("90", "3 mois"),
        ],
        width=160,
    )

    action_dropdown = ft.Dropdown(
        label="Action",
        value="all",
        options=[ft.DropdownOption("all", "Toutes")] +
                [ft.DropdownOption(k, v) for k, v in ACTION_LABELS.items()],
        width=160,
    )

    module_dropdown = ft.Dropdown(
        label="Module",
        value="all",
        options=[ft.DropdownOption("all", "Tous")] +
                [ft.DropdownOption(k, v) for k, v in MODULE_LABELS.items()],
        width=160,
    )

    def load_logs() -> None:
        loading.visible = True
        error_text.visible = False
        empty_text.visible = False
        page.update()

        try:
            params = {"days": int(days_dropdown.value)}
            if action_dropdown.value != "all":
                params["action"] = action_dropdown.value
            if module_dropdown.value != "all":
                params["model_name"] = module_dropdown.value
            if search_field.value and search_field.value.strip():
                params["search"] = search_field.value.strip()

            response = auth.api.get("/audit/logs", params=params)

            if isinstance(response, dict):
                logs.clear()
                logs.extend(response.get("items", response.get("results", [])))
            elif isinstance(response, list):
                logs.clear()
                logs.extend(response)
            else:
                error_text.value = "Format de réponse inattendu du serveur."
                error_text.visible = True

            render_logs()
        except Exception as exc:
            error_text.value = f"Erreur de chargement : {exc}"
            error_text.visible = True
        finally:
            loading.visible = False
            page.update()

    def apply_filters():
        load_logs()

    def render_logs():
        logs_table.rows.clear()

        if not logs:
            empty_text.visible = True
        else:
            empty_text.visible = False
            for log in logs:
                ts_str = str(log.get("timestamp") or "")
                try:
                    dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    date_fmt = dt.strftime("%d/%m/%Y %H:%M")
                except Exception:
                    date_fmt = ts_str[:16] if ts_str else "N/A"

                user = str(log.get("user") or "Système")
                action_raw = str(log.get("action") or "unknown")
                action_lbl = ACTION_LABELS.get(action_raw, action_raw.capitalize())

                module_raw = str(log.get("model_name") or "Inconnu")
                module_lbl = MODULE_LABELS.get(module_raw, module_raw)

                details = str(log.get("details") or "")
                if len(details) > 60:
                    details = details[:57] + "..."

                logs_table.rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(date_fmt, size=12)),
                        ft.DataCell(ft.Text(user, size=12, weight=ft.FontWeight.W_500)),
                        ft.DataCell(ft.Text(action_lbl, size=12)),
                        ft.DataCell(ft.Text(module_lbl, size=12)),
                        ft.DataCell(ft.Text(details, size=12, color=Colors.NEUTRAL)),
                    ])
                )
        # CORRECTION : diagnostic pour confirmer que les données arrivent
        # jusqu'ici et que le DataTable contient bien des lignes.
        print(f"🔍 LOGS : {len(logs)} logs reçus | {len(logs_table.rows)} lignes dans la table")
        page.update()

    def export_to_csv():
        try:
            user_profile = os.environ.get("USERPROFILE", os.path.expanduser("~"))
            export_dir = os.path.join(user_profile, "Documents", "Cimetiere")
            os.makedirs(export_dir, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"Logs_Audit_{timestamp}.csv"
            filepath = os.path.join(export_dir, filename)

            with open(filepath, mode='w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerow(["Date", "Utilisateur", "Action", "Module", "Détails"])
                for log in logs:
                    ts_str = str(log.get("timestamp") or "")
                    try:
                        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                        date_fmt = dt.strftime("%d/%m/%Y %H:%M")
                    except Exception:
                        date_fmt = ts_str

                    user = str(log.get("user") or "Système")
                    action_raw = str(log.get("action") or "unknown")
                    action_lbl = ACTION_LABELS.get(action_raw, action_raw.capitalize())
                    module_raw = str(log.get("model_name") or "Inconnu")
                    module_lbl = MODULE_LABELS.get(module_raw, module_raw)
                    details = str(log.get("details") or "").replace(";", ",")

                    writer.writerow([date_fmt, user, action_lbl, module_lbl, details])

            show_overlay(page, ft.SnackBar(
                content=ft.Text(f"✅ Export réussi !\nFichier sauvegardé dans :\n{filepath}", size=13),
                bgcolor=Colors.PRIMARY,
                duration=5000,
            ))
        except Exception as exc:
            show_overlay(page, ft.SnackBar(
                content=ft.Text(f"❌ Erreur lors de l'export : {exc}", size=13),
                bgcolor=Colors.ERROR,
                duration=4000,
            ))

    device = get_device_type(page.window.width or 1200)
    load_logs()

    return ft.View(
        route="/logs",
        controls=[
            ft.Row([
                ft.Text("Journal d'Audit", style=heading_style(size=22)),
                ft.Container(expand=True),
                ft.ElevatedButton(
                    content=ft.Row([ft.Icon(ft.Icons.REFRESH, color=Colors.TEXT_ON_DARK), ft.Text("Actualiser", color=Colors.TEXT_ON_DARK)], spacing=6),
                    style=ft.ButtonStyle(bgcolor=Colors.PRIMARY),
                    height=42,
                    on_click=lambda _: apply_filters(),
                ),
            ]),
            ft.Container(height=10),
            error_text,
            loading,
            empty_text,
            ft.Container(height=10),

            # ✅ CORRECTION : wrap=True retiré (search_field a expand=True,
            # combinaison invalide avec un Row en mode wrap -> rectangle
            # gris silencieux côté Flutter)
            ft.Row([
                search_field,
                days_dropdown,
                action_dropdown,
                module_dropdown,
                ft.ElevatedButton(
                    content=ft.Row([ft.Icon(ft.Icons.FILTER_ALT, color=Colors.TEXT_ON_DARK), ft.Text("Appliquer", color=Colors.TEXT_ON_DARK)], spacing=6),
                    style=ft.ButtonStyle(bgcolor=Colors.PRIMARY),
                    height=42,
                    on_click=lambda _: apply_filters(),
                )
            ], spacing=10),

            ft.Container(height=15),
            ft.Row([
                ft.ElevatedButton(
                    content=ft.Row([ft.Icon(ft.Icons.DOWNLOAD, color=Colors.TEXT_ON_DARK), ft.Text("Exporter en CSV", color=Colors.TEXT_ON_DARK)], spacing=6),
                    style=ft.ButtonStyle(bgcolor="#496042"),
                    height=42,
                    on_click=lambda _: export_to_csv(),
                ),
                ft.Text(f"{len(logs)} enregistrement(s) trouvé(s)", size=12, color=Colors.NEUTRAL),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),

            ft.Container(height=10),
            ft.Container(
                content=ft.Row([logs_table], scroll=ft.ScrollMode.AUTO),
                padding=15,
                bgcolor="#FFFFFF",
                border_radius=12,
                border=ft.Border.all(1, Colors.BORDER),
            ),
        ],
        bgcolor=Colors.BACKGROUND,
        padding=16 if device == "mobile" else 32,
    )