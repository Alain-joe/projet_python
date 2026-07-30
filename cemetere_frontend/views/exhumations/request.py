"""
views/exhumations/request.py — Formulaire de demande d'exhumation avec recherche de défunt.
Compatible Flet 0.86.0

CORRECTION AJOUTÉE :
- motif_field : keyboard_type=TEXT forcé explicitement (le champ n'acceptait
  que des chiffres sur mobile faute de type de clavier précisé).
- _friendly_error() : traduction en français des messages d'erreur bruts
  renvoyés par le backend (validation Pydantic/Ninja en anglais), affichés
  seulement si la validation front (déjà en français) n'a rien détecté.

VALIDATION (message précis pour chaque erreur, via error_text) :
  - Recherche : champ vide → message explicite au lieu de ne rien faire
  - Motif : obligatoire, entre 10 et 500 caractères (un motif d'exhumation
    est une démarche officielle, une simple phrase courte n'est pas
    suffisante)
  - Date prévue : format AAAA-MM-JJ obligatoire et valide, ne peut pas
    être dans le passé

CORRECTION (déjà présente) : time.sleep() bloquant remplacé par
page.run_task() + asyncio.sleep().

CORRECTION (déjà présente) : page.window.width sécurisé avec repli 1200,
comme sur les autres formulaires. error_text/success_text systématiquement
réinitialisés au début de chaque validation.
"""
from __future__ import annotations
import asyncio
from datetime import datetime
import flet as ft
from core.auth import AuthState
from core.api import ApiError, Endpoints
from core.theme import Colors, get_device_type, heading_style


# ==============================================================================
# TRADUCTION DES ERREURS BACKEND (fallback si la validation front n'a rien vu)
# ==============================================================================
_ERROR_TRANSLATIONS = {
    "field required": "Ce champ est obligatoire.",
    "this field is required": "Ce champ est obligatoire.",
    "none is not an allowed value": "Ce champ ne peut pas être vide.",
    "value is not a valid integer": "Une valeur numérique est attendue.",
    "value is not a valid date": "Format de date invalide.",
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
    message générique en français compréhensible. Utilisé uniquement en
    dernier recours, quand la validation locale n'a rien détecté mais que
    le serveur refuse quand même la requête (ex: incohérence de schéma).
    """
    raw = getattr(exc, "message", None) or str(exc)
    raw_lower = raw.lower()

    for needle, translation in _ERROR_TRANSLATIONS.items():
        if needle in raw_lower:
            return translation

    # Si le message semble déjà en français (contient des mots-clés courants
    # de nos propres messages), on le garde tel quel.
    if any(w in raw_lower for w in ["veuillez", "obligatoire", "invalide", "erreur", "échec"]):
        return raw

    # Repli générique : on évite d'afficher un message technique brut à l'utilisateur.
    return "Une erreur est survenue lors du traitement de la demande. Veuillez réessayer."


def build_exhumation_request_view(page: ft.Page, auth: AuthState) -> ft.View:
    selected_inhumation = None

    search_field = ft.TextField(
        label="Nom du défunt",
        border_radius=12,
        filled=True,
        bgcolor=Colors.BACKGROUND,
        keyboard_type=ft.KeyboardType.TEXT,
    )
    search_results = ft.Column(spacing=5, scroll=ft.ScrollMode.AUTO, expand=False)

    motif_field = ft.TextField(
        label="Motif de la demande",
        multiline=True,
        min_lines=3,
        border_radius=12,
        filled=True,
        bgcolor=Colors.BACKGROUND,
        keyboard_type=ft.KeyboardType.TEXT,  # ✅ CORRECTION : forcé explicitement (texte libre, pas de chiffres uniquement)
        hint_text="Ex : Transfert vers un caveau familial suite à...",
    )
    date_field = ft.TextField(
        label="Date prévue (AAAA-MM-JJ)",
        border_radius=12,
        filled=True,
        bgcolor=Colors.BACKGROUND,
        hint_text="ex: 2026-08-15",
    )

    info_box = ft.Container(visible=False, padding=16, bgcolor="#E8F5E9", border_radius=8)
    error_text = ft.Text("", color=Colors.ERROR, size=13, visible=False, weight=ft.FontWeight.W_600)
    success_text = ft.Text("", color=Colors.PRIMARY, size=13, visible=False)
    loading = ft.ProgressRing(visible=False)

    def show_error(message: str) -> None:
        error_text.value = message
        error_text.visible = True
        success_text.visible = False
        loading.visible = False
        page.update()

    def get_user_id() -> int | None:
        """Récupère l'ID utilisateur de manière fiable"""
        if auth.user and auth.user.get("id"):
            return int(auth.user.get("id"))

        if auth.access_token:
            try:
                import jwt
                payload = jwt.decode(auth.access_token, options={"verify_signature": False})
                return int(payload.get("user_id"))
            except Exception:
                pass

        return None

    def search_inhumation(e):
        nom = (search_field.value or "").strip()
        error_text.visible = False

        if not nom:
            show_error("❌ Veuillez saisir un nom avant de lancer la recherche.")
            return

        if len(nom) < 2:
            show_error("❌ Saisissez au moins 2 caractères pour la recherche.")
            return

        search_results.controls = [ft.ProgressRing(width=20, height=20)]
        search_results.visible = True
        page.update()

        try:
            data = auth.api.get("/cemetery/inhumations/search", params={"nom": nom})
            search_results.controls.clear()

            if not data:
                search_results.controls.append(ft.Text("Aucun défunt trouvé.", color=Colors.NEUTRAL, italic=True))
            else:
                for inh in data:
                    row = ft.ListTile(
                        title=ft.Text(f"{inh.get('defunt_nom', '')} {inh.get('defunt_prenom', '')}", weight=ft.FontWeight.W_600),
                        subtitle=ft.Text(f"Caveau: {inh.get('grave_code', '?')} | Décès: {inh.get('defunt_date_deces', '—')}"),
                        trailing=ft.Icon(ft.Icons.CHECK_CIRCLE, color=Colors.PRIMARY),
                        on_click=lambda _, i=inh: select_inhumation(i),
                    )
                    search_results.controls.append(row)
        except ApiError as exc:
            search_results.controls = [ft.Text(f"Erreur : {_friendly_error(exc)}", color=Colors.ERROR)]
        finally:
            page.update()

    def select_inhumation(inh: dict):
        nonlocal selected_inhumation
        selected_inhumation = inh
        error_text.visible = False

        info_box.content = ft.Column([
            ft.Text("✅ Défunt sélectionné :", weight=ft.FontWeight.BOLD, color="#2E7D32"),
            ft.Text(f"Nom : {inh.get('defunt_nom')} {inh.get('defunt_prenom')}"),
            ft.Text(f"Caveau : {inh.get('grave_code')}"),
            ft.Text(f"Date de décès : {inh.get('defunt_date_deces')}"),
        ], spacing=4)
        info_box.visible = True
        search_results.visible = False
        page.update()

    def validate() -> str | None:
        if not selected_inhumation:
            return "❌ Veuillez d'abord rechercher et sélectionner un défunt."

        motif = (motif_field.value or "").strip()
        if not motif:
            return "❌ Le motif de la demande est obligatoire."
        if len(motif) < 10:
            return "❌ Le motif doit contenir au moins 10 caractères (précisez la raison de la demande)."
        if len(motif) > 500:
            return "❌ Le motif ne doit pas dépasser 500 caractères."

        raw_date = (date_field.value or "").strip()
        if not raw_date:
            return "❌ La date prévue est obligatoire."
        try:
            date_prevue = datetime.strptime(raw_date, "%Y-%m-%d").date()
        except ValueError:
            return "❌ Format de date invalide. Utilisez le format AAAA-MM-JJ (ex: 2026-08-15)."

        if date_prevue < datetime.now().date():
            return "❌ La date prévue ne peut pas être dans le passé."

        user_id = get_user_id()
        if not user_id:
            return "❌ Erreur d'authentification. Veuillez vous reconnecter."

        return None

    def submit_request(e):
        error = validate()
        if error:
            show_error(error)
            return

        user_id = get_user_id()

        loading.visible = True
        error_text.visible = False
        success_text.visible = False
        page.update()

        try:
            payload = {
                "inhumation_id": int(selected_inhumation["id"]),
                "demandeur_id": user_id,
                "motif": motif_field.value.strip(),
                "date_prevue": date_field.value.strip(),
            }
            auth.api.post("/cemetery/exhumations", json=payload)

            success_text.value = "✅ Demande envoyée avec succès. En attente de validation."
            success_text.visible = True
            error_text.visible = False
            loading.visible = False
            page.update()

            async def delayed_redirect():
                await asyncio.sleep(1.5)
                page.go("/exhumations")

            page.run_task(delayed_redirect)

        except ApiError as exc:
            # ✅ CORRECTION : message backend traduit en français au lieu du texte brut
            show_error(f"❌ Échec : {_friendly_error(exc)}")
        except Exception as exc:
            show_error("❌ Une erreur inattendue est survenue. Veuillez réessayer.")

    window_width = None
    if hasattr(page, "window") and page.window is not None:
        window_width = page.window.width
    if not window_width:
        window_width = getattr(page, "width", None)
    device = get_device_type(window_width or 1200)

    form_content = ft.Column(
        [
            ft.Text("Nouvelle demande d'exhumation", style=heading_style(size=22)),
            ft.Container(height=10),

            ft.Text("Étape 1 : Rechercher le défunt", style=heading_style(size=16)),
            ft.Row([
                search_field,
                ft.ElevatedButton(
                    content=ft.Text("Rechercher"),
                    on_click=search_inhumation,
                    style=ft.ButtonStyle(bgcolor=Colors.PRIMARY),
                    height=50
                ),
            ], expand=True),
            ft.Container(height=10),
            search_results,
            ft.Container(height=10),
            info_box,

            ft.Divider(height=20, color=Colors.BORDER),

            ft.Text("Étape 2 : Détails de la demande", style=heading_style(size=16)),
            motif_field,
            ft.Container(height=10),
            date_field,
            ft.Container(height=20),

            error_text,
            success_text,
            loading,

            ft.Container(height=20),
            ft.ElevatedButton(
                content=ft.Text("Soumettre la demande", color=Colors.TEXT_ON_DARK, weight=ft.FontWeight.BOLD),
                style=ft.ButtonStyle(bgcolor=Colors.PRIMARY),
                width=300,
                on_click=submit_request
            ),
            ft.Container(height=40),
        ],
        spacing=0,
    )

    return ft.View(
        route="/exhumations/nouvelle",
        controls=[
            ft.Container(
                content=form_content,
                padding=16 if device == "mobile" else 32,
            )
        ],
        bgcolor=Colors.BACKGROUND,
    )