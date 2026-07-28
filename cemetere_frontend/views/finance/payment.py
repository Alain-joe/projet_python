"""
views/finance/payment.py — Paiement multi-canaux avec validation stricte.
Compatible Flet 0.86.0

CHANGEMENT IMPORTANT : les messages d'erreur de validation (montant vide,
négatif, non numérique, canal non choisi, téléphone invalide, référence
vide...) s'affichent désormais via error_text (Text intégré à la page),
PAS via un SnackBar. Le SnackBar Flet 0.86 a un comportement instable
quand on l'ouvre/ferme rapidement à répétition (le 1er affichage marche,
les suivants sont silencieusement ignorés). error_text est un simple
widget toujours présent, mis à jour par page.update() classique : aucun
risque de blocage, quel que soit le nombre de clics.

Le SnackBar (vert, "#496042") reste utilisé UNIQUEMENT pour la
confirmation finale de paiement réussi, qui ne se déclenche qu'une seule
fois par clic (après un aller-retour réseau), donc hors de portée du bug.
"""
from __future__ import annotations
from urllib.parse import urlparse, parse_qs
import re
import flet as ft

from core.auth import AuthState
from core.api import ApiError, Endpoints
from core.theme import Colors, get_device_type, heading_style
from core.ui_utils import show_overlay


def _get_invoice_id(page: ft.Page) -> str | None:
    query = parse_qs(urlparse(page.route).query)
    values = query.get("invoice_id")
    return values[0] if values else None


def build_payment_view(page: ft.Page, auth: AuthState) -> ft.View:
    invoice_id = _get_invoice_id(page)

    current_solde = {"value": 0.0}

    invoice_summary = ft.Column(spacing=6)
    error_text = ft.Text("", color=Colors.ERROR, size=13, visible=False, weight=ft.FontWeight.W_600)
    loading = ft.ProgressRing(visible=True)

    canal_dropdown = ft.Dropdown(
        label="Mode de paiement *",
        options=[
            ft.DropdownOption("especes", "Espèces"),
            ft.DropdownOption("mobile_money", "MTN Mobile Money"),
            ft.DropdownOption("airtel_money", "Airtel Money"),
            ft.DropdownOption("virement", "Virement bancaire"),
        ],
        border_radius=12,
        filled=True,
        bgcolor=Colors.BACKGROUND,
    )

    montant_field = ft.TextField(
        label="Montant à payer *",
        keyboard_type=ft.KeyboardType.NUMBER,
        border_radius=12,
        filled=True,
        bgcolor=Colors.BACKGROUND,
    )

    phone_field = ft.TextField(
        label="Numéro de téléphone",
        keyboard_type=ft.KeyboardType.NUMBER,
        border_radius=12,
        filled=True,
        bgcolor=Colors.BACKGROUND,
        visible=False,
    )

    reference_field = ft.TextField(
        label="Référence du virement",
        border_radius=12,
        filled=True,
        bgcolor=Colors.BACKGROUND,
        visible=False,
    )

    simulate_notice = ft.Text("", size=12, color=Colors.NEUTRAL, visible=False, italic=True)

    pay_button = ft.ElevatedButton(
        content=ft.Row([
            ft.Icon(ft.Icons.PAYMENTS, color=Colors.TEXT_ON_DARK),
            ft.Text("Payer", color=Colors.TEXT_ON_DARK, weight=ft.FontWeight.BOLD)
        ], spacing=5, alignment=ft.MainAxisAlignment.CENTER),
        style=ft.ButtonStyle(bgcolor=Colors.PRIMARY),
        width=300,
        height=50,
        disabled=True,
    )
    submit_loading = ft.ProgressRing(visible=False, width=20, height=20)

    def _show_error(message: str) -> None:
        """Affiche une erreur de validation via error_text (fiable, pas de SnackBar)."""
        error_text.value = message
        error_text.color = Colors.ERROR
        error_text.visible = True
        page.update()

    def _snack_success(message: str) -> None:
        """SnackBar vert réservé à la confirmation finale de paiement réussi."""
        show_overlay(page, ft.SnackBar(content=ft.Text(message, color=Colors.TEXT_ON_DARK), bgcolor="#496042"))

    def update_ui_state() -> None:
        canal = canal_dropdown.value
        phone_field.visible = False
        reference_field.visible = False
        simulate_notice.visible = False
        error_text.visible = False

        if canal == "mobile_money":
            phone_field.visible = True
            phone_field.label = "Numéro MTN (ex: 0612345678)"
            simulate_notice.value = "🟢 Mode SIMULATION : aucun débit réel."
            simulate_notice.visible = True
        elif canal == "airtel_money":
            phone_field.visible = True
            phone_field.label = "Numéro Airtel (ex: 0512345678)"
            simulate_notice.value = "🟢 Mode SIMULATION : aucun débit réel."
            simulate_notice.visible = True
        elif canal == "virement":
            reference_field.visible = True

        pay_button.disabled = montant_field.disabled
        page.update()

    canal_dropdown.on_change = lambda _: update_ui_state()
    montant_field.on_change = lambda _: update_ui_state()
    phone_field.on_change = lambda _: update_ui_state()
    reference_field.on_change = lambda _: update_ui_state()

    def load_invoice() -> None:
        if not invoice_id:
            error_text.value = "Aucune facture sélectionnée."
            error_text.visible = True
            loading.visible = False
            page.update()
            return

        loading.visible = True
        error_text.visible = False
        page.update()

        try:
            data = auth.api.get(f"{Endpoints.FACTURES}/{invoice_id}")
        except ApiError as exc:
            loading.visible = False
            error_text.value = f"Impossible de charger la facture : {exc.message}"
            error_text.visible = True
            page.update()
            return

        solde = float(data.get("montant_restant", 0))
        current_solde["value"] = solde

        invoice_summary.controls = [
            ft.Text(f"Facture #{data.get('numero', invoice_id)}", style=heading_style(size=18)),
            ft.Row([ft.Text("Montant total", color=Colors.NEUTRAL), ft.Text(f"{float(data.get('montant_total', 0)):,.0f} FCFA".replace(",", " "))], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([ft.Text("Déjà payé", color=Colors.NEUTRAL), ft.Text(f"{float(data.get('montant_paye', 0)):,.0f} FCFA".replace(",", " "))], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([ft.Text("Solde restant dû", weight=ft.FontWeight.W_600), ft.Text(f"{solde:,.0f} FCFA".replace(",", " "), color=Colors.ERROR if solde > 0 else Colors.PRIMARY)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ]

        if solde > 0:
            montant_field.value = str(int(solde))
            montant_field.disabled = False
        else:
            montant_field.value = "0"
            montant_field.disabled = True

        loading.visible = False
        update_ui_state()

    def validate_montant(canal: str) -> tuple[float | None, str | None]:
        raw = (montant_field.value or "").strip()

        if not raw:
            return None, "❌ Le montant est obligatoire."

        if "." in raw or "," in raw:
            return None, "❌ Montant invalide : les centimes ne sont pas utilisés au Congo, saisissez un montant entier (ex: 5000, pas 5000.50)."

        try:
            montant = int(raw)
        except ValueError:
            return None, "❌ Montant invalide : veuillez saisir uniquement des chiffres."

        if montant <= 0:
            return None, "❌ Le montant doit être supérieur à 0 FCFA."

        solde = current_solde["value"]
        if montant > solde:
            return None, f"❌ Le montant ne peut pas dépasser le solde restant dû ({solde:,.0f} FCFA).".replace(",", " ")

        if canal == "especes" and montant % 25 != 0 and montant != int(solde):
            return None, "❌ En espèces, le montant doit être un multiple de 25 FCFA (25, 50, 100, 500, 1000...), car les pièces/billets congolais fonctionnent ainsi."

        return float(montant), None

    def on_pay_click(_: ft.ControlEvent) -> None:
        error_text.visible = False
        canal = canal_dropdown.value

        if not canal:
            _show_error("❌ Veuillez choisir un mode de paiement.")
            return

        montant, montant_error = validate_montant(canal)
        if montant_error:
            _show_error(montant_error)
            return

        if canal == "mobile_money":
            phone = (phone_field.value or "").strip()
            if not re.match(r'^06\d{7,}$', phone):
                _show_error("❌ Numéro MTN invalide ! Il doit commencer par 06 et contenir au moins 9 chiffres (ex: 0612345678).")
                return
        elif canal == "airtel_money":
            phone = (phone_field.value or "").strip()
            if not re.match(r'^(04|05)\d{7,}$', phone):
                _show_error("❌ Numéro Airtel invalide ! Il doit commencer par 04 ou 05 et contenir au moins 9 chiffres (ex: 0512345678).")
                return
        elif canal == "virement":
            ref = (reference_field.value or "").strip()
            if not ref:
                _show_error("❌ Veuillez saisir la référence du virement.")
                return

        submit_loading.visible = True
        pay_button.disabled = True
        page.update()

        try:
            if canal == "especes":
                auth.api.payer_especes(invoice_id, montant, "ESP-AUTO")
                _snack_success("✅ Paiement en espèces enregistré avec succès !")

            elif canal == "mobile_money":
                auth.api.payer_mtn(invoice_id, phone_field.value.strip(), montant)
                _snack_success("✅ Paiement MTN Mobile Money enregistré avec succès !")

            elif canal == "airtel_money":
                auth.api.payer_airtel(invoice_id, phone_field.value.strip(), montant)
                _snack_success("✅ Paiement Airtel Money enregistré avec succès !")

            elif canal == "virement":
                result = auth.api.payer_virement(invoice_id, montant, reference_field.value.strip())
                msg = result.get("message_virement", "✅ Virement enregistré. En attente de validation par l'administration.")
                _snack_success(msg)

            load_invoice()

        except ApiError as exc:
            _show_error(f"❌ Échec du paiement : {exc.message}")
            submit_loading.visible = False
            pay_button.disabled = False
            page.update()
        except Exception as exc:
            _show_error(f"❌ Erreur inattendue : {str(exc)}")
            submit_loading.visible = False
            pay_button.disabled = False
            page.update()

    pay_button.on_click = on_pay_click

    def go_back(_: ft.ControlEvent) -> None:
        page.go("/finance")

    load_invoice()

    device = get_device_type(page.window.width or 1200)

    header_row = ft.Row([
        ft.IconButton(ft.Icons.ARROW_BACK, tooltip="Retour", on_click=go_back),
        ft.Text("Paiement de facture", style=heading_style(size=22)),
    ], spacing=4)

    form_card = ft.Container(
        content=ft.Column([
            header_row, loading, invoice_summary, ft.Divider(color=Colors.BORDER),
            canal_dropdown, ft.Container(height=10), montant_field, ft.Container(height=10),
            phone_field, ft.Container(height=10), reference_field, ft.Container(height=5),
            simulate_notice, ft.Container(height=15), error_text,
            ft.Row([pay_button, submit_loading], alignment=ft.MainAxisAlignment.CENTER),
        ], spacing=0),
        padding=32, bgcolor="#FFFFFF", border_radius=20,
        width=480 if device == "desktop" else None,
        shadow=ft.BoxShadow(spread_radius=0, blur_radius=20, color="#0000001A"),
    )

    return ft.View(
        route="/paiements",
        controls=[ft.Row([form_card], alignment=ft.MainAxisAlignment.CENTER, vertical_alignment=ft.CrossAxisAlignment.START)],
        bgcolor=Colors.BACKGROUND, padding=16,
    )