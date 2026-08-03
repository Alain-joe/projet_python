"""
core/router.py — Navigation par rôle (RBAC) avec dispatchers.
Compatible Flet 0.86.3
CORRECTION : Suppression de la route /cimetiere/alleys (dessin d'allées abandonné
au profit d'une configuration standard en une seule étape).
CORRECTION CRITIQUE : _on_resize plantait avec
"TypeError: RouteChangeEvent.__init__() missing 2 required positional
arguments: 'name' and 'control'" — cette version de Flet exige ces deux
arguments en plus de 'route'. Correctif : la logique de rendu de route est
extraite dans _render_route(path), qui ne nécessite aucun objet Event.
_on_route_change et _on_resize appellent tous les deux cette méthode
commune, évitant de construire un RouteChangeEvent factice.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable
import flet as ft
from views.notifications.list import build_notifications_list_view
from core.auth import AuthState, Role
from core.theme import Colors
from views.shared.navigation import build_navigation


@dataclass
class Route:
    path: str
    view_builder: Callable[[ft.Page, AuthState], ft.View]
    allowed_roles: tuple[Role, ...] | None = None
    public: bool = False


class Router:
    def __init__(self, page: ft.Page, auth: AuthState):
        self.page = page
        self.auth = auth
        self._routes: dict[str, Route] = {}
        self.page.on_route_change = self._on_route_change
        # ✅ Redéclenche le rendu de la route courante quand la taille réelle
        # de la fenêtre/viewport est connue (corrige le mode mobile).
        self.page.on_resize = self._on_resize

    def register(self, route: Route) -> None:
        self._routes[route.path] = route

    def register_many(self, routes: list[Route]) -> None:
        for r in routes:
            self.register(r)

    def go(self, path: str) -> None:
        self.page.go(path)

    def default_dashboard_path(self) -> str:
        mapping = {
            Role.ADMIN: "/dashboard/admin",
            Role.SECRETARIAT: "/dashboard/secretariat",
            Role.AGENT: "/dashboard/agent",
            Role.CLIENT: "/dashboard/client"
        }
        return mapping.get(self.auth.role, "/login")

    def _on_resize(self, e: ft.ControlEvent) -> None:
        # ✅ CORRECTION : n'appelle plus _on_route_change avec un faux
        # RouteChangeEvent (signature incompatible avec cette version de
        # Flet) — appelle directement _render_route avec la route actuelle.
        if self.page.route:
            self._render_route(self.page.route)

    def _on_route_change(self, e: ft.RouteChangeEvent) -> None:
        self._render_route(e.route)

    def _render_route(self, raw_route: str) -> None:
        target_path = raw_route.split("?")[0].rstrip("/")
        route = self._routes.get(target_path)
        if route is None:
            self._render_not_found()
            return
        if not route.public and not self.auth.is_authenticated:
            self.page.views.clear()
            self.page.go("/login")
            return
        if route.allowed_roles is not None and self.auth.role not in route.allowed_roles:
            self.page.go(self.default_dashboard_path())
            return
        view = self._build_view_with_navigation(route)
        self.page.views.clear()
        self.page.views.append(view)
        self.page.update()

    def _build_view_with_navigation(self, route: Route) -> ft.View:
        try:
            original_view = route.view_builder(self.page, self.auth)
            if original_view is None:
                raise ValueError(f"La fonction de vue pour '{route.path}' a retourné None.")
        except Exception as exc:
            import traceback
            tb = traceback.format_exc()
            print(f"ERREUR DE CONSTRUCTION DE VUE : {route.path}\n{tb}")
            return ft.View(
                route=route.path,
                controls=[
                    ft.Container(
                        content=ft.Column([
                            ft.Text(f"Erreur page « {route.path} »", size=18, weight=ft.FontWeight.BOLD, color="#C62828"),
                            ft.Text(str(exc), color="#C62828", selectable=True),
                            ft.Divider(),
                            ft.Text("Trace complète :", weight=ft.FontWeight.BOLD, size=12),
                            ft.Text(tb, size=11, selectable=True, font_family="Consolas")
                        ], spacing=10),
                        padding=24
                    )
                ],
                bgcolor="#FFF5F5"
            )

        if route.public:
            return original_view

        nav = build_navigation(self.page, self.auth)
        if nav["appbar"]:
            return ft.View(
                route=route.path,
                appbar=nav["appbar"],
                controls=original_view.controls,
                bgcolor=original_view.bgcolor or Colors.BACKGROUND,
                padding=original_view.padding,
                scroll=ft.ScrollMode.AUTO
            )
        else:
            return ft.View(
                route=route.path,
                controls=[
                    ft.Row([
                        nav["rail"],
                        ft.Container(
                            content=ft.Column(
                                controls=original_view.controls,
                                expand=True,
                                scroll=ft.ScrollMode.AUTO
                            ),
                            expand=True,
                            padding=original_view.padding or 0
                        )
                    ], expand=True)
                ],
                bgcolor=original_view.bgcolor or Colors.BACKGROUND
            )

    def _render_not_found(self) -> None:
        self.page.views.clear()
        self.page.views.append(
            ft.View(
                route="/not-found",
                controls=[
                    ft.SafeArea(
                        ft.Column([
                            ft.Text("Page introuvable", size=24, weight=ft.FontWeight.BOLD),
                            ft.Container(height=20),
                            ft.ElevatedButton(
                                content=ft.Row([ft.Icon(ft.Icons.HOME), ft.Text("Retour à l'accueil")], spacing=5),
                                on_click=lambda _: self.go(self.default_dashboard_path())
                            )
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, expand=True)
                    )
                ]
            )
        )
        self.page.update()


# ==============================================================================
# DISPATCHERS DE ROUTES
# ==============================================================================
def route_exhumations(page: ft.Page, auth: AuthState) -> ft.View:
    if auth.role == Role.SECRETARIAT:
        from views.exhumations.list_secretaire import build_exhumations_list_secretaire_view
        return build_exhumations_list_secretaire_view(page, auth)
    elif auth.role == Role.AGENT:
        from views.exhumations.list_agent import build_exhumations_list_agent_view
        return build_exhumations_list_agent_view(page, auth)
    from views.exhumations.list import build_exhumations_list_view
    return build_exhumations_list_view(page, auth)

def route_graves(page: ft.Page, auth: AuthState) -> ft.View:
    if auth.role == Role.SECRETARIAT:
        from views.graves.list_secretaire import build_graves_list_secretaire_view
        return build_graves_list_secretaire_view(page, auth)
    from views.graves.list import build_graves_list_view
    return build_graves_list_view(page, auth)

def route_reservations(page: ft.Page, auth: AuthState) -> ft.View:
    if auth.role == Role.SECRETARIAT:
        from views.reservations.list_secretaire import build_reservations_list_secretaire_view
        return build_reservations_list_secretaire_view(page, auth)
    elif auth.role == Role.AGENT:
        from views.reservations.list_agent import build_reservations_list_agent_view
        return build_reservations_list_agent_view(page, auth)
    from views.reservations.list import build_reservations_list_view
    return build_reservations_list_view(page, auth)

def route_inhumations(page: ft.Page, auth: AuthState) -> ft.View:
    if auth.role == Role.AGENT:
        from views.inhumations.list_agent import build_inhumations_list_agent_view
        return build_inhumations_list_agent_view(page, auth)
    from views.inhumations.list import build_inhumations_list_view
    return build_inhumations_list_view(page, auth)


def build_routes(auth: AuthState) -> list[Route]:
    from views.auth.welcome import build_welcome_view
    from views.auth.register import build_register_view
    from views.auth.login import build_login_view
    from views.auth.mfa import build_mfa_view

    from views.finance.pending_virements import build_pending_virements_view

    from views.dashboard.admin import build_admin_dashboard_view
    from views.dashboard.secretariat import build_secretariat_dashboard_view
    from views.dashboard.agent import build_agent_dashboard_view
    from views.dashboard.client import build_client_dashboard_view

    from views.map.view import build_map_view
    from views.finance.payment import build_payment_view
    from views.finance.admin import build_finance_admin_view
    from views.concessions.list import build_concessions_list_view
    from views.concessions.detail import build_concession_detail_view
    from views.concessions.renew import build_concession_renewal_view
    from views.concessions.create import build_concession_create_view
    from views.concessions.ready_list import build_concessions_ready_view
    from views.users.list import build_users_list_view
    from views.users.create import build_user_create_view
    from views.users.profile import build_profile_view
    from views.alerts.list import build_alerts_view
    from views.reports.list import build_reports_view
    from views.reports.logs import build_audit_logs_view
    from views.cemetery.config import build_cemetery_config_view

    from views.cemetery.initial_setup import build_initial_setup_view
    from views.cemetery.sections_list import build_sections_list_view
    from views.cemetery.alleys_list import build_alleys_list_view

    from views.graves.report_problem import build_report_problem_view
    from views.graves.signalements_list import build_signalements_list_view
    from views.graves.signalement_detail import build_signalement_detail_view
    from views.graves.generate_grid import build_generate_grid_view

    from views.shared.placeholders import build_cemeteries_view, build_sections_view, build_settings_view

    from views.reservations.list import build_reservations_list_view
    from views.reservations.client_list import build_client_reservations_list_view
    from views.exhumations.client_exhumations import build_client_exhumations_view
    from views.finance.client_payments import build_client_payments_view

    return [
        Route("/welcome", build_welcome_view, public=True),
        Route("/register", build_register_view, public=True),
        Route("/login", build_login_view, public=True),
        Route("/mfa", build_mfa_view, public=True),

        Route("/dashboard/admin", build_admin_dashboard_view, allowed_roles=(Role.ADMIN,)),
        Route("/dashboard/secretariat", build_secretariat_dashboard_view, allowed_roles=(Role.SECRETARIAT,)),
        Route("/dashboard/agent", build_agent_dashboard_view, allowed_roles=(Role.AGENT,)),
        Route("/dashboard/client", build_client_dashboard_view, allowed_roles=(Role.CLIENT,)),

        Route("/cimetiere/setup", build_initial_setup_view, allowed_roles=(Role.ADMIN,)),
        Route("/cimetiere/sections", build_sections_list_view, allowed_roles=(Role.ADMIN, Role.SECRETARIAT)),
        Route("/cimetiere/alleys-list", build_alleys_list_view, allowed_roles=(Role.ADMIN, Role.SECRETARIAT)),

        Route("/cemeteries", build_cemeteries_view, allowed_roles=(Role.ADMIN, Role.SECRETARIAT)),
        Route("/sections", build_sections_view, allowed_roles=(Role.ADMIN, Role.SECRETARIAT)),

        Route("/graves", route_graves, allowed_roles=(Role.ADMIN, Role.SECRETARIAT, Role.AGENT)),
        Route("/graves/generate-grid", build_generate_grid_view, allowed_roles=(Role.ADMIN,)),

        Route("/graves/signaler", build_report_problem_view, allowed_roles=(Role.AGENT, Role.ADMIN, Role.SECRETARIAT, Role.CLIENT)),
        Route("/graves/signalements", build_signalements_list_view, allowed_roles=(Role.ADMIN, Role.SECRETARIAT, Role.AGENT)),
        Route("/graves/signalements/detail", build_signalement_detail_view, allowed_roles=(Role.ADMIN, Role.SECRETARIAT, Role.AGENT)),

        Route("/concessions", build_concessions_list_view, allowed_roles=(Role.ADMIN, Role.SECRETARIAT)),
        Route("/concessions/ready", build_concessions_ready_view, allowed_roles=(Role.ADMIN, Role.SECRETARIAT)),
        Route("/concessions/nouvelle", build_concession_create_view, allowed_roles=(Role.ADMIN, Role.SECRETARIAT)),
        Route("/concessions/detail", build_concession_detail_view, allowed_roles=(Role.ADMIN, Role.SECRETARIAT, Role.CLIENT)),
        Route("/concessions/renewal", build_concession_renewal_view, allowed_roles=(Role.ADMIN, Role.SECRETARIAT)),

        Route("/reservations", route_reservations, allowed_roles=(Role.ADMIN, Role.SECRETARIAT, Role.AGENT)),
        Route("/reservations/nouvelle", lambda p, a: __import__('views.reservations.form', fromlist=['build_reservation_form_view']).build_reservation_form_view(p, a), allowed_roles=(Role.CLIENT, Role.ADMIN, Role.SECRETARIAT)),

        Route("/exhumations", route_exhumations, allowed_roles=(Role.ADMIN, Role.SECRETARIAT, Role.AGENT)),
        Route("/inhumations", route_inhumations, allowed_roles=(Role.ADMIN, Role.SECRETARIAT, Role.AGENT)),
        Route("/inhumations/confirm", lambda p, a: __import__('views.inhumations.confirm', fromlist=['build_inhumation_confirm_view']).build_inhumation_confirm_view(p, a), allowed_roles=(Role.ADMIN, Role.SECRETARIAT, Role.AGENT)),

        Route("/finance", build_finance_admin_view, allowed_roles=(Role.ADMIN, Role.SECRETARIAT)),
        Route("/finance/virements-en-attente", build_pending_virements_view, allowed_roles=(Role.ADMIN, Role.SECRETARIAT)),
        Route("/alerts", build_alerts_view, allowed_roles=(Role.ADMIN, Role.SECRETARIAT)),
        Route("/reports", build_reports_view, allowed_roles=(Role.ADMIN, Role.SECRETARIAT)),
        Route("/logs", build_audit_logs_view, allowed_roles=(Role.ADMIN, Role.SECRETARIAT)),
        Route("/users", build_users_list_view, allowed_roles=(Role.ADMIN,)),
        Route("/users/nouveau", build_user_create_view, allowed_roles=(Role.ADMIN, Role.SECRETARIAT)),
        Route("/settings", build_settings_view, allowed_roles=(Role.ADMIN,)),
        Route("/profil", build_profile_view, allowed_roles=(Role.ADMIN, Role.SECRETARIAT, Role.AGENT, Role.CLIENT)),
        Route("/cimetiere/config", build_cemetery_config_view, allowed_roles=(Role.ADMIN,)),
        Route("/carte", build_map_view, allowed_roles=None),
        Route("/paiements", build_payment_view, allowed_roles=None),
        Route("/notifications", build_notifications_list_view, allowed_roles=(Role.ADMIN, Role.SECRETARIAT, Role.AGENT, Role.CLIENT)),

        Route("/reservations/mine", build_client_reservations_list_view, allowed_roles=(Role.CLIENT,)),
        Route("/exhumations/client", build_client_exhumations_view, allowed_roles=(Role.CLIENT,)),
        Route("/finance/client-paiements", build_client_payments_view, allowed_roles=(Role.CLIENT,)),
    ]