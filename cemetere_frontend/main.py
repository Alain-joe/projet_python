"""
main.py — Point d'entrée de l'application (routing + auth).
Compatible Flet 0.86.3
CORRECTION : Nettoyage de l'URL sans corrompre la pile de navigation.
"""
import flet as ft
from urllib.parse import urlparse, parse_qs
import asyncio

from core.theme import apply_theme
from core.auth import AuthState
from core.router import Router, build_routes


async def main(page: ft.Page) -> None:
    print("🚀 [MAIN] Application démarrée")
    page.title = "GI2 — Gestion de Cimetière"
    page.window_min_width = 400

    apply_theme(page, dark=False)

    # ==========================================================================
    # 1. INTERCEPTION ET NETTOYAGE DES PARAMÈTRES DE L'URL
    # ==========================================================================
    parsed_url = urlparse(page.route)
    query = parse_qs(parsed_url.query)
    
    url_token = query.get("token")
    url_grave_id = query.get("grave_id")
    url_grave_code = query.get("grave_code")

    clean_path = parsed_url.path
    
    final_route_params = []
    if url_grave_id:
        final_route_params.append(f"grave_id={url_grave_id[0]}")
    if url_grave_code:
        final_route_params.append(f"grave_code={url_grave_code[0]}")
    
    # On reconstruit l'URL SANS le token pour la sécurité
    clean_route = f"{clean_path}?{'&'.join(final_route_params)}" if final_route_params else clean_path

    # ==========================================================================
    # 2. Initialisation de l'auth et restauration de session
    # ==========================================================================
    auth = AuthState()

    # On ne restaure la session QUE si l'utilisateur n'est pas déjà connecté
    if url_token and not auth.is_authenticated:
        token_str = url_token[0]
        print(f"🔑 Token détecté depuis l'URL, restauration de la session...")
        auth.restore_session(token_str)
    elif url_token and auth.is_authenticated:
        print(f"⚠️ [MAIN] Token dans l'URL ignoré : utilisateur déjà connecté ({auth.username})")

    print("[MAIN] Nettoyage initial de l'overlay et du dialog")
    page.overlay.clear()
    page.dialog = None

    def on_resize(_: ft.ControlEvent) -> None:
        page.update()
    page.on_resize = on_resize

    router = Router(page, auth)
    router.register_many(build_routes(auth))
    
    # ✅ On force l'URL propre dans le navigateur AVANT de naviguer
    page.route = clean_route
    page.update()

    # ==========================================================================
    # 3. Navigation intelligente au démarrage
    # ==========================================================================
    async def navigate_to_start():
        is_auth = auth.is_authenticated
        
        if clean_path == "/graves/signaler" and url_grave_id:
            start_route = f"/graves/signaler?grave_id={url_grave_id[0]}&grave_code={url_grave_code[0] if url_grave_code else 'Inconnu'}"
        elif clean_path == "/reservations/nouvelle" and url_grave_id:
            start_route = f"/reservations/nouvelle?grave_id={url_grave_id[0]}"
        else:
            start_route = "/dashboard/admin" if is_auth else "/login"
            
        print(f"🧭 [MAIN] Navigation vers : {start_route}")
        # ✅ Utilisation de page.go() qui est la méthode standard et sûre
        page.go(start_route)

    await navigate_to_start()


if __name__ == "__main__":
    ft.run(main, view=ft.AppView.WEB_BROWSER, port=8550)