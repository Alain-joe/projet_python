"""
views/finance/client_payments.py — Factures et paiements pour le Client.
Compatible Flet 0.86.3. Responsive, avec export PDF amélioré.
"""
from __future__ import annotations
import flet as ft
from core.auth import AuthState
from core.api import Endpoints, ApiError
from core.theme import Colors, get_device_type, heading_style

def build_client_payments_view(page: ft.Page, auth: AuthState) -> ft.View:
    invoices = []
    loading = ft.ProgressRing(visible=True)
    error_text = ft.Text("", color=Colors.ERROR, size=13, visible=False)
    list_container = ft.Column(spacing=10)
    
    total_facture = ft.Text("0 FCFA", size=18, weight=ft.FontWeight.BOLD, color=Colors.TEXT)
    total_paye = ft.Text("0 FCFA", size=18, weight=ft.FontWeight.BOLD, color="#496042")
    reste_a_payer = ft.Text("0 FCFA", size=18, weight=ft.FontWeight.BOLD, color="#C62828")

    async def load_data() -> None:
        loading.visible, error_text.visible = True, False
        page.update()
        try:
            data = auth.api.get("/finance/factures/mine")
            invoices.clear()
            if isinstance(data, list): invoices.extend(data)
            elif isinstance(data, dict): invoices.extend(data.get("results", []))
            
            somme_totale = sum(float(inv.get("montant_total", 0)) for inv in invoices)
            somme_payee = sum(float(inv.get("montant_paye", 0)) for inv in invoices)
            somme_reste = sum(float(inv.get("montant_restant", 0)) for inv in invoices)
            
            total_facture.value = f"{somme_totale:,.0f} FCFA".replace(",", " ")
            total_paye.value = f"{somme_payee:,.0f} FCFA".replace(",", " ")
            reste_a_payer.value = f"{somme_reste:,.0f} FCFA".replace(",", " ")
            
            render_list()
        except ApiError as exc:
            error_text.value = f"Erreur : {exc.message}"
            error_text.visible = True
        except Exception as exc:
            error_text.value = f"Erreur de connexion : {exc}"
            error_text.visible = True
        finally:
            loading.visible = False
            page.update()

    def render_list() -> None:
        list_container.controls.clear()
        if not invoices:
            list_container.controls.append(ft.Container(content=ft.Text("Aucune facture.", color=Colors.NEUTRAL, italic=True), padding=40, alignment=ft.Alignment(0.5, 0.5)))
        else:
            for inv in invoices:
                list_container.controls.append(build_invoice_card(inv))
        page.update()

    def build_invoice_card(inv: dict) -> ft.Control:
        montant_total = float(inv.get("montant_total", 0))
        montant_restant = float(inv.get("montant_restant", 0))
        is_paid = montant_restant <= 0
        statut = "Payée" if is_paid else "En cours"
        color = "#496042" if is_paid else "#F9A825"

        # ✅ CORRECTION : URL PDF avec token pour l'authentification
        pdf_url = f"http://127.0.0.1:8000/api/finance/factures/{inv['id']}/pdf?token={auth.access_token}"

        actions = [
            ft.ElevatedButton(
                content=ft.Row([ft.Icon(ft.Icons.PICTURE_AS_PDF, size=16, color=Colors.TEXT_ON_DARK), ft.Text("📄 PDF", size=12, color=Colors.TEXT_ON_DARK)]),
                bgcolor="#2E7D9A",
                height=36,
                on_click=lambda _, url=pdf_url: page.launch_url(url),
            )
        ]
        if not is_paid:
            actions.insert(0, ft.ElevatedButton(
                content=ft.Text("💳 Payer", color=Colors.TEXT_ON_DARK, size=12),
                bgcolor=Colors.PRIMARY,
                height=36,
                on_click=lambda _, iid=inv["id"]: page.go(f"/paiements?invoice_id={iid}"),
            ))

        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text(f"Facture #{inv.get('numero', inv.get('id', '?'))}", weight=ft.FontWeight.W_600, size=14, expand=True),
                    ft.Container(content=ft.Text(statut, size=11, color=Colors.TEXT_ON_DARK), bgcolor=color, padding=8, border_radius=12),
                ]),
                ft.Row([
                    ft.Text(f"Total : {montant_total:,.0f} FCFA".replace(",", " "), size=12, color=Colors.NEUTRAL),
                    ft.Text(f"Reste : {montant_restant:,.0f} FCFA".replace(",", " "), size=12, color="#C62828" if not is_paid else "#496042", weight=ft.FontWeight.W_600),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(height=10, color=Colors.BORDER),
                ft.Row(actions, spacing=8, alignment=ft.MainAxisAlignment.END),
            ], spacing=6),
            padding=14, bgcolor="#FFFFFF", border_radius=10, border=ft.Border.all(1, Colors.BORDER),
        )

    width = getattr(page, 'window', page).width if hasattr(page, 'window') else (getattr(page, 'width', 1200) or 1200)
    device = get_device_type(width)

    page.run_task(load_data)

    return ft.View(
        route="/finance/client-paiements",
        controls=[
            ft.Row([
                ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: page.go("/dashboard/client")),
                ft.Text("Mes Paiements", style=heading_style(size=22)),
            ]),
            ft.Container(height=16),
            ft.ResponsiveRow([
                ft.Container(content=ft.Column([ft.Text("Total Facturé", size=11, color=Colors.NEUTRAL), total_facture], spacing=4), padding=16, bgcolor="#FFFFFF", border_radius=10, border=ft.Border(top=ft.BorderSide(3, Colors.PRIMARY)), col={"xs": 12, "sm": 4}),
                ft.Container(content=ft.Column([ft.Text("Avances versées", size=11, color=Colors.NEUTRAL), total_paye], spacing=4), padding=16, bgcolor="#FFFFFF", border_radius=10, border=ft.Border(top=ft.BorderSide(3, "#496042")), col={"xs": 12, "sm": 4}),
                ft.Container(content=ft.Column([ft.Text("Reste à payer", size=11, color=Colors.NEUTRAL), reste_a_payer], spacing=4), padding=16, bgcolor="#FFFFFF", border_radius=10, border=ft.Border(top=ft.BorderSide(3, "#C62828")), col={"xs": 12, "sm": 4}),
            ], spacing=12, run_spacing=12),
            ft.Container(height=20),
            error_text,
            loading,
            list_container,
        ],
        bgcolor=Colors.BACKGROUND,
        padding=16 if device == "mobile" else 32,
        scroll=ft.ScrollMode.AUTO,
    )