"""
views/users/list.py — Liste des utilisateurs avec recherche, date de création, popups.
Version Finale : Username optionnel, compatible Flet 0.86.0 et Router.
✅ CORRECTION : ft.colors (minuscule, API obsolète) remplacé par ft.Colors (Flet 0.86.0)
✅ CORRECTION : troncature des textes longs (email, nom, etc.) pour éviter le chevauchement
   des colonnes, et harmonisation des largeurs fixes entre le header et les lignes.

CORRECTIONS APPLIQUÉES :
- create_user : ajout du champ "Confirmer le mot de passe" + validation
  des champs obligatoires (Prénom, Nom, Email, Date de naissance) +
  date de naissance via calendrier (ft.DatePicker) au lieu du texte libre.
- edit_user : fonction réparée (elle était sortie de sa fonction parente
  et dupliquée dans la version précédente -> cassait le fichier /
  empêchait l'enregistrement). Même validation + calendrier que
  create_user. Payload envoyé au backend complété avec is_active et
  is_approved (le schéma PUT /users/{id}/ les attend).
- Diagnostic temporaire (print) conservé dans on_save de edit_user pour
  confirmer que payload et réponse backend sont bien ceux attendus.
- render_users : ajout de overflow=ELLIPSIS/max_lines=1 sur les textes
  variables (nom, email, téléphone, rôle) et alignement des largeurs
  fixes de colonnes (Rôle/Création/Statut/Actions) avec le header.
"""
import flet as ft
from datetime import datetime
from core.theme import Colors, get_device_type, heading_style

def build_users_list_view(page: ft.Page, auth):
    users = []
    filtered_users = []

    def show_snack(message: str, error: bool = False):
        page.snack_bar = ft.SnackBar(
            content=ft.Row([
                ft.Icon(ft.Icons.ERROR if error else ft.Icons.CHECK_CIRCLE, color=ft.Colors.WHITE),
                ft.Text(message, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD)
            ]),
            bgcolor=ft.Colors.RED_700 if error else ft.Colors.GREEN_700,
            behavior=ft.SnackBarBehavior.FLOATING,
        )
        page.snack_bar.open = True
        page.update()

    def _friendly_error(exc) -> str:
        """
        Extrait un message d'erreur lisible depuis une exception API.
        Gère le format Pydantic/Ninja : liste de dicts avec clé 'msg'
        (ex: erreurs de validation sur téléphone, email, etc.)
        """
        payload = exc.args[0] if exc.args else exc
        if isinstance(payload, list):
            messages = []
            for item in payload:
                if isinstance(item, dict) and "msg" in item:
                    msg = str(item["msg"])
                    # Nettoie le préfixe technique "Value error, " ajouté par Pydantic
                    if msg.startswith("Value error, "):
                        msg = msg[len("Value error, "):]
                    messages.append(msg)
            if messages:
                return " • ".join(messages)
        return str(exc)    

    def load_users(e=None):
        nonlocal users, filtered_users
        users_container.controls = [ft.Container(content=ft.ProgressRing(), alignment=ft.Alignment(0, 0), padding=40)]
        page.update()
        try:
            response = auth.api.get("/users/list")
            if isinstance(response, list):
                users = response
                filtered_users = users.copy()
                render_users(filtered_users)
            else:
                show_snack("Erreur de chargement", True)
        except Exception as e:
            show_snack(f"Erreur : {str(e)}", True)

    def filter_users(e=None):
        nonlocal filtered_users
        text = search_field.value.lower().strip() if search_field.value else ""
        filtered_users = []
        if not text:
            filtered_users = users.copy()
        else:
            for user in users:
                data = (str(user.get("username", "")) + str(user.get("first_name", "")) + str(user.get("last_name", "")) + str(user.get("email", "")) + str(user.get("role", ""))).lower()
                if text in data:
                    filtered_users.append(user)
        render_users(filtered_users)

    def go_back(e):
        page.go("/dashboard/admin")

    # ==========================================================================
    # GESTION DES DIALOGUES
    # ==========================================================================
    def show_dialog(dialog: ft.AlertDialog):
        if dialog not in page.overlay:
            page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def hide_dialog(dialog: ft.AlertDialog):
        dialog.open = False
        page.update()

    def show_date_picker(dp: ft.DatePicker):
        if dp not in page.overlay:
            page.overlay.append(dp)
        dp.open = True
        page.update()

    # ==========================================================================
    # ACTIONS : CRÉATION
    # ==========================================================================
    def create_user(e):
        username_field = ft.TextField(
            label="Nom d'utilisateur (optionnel - auto-généré si vide)",
            expand=True,
            prefix_icon=ft.Icons.PERSON_OUTLINE,
            hint_text="ex: jean.dupont"
        )
        first_name_field = ft.TextField(label="Prénom *", expand=True)
        last_name_field = ft.TextField(label="Nom *", expand=True)
        email_field = ft.TextField(label="Email *", expand=True)
        phone_field = ft.TextField(label="Téléphone", expand=True)

        sex_field = ft.Dropdown(
            label="Sexe", value="N", expand=True,
            options=[
                ft.dropdown.Option("M", "Masculin"),
                ft.dropdown.Option("F", "Féminin"),
                ft.dropdown.Option("O", "Autre"),
                ft.dropdown.Option("N", "Non renseigné")
            ]
        )

        birth_date_field = ft.TextField(
            label="Date de naissance *",
            expand=True,
            read_only=True,
            hint_text="AAAA-MM-JJ",
            prefix_icon=ft.Icons.CALENDAR_MONTH,
        )

        def on_birth_date_change(e: ft.ControlEvent):
            if e.control.value:
                birth_date_field.value = e.control.value.strftime("%Y-%m-%d")
                birth_date_field.error_text = None
                page.update()

        birth_date_picker = ft.DatePicker(
            first_date=datetime(1900, 1, 1),
            last_date=datetime.now(),
            on_change=on_birth_date_change,
        )
        birth_date_field.on_focus = lambda e: show_date_picker(birth_date_picker)

        role_field = ft.Dropdown(
            label="Rôle *", value="client", expand=True,
            options=[
                ft.dropdown.Option("admin", "Administrateur"),
                ft.dropdown.Option("agent", "Agent"),
                ft.dropdown.Option("secretariat", "Secrétariat"),
                ft.dropdown.Option("client", "Client")
            ]
        )
        password_field = ft.TextField(label="Mot de passe (optionnel - auto-généré si vide)", expand=True, password=True, can_reveal_password=True)
        confirm_password_field = ft.TextField(label="Confirmer le mot de passe", expand=True, password=True, can_reveal_password=True)

        def on_cancel(e):
            hide_dialog(dialog)

        def validate() -> bool:
            valid = True
            required = [
                (first_name_field, "Champ requis"),
                (last_name_field, "Champ requis"),
                (email_field, "Champ requis"),
                (birth_date_field, "Champ requis"),
            ]
            for field, msg in required:
                if not field.value or not field.value.strip():
                    field.error_text = msg
                    valid = False
                else:
                    field.error_text = None

            if email_field.value and email_field.value.strip() and "@" not in email_field.value:
                email_field.error_text = "Email invalide"
                valid = False

            if password_field.value or confirm_password_field.value:
                if password_field.value != confirm_password_field.value:
                    confirm_password_field.error_text = "Les mots de passe ne correspondent pas"
                    valid = False
                else:
                    confirm_password_field.error_text = None
            else:
                confirm_password_field.error_text = None

            page.update()
            return valid

        def on_create(e):
            if not validate():
                return
            hide_dialog(dialog)
            payload = {
                "username": username_field.value.strip() if username_field.value else None,
                "first_name": first_name_field.value.strip(),
                "last_name": last_name_field.value.strip(),
                "email": email_field.value.strip(),
                "phone": phone_field.value.strip(),
                "sex": sex_field.value,
                "birth_date": birth_date_field.value.strip() or None,
                "role": role_field.value,
                "password": password_field.value or None
            }
            try:
                response = auth.api.post("/users/create-internal/", json=payload)
                print(f"🔍 CREATE USER — payload envoyé : {payload}")
                print(f"🔍 CREATE USER — réponse backend : {response!r}")
                if response is True or response is None or (isinstance(response, dict) and "error" not in response):
                    username = response.get("username", "N/A") if isinstance(response, dict) else "N/A"
                    temp_pwd = response.get("temporary_password") if isinstance(response, dict) else None

                    msg = f"✅ Utilisateur créé avec succès\n\n👤 Identifiant : {username}"
                    if temp_pwd:
                        msg += f"\n🔑 Mot de passe : {temp_pwd}"
                    show_snack(msg)
                    load_users()
                else:
                    err = response.get("error", "Erreur inconnue") if isinstance(response, dict) else str(response)
                    show_snack(f"Erreur: {err}", True)
            except Exception as exc:
                print(f"🔍 CREATE USER — EXCEPTION : {exc}")
                show_snack(f"❌ {_friendly_error(exc)}", True)
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row([ft.Icon(ft.Icons.PERSON_ADD, color=ft.Colors.GREEN_700), ft.Text("Nouvel utilisateur")]),
            content=ft.Container(
                content=ft.Column([
                    username_field,
                    ft.Row([first_name_field, last_name_field]),
                    ft.Row([email_field, phone_field]),
                    ft.Row([sex_field, birth_date_field]),
                    role_field,
                    ft.Row([password_field, confirm_password_field]),
                ], spacing=12, tight=True, scroll=ft.ScrollMode.AUTO),
                width=550,
                height=420,
            ),
            actions=[
                ft.TextButton(content=ft.Text("Annuler"), on_click=on_cancel),
                ft.ElevatedButton(content=ft.Text("Créer"), bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE, on_click=on_create),
            ]
        )
        show_dialog(dialog)

    # ==========================================================================
    # ACTIONS : SUPPRESSION
    # ==========================================================================
    def confirm_delete(user):
        def on_cancel(e):
            hide_dialog(dialog)

        def on_confirm(e):
            hide_dialog(dialog)
            try:
                response = auth.api.delete(f"/users/{user['id']}/")
                if response is True or response is None or (isinstance(response, dict) and "error" not in response):
                    show_snack("Utilisateur supprimé avec succès")
                    load_users()
                else:
                    err = response.get("error", "Erreur inconnue") if isinstance(response, dict) else str(response)
                    show_snack(f"Erreur: {err}", True)
            except Exception:
                show_snack("Erreur de connexion", True)

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row([ft.Icon(ft.Icons.DELETE_FOREVER, color=ft.Colors.RED_700), ft.Text("Confirmation")]),
            content=ft.Text(f"Supprimer {user.get('first_name', '')} {user.get('last_name', '')} ?"),
            actions=[
                ft.TextButton(content=ft.Text("Annuler"), on_click=on_cancel),
                ft.ElevatedButton(content=ft.Text("Supprimer"), bgcolor=ft.Colors.RED_700, color=ft.Colors.WHITE, on_click=on_confirm),
            ]
        )
        show_dialog(dialog)

    # ==========================================================================
    # ACTIONS : MODIFICATION
    # ==========================================================================
    def edit_user(user):
        username_field = ft.TextField(
            label="Nom d'utilisateur (non modifiable)",
            value=user.get("username", ""),
            expand=True,
            read_only=True,
            prefix_icon=ft.Icons.LOCK_OUTLINE,
            text_size=12,
        )

        first_name_field = ft.TextField(label="Prénom *", value=user.get("first_name", ""), expand=True)
        last_name_field = ft.TextField(label="Nom *", value=user.get("last_name", ""), expand=True)
        email_field = ft.TextField(label="Email *", value=user.get("email", ""), expand=True)
        phone_field = ft.TextField(label="Téléphone", value=user.get("phone", ""), expand=True)

        sex_field = ft.Dropdown(
            label="Sexe", value=user.get("sex", "N"), expand=True,
            options=[
                ft.dropdown.Option("M", "Masculin"),
                ft.dropdown.Option("F", "Féminin"),
                ft.dropdown.Option("O", "Autre"),
                ft.dropdown.Option("N", "Non renseigné")
            ]
        )

        birth_date_field = ft.TextField(
            label="Date de naissance *",
            value=user.get("birth_date", "") or "",
            expand=True,
            read_only=True,
            hint_text="AAAA-MM-JJ",
            prefix_icon=ft.Icons.CALENDAR_MONTH,
        )

        def on_birth_date_change(e: ft.ControlEvent):
            if e.control.value:
                birth_date_field.value = e.control.value.strftime("%Y-%m-%d")
                birth_date_field.error_text = None
                page.update()

        try:
            initial_date = datetime.strptime(user.get("birth_date", ""), "%Y-%m-%d") if user.get("birth_date") else datetime.now()
        except Exception:
            initial_date = datetime.now()

        birth_date_picker = ft.DatePicker(
            first_date=datetime(1900, 1, 1),
            last_date=datetime.now(),
            value=initial_date,
            on_change=on_birth_date_change,
        )
        birth_date_field.on_focus = lambda e: show_date_picker(birth_date_picker)

        role_field = ft.Dropdown(
            label="Rôle *", value=user.get("role", "client"), expand=True,
            options=[
                ft.dropdown.Option("admin", "Administrateur"),
                ft.dropdown.Option("agent", "Agent"),
                ft.dropdown.Option("secretariat", "Secrétariat"),
                ft.dropdown.Option("client", "Client")
            ]
        )

        def on_cancel(e):
            hide_dialog(dialog)

        def validate() -> bool:
            valid = True
            required = [
                (first_name_field, "Champ requis"),
                (last_name_field, "Champ requis"),
                (email_field, "Champ requis"),
                (birth_date_field, "Champ requis"),
            ]
            for field, msg in required:
                if not field.value or not field.value.strip():
                    field.error_text = msg
                    valid = False
                else:
                    field.error_text = None
            if email_field.value and email_field.value.strip() and "@" not in email_field.value:
                email_field.error_text = "Email invalide"
                valid = False
            page.update()
            return valid

        def on_save(e):
            if not validate():
                return
            hide_dialog(dialog)
            payload = {
                "first_name": first_name_field.value.strip(),
                "last_name": last_name_field.value.strip(),
                "email": email_field.value.strip(),
                "phone": phone_field.value.strip(),
                "sex": sex_field.value,
                "birth_date": birth_date_field.value.strip() or None,
                "role": role_field.value,
                "is_active": user.get("is_active", True),
                "is_approved": user.get("is_approved", True),
            }
            # 🔍 DIAGNOSTIC TEMPORAIRE : à retirer une fois l'enregistrement
            # confirmé fiable. Affiche dans le terminal le payload envoyé
            # et la réponse brute du backend.
            try:
                response = auth.api.put(f"/users/{user['id']}/", json=payload)
                print(f"🔍 EDIT USER — payload envoyé : {payload}")
                print(f"🔍 EDIT USER — réponse backend : {response!r}")
                if response is True or response is None or (isinstance(response, dict) and "error" not in response):
                    show_snack("Utilisateur modifié avec succès")
                    load_users()
                else:
                    err = response.get("error", "Erreur inconnue") if isinstance(response, dict) else str(response)
                    show_snack(f"Erreur: {err}", True)
            except Exception as exc:
                print(f"🔍 EDIT USER — EXCEPTION : {exc}")
                show_snack(f"❌ {_friendly_error(exc)}", True)

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row([ft.Icon(ft.Icons.EDIT, color=ft.Colors.BLUE_700), ft.Text("Modifier utilisateur")]),
            content=ft.Container(
                content=ft.Column([
                    username_field,
                    ft.Row([first_name_field, last_name_field]),
                    ft.Row([email_field, phone_field]),
                    ft.Row([sex_field, birth_date_field]),
                    role_field
                ], spacing=12, tight=True, scroll=ft.ScrollMode.AUTO),
                width=550,
                height=380,
            ),
            actions=[
                ft.TextButton(content=ft.Text("Annuler"), on_click=on_cancel),
                ft.ElevatedButton(content=ft.Text("Enregistrer"), bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE, on_click=on_save),
            ]
        )
        show_dialog(dialog)

    # ==========================================================================
    # ACTIONS RAPIDES (Toggle)
    # ==========================================================================
    def toggle_active(user):
        new_status = not user.get("is_active", True)
        try:
            response = auth.api.put(f"/users/{user['id']}/", json={"is_active": new_status})
            if response is True or response is None or (isinstance(response, dict) and "error" not in response):
                show_snack(f"Utilisateur {'activé' if new_status else 'désactivé'}")
                load_users()
        except Exception:
            show_snack("Erreur", True)

    def toggle_approve(user):
        new_status = not user.get("is_approved", True)
        endpoint = "approve" if new_status else "reject"
        try:
            response = auth.api.patch(f"/users/{user['id']}/{endpoint}/")
            if response is True or response is None or (isinstance(response, dict) and "error" not in response):
                show_snack(f"Utilisateur {'approuvé' if new_status else 'rejeté'}")
                load_users()
        except Exception:
            show_snack("Erreur", True)

    # ==========================================================================
    # COMPOSANTS UI
    # ==========================================================================
    search_field = ft.TextField(hint_text="Rechercher...", prefix_icon=ft.Icons.SEARCH, expand=True, border_radius=8, on_change=filter_users)
    new_user_btn = ft.ElevatedButton(content=ft.Text("Nouvel utilisateur"), icon=ft.Icons.PERSON_ADD, bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE, on_click=create_user)
    refresh_btn = ft.IconButton(icon=ft.Icons.REFRESH, tooltip="Actualiser", on_click=load_users)
    back_btn = ft.IconButton(icon=ft.Icons.ARROW_BACK, tooltip="Retour", on_click=go_back, icon_size=24)

    header = ft.Container(
        content=ft.Row([
            ft.Text("Utilisateur", weight=ft.FontWeight.BOLD, size=12, expand=3),
            ft.Text("Contact", weight=ft.FontWeight.BOLD, size=12, expand=3),
            ft.Text("Rôle", weight=ft.FontWeight.BOLD, size=12, width=110),
            ft.Text("Création", weight=ft.FontWeight.BOLD, size=12, width=110),
            ft.Text("Statut", weight=ft.FontWeight.BOLD, size=12, width=90),
            ft.Text("Actions", weight=ft.FontWeight.BOLD, size=12, width=180)
        ], alignment=ft.MainAxisAlignment.START, spacing=8),
        padding=10, bgcolor=ft.Colors.GREY_200,
        border_radius=ft.BorderRadius(top_left=8, top_right=8, bottom_left=0, bottom_right=0)
    )

    users_container = ft.Column(spacing=5)

    def render_users(display_users=None):
        if display_users is None: display_users = users
        users_container.controls.clear()

        if not display_users:
            users_container.controls.append(
                ft.Container(
                    content=ft.Column([ft.Icon(ft.Icons.PERSON_OFF, size=48, color=ft.Colors.GREY_400), ft.Text("Aucun utilisateur trouvé.", color=ft.Colors.GREY_600)], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    alignment=ft.Alignment(0, 0), padding=40
                )
            )
            page.update()
            return

        for user in display_users:
            created_at = user.get("created_at")
            creation_date = created_at[:10] if created_at else "N/A"
            is_active = user.get("is_active", True)
            is_approved = user.get("is_approved", True)

            if is_active and is_approved:
                status_icon, status_color, status_text = ft.Icons.CHECK_CIRCLE, ft.Colors.GREEN_700, "Actif"
            elif not is_approved:
                status_icon, status_color, status_text = ft.Icons.HOURGLASS_EMPTY, ft.Colors.ORANGE_700, "En attente"
            else:
                status_icon, status_color, status_text = ft.Icons.BLOCK, ft.Colors.RED_700, "Inactif"

            row = ft.Container(
                content=ft.Row([
                    # Colonne Utilisateur — nom + @username, texte tronqué si trop long
                    ft.Column([
                        ft.Text(
                            f"{user.get('first_name', '')} {user.get('last_name', '')}",
                            weight=ft.FontWeight.BOLD, size=13,
                            overflow=ft.TextOverflow.ELLIPSIS, max_lines=1,
                        ),
                        ft.Text(
                            f"@{user.get('username', '')}", size=11, color=ft.Colors.GREY_600,
                            overflow=ft.TextOverflow.ELLIPSIS, max_lines=1,
                        ),
                    ], expand=3, spacing=2, tight=True),

                    # Colonne Contact — email + téléphone, texte tronqué si trop long
                    ft.Column([
                        ft.Row([
                            ft.Icon(ft.Icons.EMAIL, size=14),
                            ft.Text(user.get("email", ""), size=11, overflow=ft.TextOverflow.ELLIPSIS, max_lines=1, expand=True),
                        ], spacing=4, tight=True),
                        ft.Row([
                            ft.Icon(ft.Icons.PHONE, size=14),
                            ft.Text(user.get("phone") or "N/A", size=11, overflow=ft.TextOverflow.ELLIPSIS, max_lines=1, expand=True),
                        ], spacing=4, tight=True),
                    ], expand=3, spacing=2, tight=True),

                    # Colonne Rôle — largeur fixe, alignée avec le header
                    ft.Container(
                        content=ft.Row([ft.Icon(ft.Icons.BADGE, size=14), ft.Text(user.get("role", "").capitalize(), size=11, overflow=ft.TextOverflow.ELLIPSIS, max_lines=1)], spacing=4, tight=True),
                        width=110,
                    ),

                    # Colonne Création — largeur fixe, alignée avec le header
                    ft.Container(
                        content=ft.Row([ft.Icon(ft.Icons.CALENDAR_MONTH, size=15, color=ft.Colors.BLUE_700), ft.Text(creation_date, size=11)], spacing=4, tight=True),
                        width=110,
                    ),

                    # Colonne Statut — largeur fixe, alignée avec le header
                    ft.Container(
                        content=ft.Row([ft.Icon(status_icon, color=status_color, size=18), ft.Text(status_text, size=11, color=status_color)], spacing=4, tight=True),
                        width=90,
                    ),

                    # Colonne Actions — largeur fixe, icônes resserrées
                    ft.Container(
                        content=ft.Row([
                            ft.IconButton(icon=ft.Icons.EDIT, icon_size=18, icon_color=ft.Colors.BLUE_700, tooltip="Modifier", on_click=lambda e, u=user: edit_user(u), style=ft.ButtonStyle(padding=4)),
                            ft.IconButton(icon=ft.Icons.PLAY_ARROW if not is_active else ft.Icons.BLOCK, icon_size=18, icon_color=ft.Colors.GREEN_700 if not is_active else ft.Colors.ORANGE_700, tooltip="Activer/Désactiver", on_click=lambda e, u=user: toggle_active(u), style=ft.ButtonStyle(padding=4)),
                            ft.IconButton(icon=ft.Icons.CHECK_CIRCLE if not is_approved else ft.Icons.CANCEL, icon_size=18, icon_color=ft.Colors.GREEN_700 if not is_approved else ft.Colors.RED_700, tooltip="Approuver/Rejeter", on_click=lambda e, u=user: toggle_approve(u), style=ft.ButtonStyle(padding=4)),
                            ft.IconButton(icon=ft.Icons.DELETE, icon_size=18, icon_color=ft.Colors.RED_700, tooltip="Supprimer", on_click=lambda e, u=user: confirm_delete(u), style=ft.ButtonStyle(padding=4)),
                        ], spacing=0, tight=True),
                        width=180,
                    ),
                ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                padding=10, bgcolor=ft.Colors.WHITE, border=ft.Border.all(1, ft.Colors.GREY_300), border_radius=8
            )
            users_container.controls.append(row)
        page.update()

    load_users()

    device = get_device_type(page.window.width or 1200)

    return ft.View(
        route="/users",
        controls=[
            ft.Row([back_btn, search_field, new_user_btn, refresh_btn], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Container(height=10),
            header,
            ft.Container(height=10),
            users_container,
        ],
        bgcolor=Colors.BACKGROUND,
        padding=16 if device == "mobile" else 32,
    )