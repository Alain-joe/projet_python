"""
views/exhumations/request.py — Formulaire de demande d'exhumation avec recherche de défunt.
Compatible Flet 0.86.0
"""
from __future__ import annotations
import flet as ft
from core.auth import AuthState
from core.api import ApiError, Endpoints
from core.theme import Colors, get_device_type, heading_style


def build_exhumation_request_view(page: ft.Page, auth: AuthState) -> ft.View:
    selected_inhumation = None
    
    search_field = ft.TextField(label="Nom du défunt", border_radius=12, filled=True, bgcolor=Colors.BACKGROUND)
    search_results = ft.Column(spacing=5, scroll=ft.ScrollMode.AUTO, expand=False)
    
    motif_field = ft.TextField(label="Motif de la demande", multiline=True, min_lines=3, border_radius=12, filled=True, bgcolor=Colors.BACKGROUND)
    date_field = ft.TextField(label="Date prévue (AAAA-MM-JJ)", border_radius=12, filled=True, bgcolor=Colors.BACKGROUND)
    
    info_box = ft.Container(visible=False, padding=16, bgcolor="#E8F5E9", border_radius=8)
    error_text = ft.Text("", color=Colors.ERROR, size=13, visible=False)
    success_text = ft.Text("", color=Colors.PRIMARY, size=13, visible=False)
    loading = ft.ProgressRing(visible=False)

    def get_user_id() -> int | None:
        """Récupère l'ID utilisateur de manière fiable"""
        # Méthode 1 : Depuis auth.user
        if auth.user and auth.user.get("id"):
            return int(auth.user.get("id"))
        
        # Méthode 2 : Décoder le token JWT
        if auth.access_token:
            try:
                import jwt
                payload = jwt.decode(auth.access_token, options={"verify_signature": False})
                return int(payload.get("user_id"))
            except Exception:
                pass
        
        return None

    def search_inhumation(e):
        nom = search_field.value.strip()
        if not nom:
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
            search_results.controls = [ft.Text(f"Erreur: {exc.message}", color=Colors.ERROR)]
        finally:
            page.update()

    def select_inhumation(inh: dict):
        nonlocal selected_inhumation
        selected_inhumation = inh
        
        info_box.content = ft.Column([
            ft.Text("✅ Défunt sélectionné :", weight=ft.FontWeight.BOLD, color="#2E7D32"),
            ft.Text(f"Nom : {inh.get('defunt_nom')} {inh.get('defunt_prenom')}"),
            ft.Text(f"Caveau : {inh.get('grave_code')}"),
            ft.Text(f"Date de décès : {inh.get('defunt_date_deces')}"),
        ], spacing=4)
        info_box.visible = True
        search_results.visible = False
        page.update()

    def submit_request(e):
        if not selected_inhumation:
            error_text.value = "Veuillez d'abord rechercher et sélectionner un défunt."
            error_text.visible = True
            page.update()
            return

        if not motif_field.value or not date_field.value:
            error_text.value = "Le motif et la date sont obligatoires."
            error_text.visible = True
            page.update()
            return

        # ✅ Récupération fiable de l'ID utilisateur
        user_id = get_user_id()
        if not user_id:
            error_text.value = "Erreur d'authentification. Veuillez vous reconnecter."
            error_text.visible = True
            page.update()
            return

        loading.visible = True
        page.update()

        try:
            payload = {
                "inhumation_id": int(selected_inhumation["id"]),
                "demandeur_id": user_id,
                "motif": motif_field.value,
                "date_prevue": date_field.value,
            }
            auth.api.post("/cemetery/exhumations", json=payload)
            
            success_text.value = "✅ Demande envoyée avec succès. En attente de validation."
            success_text.visible = True
            error_text.visible = False
            page.update()
            
            import time
            time.sleep(1.5)
            page.go("/exhumations")
        except ApiError as exc:
            error_text.value = f"Échec : {exc.message}"
            error_text.visible = True
            page.update()
        finally:
            loading.visible = False

    device = get_device_type(page.window.width or 1200)

    form_content = ft.Column(
        [
            ft.Text("Nouvelle demande d'exhumation", style=heading_style(size=22)),
            ft.Container(height=10),
            
            ft.Text("Étape 1 : Rechercher le défunt", style=heading_style(size=16)),
            ft.Row([
                search_field,
                ft.ElevatedButton(
                    "Rechercher",
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
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    return ft.View(
        route="/exhumations/nouvelle",
        controls=[
            ft.Container(
                content=form_content,
                padding=16 if device == "mobile" else 32,
                expand=True,
            )
        ],
        bgcolor=Colors.BACKGROUND,
        scroll=ft.ScrollMode.AUTO,
    )