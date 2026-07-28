"""
views/finance/admin.py — Liste administrative des factures et paiements.
Cahier des charges 2.6
Compatible Flet 0.86.0
CORRECTION : KPI "Virements en attente" rendu cliquable pour accéder à la page de confirmation.
"""

from __future__ import annotations

import flet as ft

from core.auth import AuthState
from core.api import ApiError, Endpoints
from core.theme import Colors, get_device_type, heading_style

# ✅ Statuts alignés avec le backend Django + icônes universelles
STATUS_CONFIG = {
    "payee": {"label": "Payée", "color": "#496042", "icon": ft.Icons.CHECK_CIRCLE},
    "en_attente": {"label": "En attente", "color": "#8B6B3F", "icon": ft.Icons.PENDING},
    "partielle": {"label": "Partielle", "color": "#1A2B4C", "icon": ft.Icons.REMOVE_CIRCLE_OUTLINE},
    "annulee": {"label": "Annulée", "color": "#8B8B8B", "icon": ft.Icons.CANCEL},
}

FILTERS = [
    ("all", "Toutes", ft.Icons.FILTER_LIST),
    ("en_attente", "En attente", ft.Icons.PENDING),
    ("payee", "Payées", ft.Icons.CHECK_CIRCLE),
    ("partielle", "Partielles", ft.Icons.REMOVE_CIRCLE_OUTLINE),
]


def _to_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).lower() == "true"


def build_finance_admin_view(page: ft.Page, auth: AuthState) -> ft.View:
    invoices: list[dict] = []
    current_filter = "all"
    selected = {"id": None, "numero": None}

    error_text = ft.Text("", color=Colors.ERROR, size=13, visible=False)
    loading = ft.ProgressRing(visible=True)

    kpi_row = ft.ResponsiveRow(spacing=16, run_spacing=16)

    selection_hint = ft.Text(
        "Sélectionnez une facture pour activer le paiement.",
        size=12, color=Colors.NEUTRAL, italic=True,
    )

    def go_to_payment(_: ft.ControlEvent) -> None:
        if selected["id"] is not None:
            page.go(f"/paiements?invoice_id={selected['id']}")

    payer_button = ft.ElevatedButton(
        content=ft.Row(
            [ft.Icon(ft.Icons.PAYMENTS, size=16), ft.Text("Payer la facture sélectionnée", weight=ft.FontWeight.W_600)],
            spacing=6,
        ),
        style=ft.ButtonStyle(bgcolor="#D9D9D9", color=Colors.NEUTRAL),
        disabled=True,
        on_click=go_to_payment,
    )

    def update_payer_button() -> None:
        has_selection = selected["id"] is not None
        payer_button.disabled = not has_selection
        payer_button.style = ft.ButtonStyle(
            bgcolor=Colors.PRIMARY if has_selection else "#D9D9D9",
            color=Colors.TEXT_ON_DARK if has_selection else Colors.NEUTRAL,
        )
        selection_hint.value = (
            f"Facture {selected['numero']} sélectionnée."
            if has_selection
            else "Sélectionnez une facture pour activer le paiement."
        )

    def select_invoice(inv: dict, checked: bool) -> None:
        inv_id = inv.get("id")
        if checked:
            selected["id"] = inv_id
            selected["numero"] = inv.get("numero")
        elif selected["id"] == inv_id:
            selected["id"] = None
            selected["numero"] = None
        update_payer_button()
        render_invoices()
        page.update()

    search_field = ft.TextField(
        label="Rechercher (N° facture, Client...)",
        prefix_icon=ft.Icons.SEARCH,
        border_radius=12,
        filled=True,
        bgcolor=Colors.BACKGROUND,
        expand=True,
        on_change=lambda _: render_invoices(),
    )

    filter_buttons = []
    def on_filter_click(filter_key: str, btn: ft.ElevatedButton):
        nonlocal current_filter
        current_filter = filter_key
        for b in filter_buttons:
            b.style = ft.ButtonStyle(
                bgcolor=Colors.PRIMARY if b == btn else "#FFFFFF",
                color=Colors.TEXT_ON_DARK if b == btn else Colors.TEXT,
                side=ft.BorderSide(1, Colors.BORDER if b != btn else Colors.PRIMARY),
                padding=ft.Padding(left=10, top=6, right=10, bottom=6),
            )
        page.update()
        render_invoices()

    for key, label, icon in FILTERS:
        btn = ft.ElevatedButton(
            content=ft.Row([ft.Icon(icon, size=14), ft.Text(label, size=12)], spacing=4, tight=True),
            style=ft.ButtonStyle(
                bgcolor=Colors.PRIMARY if key == current_filter else "#FFFFFF",
                color=Colors.TEXT_ON_DARK if key == current_filter else Colors.TEXT,
                side=ft.BorderSide(1, Colors.BORDER if key != current_filter else Colors.PRIMARY),
                padding=ft.Padding(left=10, top=6, right=10, bottom=6),
            ),
        )
        btn.on_click = lambda _, k=key, b=btn: on_filter_click(k, b)
        filter_buttons.append(btn)

    invoices_container = ft.Column(spacing=10)

    def load_invoices() -> None:
        loading.visible = True
        error_text.visible = False
        page.update()

        try:
            data = auth.api.get(Endpoints.FACTURES)
            invoices.clear()
            if isinstance(data, list):
                invoices.extend(data)
            elif isinstance(data, dict):
                invoices.extend(
                    data.get("items", data.get("results", data.get("data", [])))
                )
            else:
                raise ValueError("Format inattendu")

            if not invoices:
                print(f"[finance_admin] 0 facture reçue. Réponse brute : {data!r}")
        except ApiError as exc:
            error_text.value = f"Erreur de chargement : {exc.message}"
            error_text.visible = True
        except Exception:
            error_text.value = "Impossible de contacter le serveur."
            error_text.visible = True

        loading.visible = False
        update_kpis()
        render_invoices()

    def update_kpis() -> None:
        total_facture = sum(float(inv.get("montant_total", 0)) for inv in invoices)
        total_restant = sum(float(inv.get("montant_restant", 0)) for inv in invoices)
        total_paye = total_facture - total_restant

        # ✅ Récupérer le nombre de virements en attente
        virements_en_attente = 0
        try:
            data_virements = auth.api.get("/finance/paiements/virements-en-attente")
            if isinstance(data_virements, list):
                virements_en_attente = len(data_virements)
        except Exception:
            pass

        kpi_row.controls = [
            ft.Container(
                content=ft.Column([
                    ft.Text("Total Facturé", size=12, color=Colors.NEUTRAL),
                    ft.Text(f"{total_facture:,.0f} FCFA".replace(",", " "), size=20, weight=ft.FontWeight.BOLD, color=Colors.TEXT),
                ], spacing=4),
                col={"sm": 12, "md": 3},
                padding=16, bgcolor="#FFFFFF", border_radius=10, border=ft.Border(top=ft.BorderSide(4, Colors.PRIMARY))
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("Total Payé", size=12, color=Colors.NEUTRAL),
                    ft.Text(f"{total_paye:,.0f} FCFA".replace(",", " "), size=20, weight=ft.FontWeight.BOLD, color="#496042"),
                ], spacing=4),
                col={"sm": 12, "md": 3},
                padding=16, bgcolor="#FFFFFF", border_radius=10, border=ft.Border(top=ft.BorderSide(4, "#496042"))
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("Reste à Recouvrer", size=12, color=Colors.NEUTRAL),
                    ft.Text(f"{total_restant:,.0f} FCFA".replace(",", " "), size=20, weight=ft.FontWeight.BOLD, color="#8A4343"),
                ], spacing=4),
                col={"sm": 12, "md": 3},
                padding=16, bgcolor="#FFFFFF", border_radius=10, border=ft.Border(top=ft.BorderSide(4, "#8A4343"))
            ),
            # ✅ KPI CLIQUABLE : Alerte Virements
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.WARNING, color="#F9A825" if virements_en_attente > 0 else Colors.NEUTRAL, size=20),
                        ft.Text("Virements en attente", size=12, color=Colors.NEUTRAL)
                    ]),
                    ft.Text(f"{virements_en_attente}", size=24, weight=ft.FontWeight.BOLD, color="#F9A825" if virements_en_attente > 0 else Colors.TEXT),
                ], spacing=4),
                col={"sm": 12, "md": 3},
                padding=16, bgcolor="#FFFFFF", border_radius=10, border=ft.Border(top=ft.BorderSide(4, "#F9A825")),
                # ✅ CORRECTION : Rendu cliquable avec effet visuel
                ink=True,
                tooltip="Cliquez pour voir et confirmer les virements en attente",
                on_click=lambda _: page.go("/finance/virements-en-attente"),
            ),
        ]
        page.update()

    def get_client_name(inv: dict) -> str:
        if "client_nom" in inv:
            return inv["client_nom"]
        if "client_username" in inv:
            return inv["client_username"]
        client = inv.get("client")
        if isinstance(client, dict):
            return client.get("username", "Inconnu")
        return "Inconnu"

    def get_filtered_invoices() -> list[dict]:
        filtered = invoices
        if current_filter != "all":
            filtered = [inv for inv in filtered if inv.get("statut") == current_filter or inv.get("status") == current_filter]

        query = (search_field.value or "").lower().strip()
        if query:
            filtered = [
                inv for inv in filtered
                if query in str(inv.get("numero", "")).lower()
                or query in get_client_name(inv).lower()
            ]
        return filtered

    def render_invoices() -> None:
        invoices_container.controls.clear()
        filtered = get_filtered_invoices()

        if not filtered:
            invoices_container.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.RECEIPT_LONG, size=40, color=Colors.BORDER),
                            ft.Text("Aucune facture ne correspond aux critères.", color=Colors.NEUTRAL, italic=True, text_align=ft.TextAlign.CENTER),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    padding=40,
                    alignment=ft.Alignment(0.5, 0.5),
                )
            )
        else:
            device = get_device_type(page.window.width or 1200)
            if device == "mobile":
                for inv in filtered:
                    invoices_container.controls.append(build_invoice_card(inv))
            else:
                invoices_container.controls.append(
                    ft.Row([build_invoice_table(filtered)], scroll=ft.ScrollMode.AUTO)
                )

        update_payer_button()
        page.update()

    def build_invoice_table(data: list[dict]) -> ft.Control:
        columns = [
            ft.DataColumn(ft.Text("N° Facture", weight=ft.FontWeight.W_600)),
            ft.DataColumn(ft.Text("Client", weight=ft.FontWeight.W_600)),
            ft.DataColumn(ft.Text("Montant", weight=ft.FontWeight.W_600)),
            ft.DataColumn(ft.Text("Reste", weight=ft.FontWeight.W_600)),
            ft.DataColumn(ft.Text("Statut", weight=ft.FontWeight.W_600)),
            ft.DataColumn(ft.Text("Actions", weight=ft.FontWeight.W_600)),
        ]
        rows = []
        for inv in data:
            status = inv.get("statut") or inv.get("status", "en_attente")
            config = STATUS_CONFIG.get(status, STATUS_CONFIG["en_attente"])
            montant = float(inv.get("montant_total", 0))
            reste = float(inv.get("montant_restant", 0))

            is_selected = selected["id"] == inv.get("id")
            rows.append(ft.DataRow(
                selected=is_selected,
                on_select_change=lambda e, i=inv: select_invoice(i, _to_bool(e.data)),
                color="#EEF3EA" if is_selected else None,
                cells=[
                    ft.DataCell(ft.Text(inv.get("numero", "?"), weight=ft.FontWeight.W_600)),
                    ft.DataCell(ft.Text(get_client_name(inv))),
                    ft.DataCell(ft.Text(f"{montant:,.0f}".replace(",", " "))),
                    ft.DataCell(ft.Text(f"{reste:,.0f}".replace(",", " "), color=Colors.ERROR if reste > 0 else Colors.PRIMARY)),
                    ft.DataCell(ft.Container(
                        content=ft.Row([
                            ft.Icon(config["icon"], size=14, color=Colors.TEXT_ON_DARK),
                            ft.Text(config["label"], size=12, color=Colors.TEXT_ON_DARK)
                        ], spacing=4),
                        bgcolor=config["color"],
                        padding=ft.Padding(left=8, top=4, right=8, bottom=4),
                        border_radius=12,
                    )),
                    ft.DataCell(ft.TextButton(
                        content=ft.Text("Détails", size=12, color=Colors.PRIMARY),
                        on_click=lambda _, i=inv: show_invoice_details(i)
                    )),
                ],
            ))

        return ft.DataTable(
            columns=columns,
            rows=rows,
            show_checkbox_column=True,
            heading_row_color="#F5F3EE",
            border=ft.Border(
                left=ft.BorderSide(1, Colors.BORDER),
                right=ft.BorderSide(1, Colors.BORDER),
                top=ft.BorderSide(1, Colors.BORDER),
                bottom=ft.BorderSide(1, Colors.BORDER),
            ),
            border_radius=8,
            horizontal_lines=ft.BorderSide(1, Colors.BORDER),
        )

    def build_invoice_card(inv: dict) -> ft.Control:
        status = inv.get("statut") or inv.get("status", "en_attente")
        config = STATUS_CONFIG.get(status, STATUS_CONFIG["en_attente"])
        montant = float(inv.get("montant_total", 0))
        reste = float(inv.get("montant_restant", 0))
        is_selected = selected["id"] == inv.get("id")

        def toggle(_: ft.ControlEvent) -> None:
            select_invoice(inv, not is_selected)

        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Row([
                        ft.Icon(
                            ft.Icons.CHECK_CIRCLE if is_selected else ft.Icons.RADIO_BUTTON_UNCHECKED,
                            size=18,
                            color=Colors.PRIMARY if is_selected else Colors.BORDER,
                        ),
                        ft.Text(inv.get("numero", "?"), weight=ft.FontWeight.W_600, size=16),
                    ], spacing=8),
                    ft.Container(
                        content=ft.Text(config["label"], size=11, color=Colors.TEXT_ON_DARK),
                        bgcolor=config["color"],
                        padding=ft.Padding(left=8, top=4, right=8, bottom=4),
                        border_radius=12,
                    )
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Text(f"Client : {get_client_name(inv)}", size=13, color=Colors.NEUTRAL),
                ft.Row([
                    ft.Text(f"Total : {montant:,.0f} FCFA".replace(",", " "), size=13),
                    ft.Text(f"Reste : {reste:,.0f} FCFA".replace(",", " "), size=13, color=Colors.ERROR if reste > 0 else Colors.PRIMARY, weight=ft.FontWeight.W_600),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(height=10, color=Colors.BORDER),
                ft.Row([
                    ft.OutlinedButton(
                        content=ft.Text("Détails"),
                        on_click=lambda e, i=inv: show_invoice_details(i),
                        expand=True,
                    ),
                    ft.ElevatedButton(
                        content=ft.Text(
                            "Sélectionnée ✓" if is_selected else "Sélectionner",
                            color=Colors.TEXT_ON_DARK,
                        ),
                        style=ft.ButtonStyle(bgcolor=Colors.PRIMARY if is_selected else "#8B6B3F"),
                        on_click=toggle,
                        expand=True,
                    ),
                ], spacing=8),
            ], spacing=8),
            padding=16,
            bgcolor="#EEF3EA" if is_selected else "#FFFFFF",
            border_radius=10,
            border=ft.Border(
                left=ft.BorderSide(2 if is_selected else 1, Colors.PRIMARY if is_selected else Colors.BORDER),
                right=ft.BorderSide(2 if is_selected else 1, Colors.PRIMARY if is_selected else Colors.BORDER),
                top=ft.BorderSide(2 if is_selected else 1, Colors.PRIMARY if is_selected else Colors.BORDER),
                bottom=ft.BorderSide(2 if is_selected else 1, Colors.PRIMARY if is_selected else Colors.BORDER),
            ),
        )

    def show_invoice_details(inv: dict):
        page.snack_bar = ft.SnackBar(
            content=ft.Text(f"Détails de la facture {inv.get('numero')} (ID: {inv.get('id')})"),
            bgcolor=Colors.SECONDARY,
        )
        page.snack_bar.open = True
        page.update()

    load_invoices()

    device = get_device_type(page.window.width or 1200)

    content_card = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("Gestion Financière", style=heading_style(size=22)),
                        ft.Column([payer_button, selection_hint], horizontal_alignment=ft.CrossAxisAlignment.END, spacing=4),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    wrap=True,
                ),
                ft.Container(height=16),
                kpi_row,
                ft.Container(height=20),
                search_field,
                ft.Container(height=15),
                ft.Row(filter_buttons, wrap=True, spacing=8),
                ft.Container(height=15),
                error_text,
                loading,
                ft.Container(
                    content=invoices_container,
                    bgcolor="#FAF9F6",
                    border_radius=10,
                    padding=10,
                    border=ft.Border(
                        left=ft.BorderSide(1, Colors.BORDER),
                        right=ft.BorderSide(1, Colors.BORDER),
                        top=ft.BorderSide(1, Colors.BORDER),
                        bottom=ft.BorderSide(1, Colors.BORDER),
                    ),
                ),
            ],
            spacing=0,
            expand=True,
            scroll=ft.ScrollMode.ALWAYS,
        ),
        padding=24,
        bgcolor="#FFFFFF",
        border_radius=16,
        expand=True,
        shadow=ft.BoxShadow(spread_radius=0, blur_radius=16, color="#0000000F"),
    )

    return ft.View(
        route="/finance",
        controls=[content_card],
        bgcolor=Colors.BACKGROUND,
        padding=16 if device == "mobile" else 32,
    )