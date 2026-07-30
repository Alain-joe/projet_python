"""
views/graves/report_problem.py — Formulaire de signalement d'un problème sur un caveau.
Compatible Flet 0.86.3

CORRECTION AJOUTÉE :
- motif_field / description_field / photos_field : keyboard_type=TEXT
  forcé explicitement (clavier mobile qui basculait en numérique par
  défaut, permettant de saisir un motif uniquement composé de chiffres).
- validate() : garde-fou supplémentaire — le motif doit contenir au
  moins une lettre (rejette un motif uniquement numérique comme
  "2222222222").
- _friendly_error() : traduction en français des messages d'erreur bruts
  renvoyés par le backend.

VALIDATION (avec motif explicite pour chaque erreur, affiché en
rouge via error_text) :
  - Motif : obligatoire, entre 5 et 150 caractères, doit contenir au
    moins une lettre
  - Description : si renseignée, minimum 10 caractères (une description
    de 2-3 caractères n'apporte rien à l'agent qui traitera le
    signalement)
  - Référence photo / URL : si renseignée, doit ressembler à une URL
    (http/https) ou une référence de dossier simple (lettres, chiffres,
    tirets, underscores, points, slashs) — pas de texte libre avec
    espaces qui ne serait ni l'un ni l'autre

CORRECTION : page.window.width sécurisé avec repli 1200 si page.window
est indisponible (même précaution que sur le formulaire de réservation).
"""
from __future__ import annotations
import re
import flet as ft
from urllib.parse import urlparse, parse_qs
import asyncio

from core.auth import AuthState
from core.api import ApiError
from core.theme import Colors, get_device_type, heading_style
from core.ui_utils import show_overlay

URL_RE = re.compile(r'^https?://[^\s]+$')
REF_RE = re.compile(r'^[A-Za-z0-9_\-./]+$')
HAS_LETTER_RE = re.compile(r'[A-Za-zÀ-ÿ]')  # ✅ au moins une lettre (accents compris)


# ==============================================================================
# TRADUCTION DES ERREURS BACKEND (fallback si le message est brut/anglais)
# ==============================================================================
_ERROR_TRANSLATIONS = {
    "field required": "Ce champ est obligatoire.",
    "this field is required": "Ce champ est obligatoire.",
    "none is not an allowed value": "Ce champ ne peut pas être vide.",
    "value is not a valid integer": "Une valeur numérique est attendue.",
    "value is not a valid date": "Format de date invalide.",
    "value is not a valid datetime": "Format de date/heure invalide.",
    "ensure this value has at least": "Le texte saisi est trop court.",
    "ensure this value has at most": "Le texte saisi est trop long.",
    "string too short": "Le texte saisi est trop court.",
    "string too long": "Le texte saisi est trop long.",
    "not found": "Élément introuvable.",
    "invalid": "Valeur invalide.",
}


def _friendly_error(exc) -> str:
    """
    Traduit un message d'erreur backend (souvent en anglais, brut) vers un
    message générique en français compréhensible.
    """
    raw = getattr(exc, "message", None) or str(exc)
    raw_lower = raw.lower()

    for needle, translation in _ERROR_TRANSLATIONS.items():
        if needle in raw_lower:
            return translation

    if any(w in raw_lower for w in ["veuillez", "obligatoire", "invalide", "erreur", "échec"]):
        return raw

    return "Une erreur est survenue lors du traitement de la demande. Veuillez réessayer."


def build_report_problem_view(page: ft.Page, auth: AuthState) -> ft.View:
    query = parse_qs(urlparse(page.route).query)
    grave_id_str = query.get("grave_id", [None])[0]
    grave_code = query.get("grave_code", ["Inconnu"])[0]

    if not grave_id_str or str(grave_id_str).lower() == "undefined":
        page.go("/graves")
        return ft.View(route="/graves/signaler", controls=[])

    try:
        grave_id = int(grave_id_str)
    except ValueError:
        page.go("/graves")
        return ft.View(route="/graves/signaler", controls=[])

    motif_field = ft.TextField(
        label="Motif du problème *",
        border_radius=8,
        hint_text="Ex: Effondrement, fissures importantes, terrain instable...",
        keyboard_type=ft.KeyboardType.TEXT,  # ✅ CORRECTION : forcé explicitement
    )

    description_field = ft.TextField(
        label="Description détaillée",
        border_radius=8,
        multiline=True,
        min_lines=4,
        hint_text="Décrivez le problème constaté sur le terrain...",
        keyboard_type=ft.KeyboardType.TEXT,  # ✅ CORRECTION : forcé explicitement
    )

    photos_field = ft.TextField(
        label="Référence photo / URL (optionnel)",
        border_radius=8,
        hint_text="Lien vers la photo ou référence du dossier...",
        keyboard_type=ft.KeyboardType.TEXT,  # ✅ CORRECTION : forcé explicitement
    )

    error_text = ft.Text("", color=Colors.ERROR, size=13, visible=False, weight=ft.FontWeight.W_600)
    loading = ft.ProgressRing(visible=False, width=20, height=20)

    def show_error(message: str) -> None:
        error_text.value = message
        error_text.visible = True
        loading.visible = False
        page.update()

    def validate() -> str | None:
        motif = motif_field.value.strip() if motif_field.value else ""
        if not motif:
            return "❌ Le motif du problème est obligatoire."
        if len(motif) < 5:
            return "❌ Le motif doit contenir au moins 5 caractères (soyez un peu plus précis)."
        if len(motif) > 150:
            return "❌ Le motif ne doit pas dépasser 150 caractères — utilisez la description pour les détails."
        # ✅ CORRECTION : rejette un motif uniquement composé de chiffres (ex: "2222222222")
        if not HAS_LETTER_RE.search(motif):
            return "❌ Le motif doit décrire le problème en mots, pas seulement des chiffres."

        description = description_field.value.strip() if description_field.value else ""
        if description and len(description) < 10:
            return "❌ La description est trop courte (minimum 10 caractères) si vous choisissez d'en ajouter une."

        photos = photos_field.value.strip() if photos_field.value else ""
        if photos:
            if not (URL_RE.match(photos) or REF_RE.match(photos)):
                return "❌ Référence photo invalide. Utilisez un lien complet (https://...) ou une référence simple (lettres, chiffres, -, _, ., /)."

        return None

    def on_submit(e):
        error = validate()
        if error:
            show_error(error)
            return

        loading.visible = True
        error_text.visible = False
        page.update()

        try:
            auth.api.signaler_probleme_caveau(
                grave_id=grave_id,
                motif=motif_field.value.strip(),
                description=description_field.value.strip(),
                photos=[photos_field.value.strip()] if photos_field.value.strip() else None
            )

            show_overlay(page, ft.SnackBar(
                content=ft.Text("✅ Signalement envoyé avec succès. En attente de validation.", color=Colors.TEXT_ON_DARK),
                bgcolor="#496042",
                duration=2000,
            ))

            async def delayed_redirect():
                await asyncio.sleep(1.5)
                page.go("/graves/signalements")

            page.run_task(delayed_redirect)

        except ApiError as exc:
            # ✅ CORRECTION : message backend traduit en français
            show_error(f"❌ Échec : {_friendly_error(exc)}")
        except Exception:
            show_error("❌ Une erreur inattendue est survenue. Veuillez réessayer.")

    submit_button = ft.ElevatedButton(
        content=ft.Row([
            ft.Icon(ft.Icons.SEND, color=Colors.TEXT_ON_DARK),
            ft.Text("Envoyer le signalement", color=Colors.TEXT_ON_DARK, weight=ft.FontWeight.BOLD)
        ], spacing=5),
        style=ft.ButtonStyle(bgcolor=Colors.PRIMARY),
        width=float("inf"),
        height=50,
        on_click=on_submit
    )

    window_width = None
    if hasattr(page, "window") and page.window is not None:
        window_width = page.window.width
    if not window_width:
        window_width = getattr(page, "width", None)
    device = get_device_type(window_width or 1200)

    return ft.View(
        route="/graves/signaler",
        controls=[
            ft.Row([
                ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: page.go("/graves")),
                ft.Text("Signaler un problème", style=heading_style(size=22)),
            ]),
            ft.Container(height=10),
            ft.Text(f"Caveau concerné : {grave_code}", size=14, color=Colors.NEUTRAL, weight=ft.FontWeight.W_600),
            ft.Container(height=20),
            ft.Container(
                content=ft.Column([
                    motif_field,
                    ft.Container(height=10),
                    description_field,
                    ft.Container(height=10),
                    photos_field,
                    ft.Container(height=20),
                    error_text,
                    submit_button,
                    ft.Container(height=10),
                    loading,
                ], spacing=0),
                padding=24,
                bgcolor="#FFFFFF",
                border_radius=12,
                width=600 if device != "mobile" else None,
            ),
        ],
        bgcolor=Colors.BACKGROUND,
        padding=24 if device != "mobile" else 16,
        scroll=ft.ScrollMode.AUTO,
    )