"""
core/router.py — Navigation par rôle (RBAC).
Compatible Flet 0.86.0
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
            Role.CLIENT: "/dashboard/client",
        }
        return mapping.get(self.auth.role, "/login")

    def _on_route_change(self, e: ft.RouteChangeEvent) -> None:
        target_path = e.route.split("?")[0].rstrip("/")
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
            print(f"ERREUR DE CONSTRUCTION DE VUE : {route.path}")
            print(tb)
            return ft.View(
                route=route.path,
                controls=[
                    ft.Container(
                        content=ft.Column([
                            ft.Text(f"Erreur page « {route.path} »", size=18, weight=ft.FontWeight.BOLD, color="#C62828"),
                            ft.Text(str(exc), color="#C62828", selectable=True),
                            ft.Divider(),
                            ft.Text("Trace complète :", weight=ft.FontWeight.BOLD, size=12),
                            ft.Text(tb, size=11, selectable=True, font_family="Consolas"),
                        ], spacing=10),
                        padding=24,
                    )
                ],
                bgcolor="#FFF5F5",
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
                scroll=ft.ScrollMode.AUTO,
            )
        else:
            return ft.View(
                route=route.path,
                controls=[
                    ft.Row(
                        [
                            nav["rail"],
                            ft.Container(
                                content=ft.Column(
                                    controls=original_view.controls,
                                    expand=True,
                                    scroll=ft.ScrollMode.AUTO,
                                ),
                                expand=True,
                                padding=original_view.padding or 0,
                            )
                        ],
                        expand=True,
                    )
                ],
                bgcolor=original_view.bgcolor or Colors.BACKGROUND,
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
                                on_click=lambda _: self.go(self.default_dashboard_path()),
                            )
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, expand=True)
                    )
                ],
            )
        )
        self.page.update()


def build_routes(auth: AuthState) -> list[Route]:
    from views.auth.login import build_login_view
    from views.auth.mfa import build_mfa_view
    from views.finance.pending_virements import build_pending_virements_view
    
    from views.dashboard.admin import build_admin_dashboard_view
    from views.dashboard.secretariat import build_secretariat_dashboard_view
    from views.dashboard.agent import build_agent_dashboard_view
    from views.dashboard.client import build_client_dashboard_view
    
    from views.reservations.list import build_reservations_list_view
    from views.reservations.form import build_reservation_form_view
    from views.map.view import build_map_view
    from views.finance.payment import build_payment_view
    from views.finance.admin import build_finance_admin_view
    from views.concessions.list import build_concessions_list_view
    from views.concessions.detail import build_concession_detail_view
    from views.concessions.renewal import build_concession_renewal_view
    from views.concessions.create import build_concession_create_view
    from views.concessions.ready_list import build_concessions_ready_view
    from views.exhumations.list import build_exhumations_list_view
    from views.inhumations.list import build_inhumations_list_view
    from views.inhumations.confirm import build_inhumation_confirm_view
    from views.users.list import build_users_list_view
    from views.users.create import build_user_create_view
    from views.users.profile import build_profile_view
    from views.graves.list import build_graves_list_view
    from views.alerts.list import build_alerts_view
    from views.reports.list import build_reports_view
    from views.reports.logs import build_audit_logs_view
    from views.cemetery.config import build_cemetery_config_view
    
    from views.cemetery.initial_setup import build_initial_setup_view
    from views.cemetery.alleys_setup import build_alleys_setup_view
    from views.cemetery.sections_list import build_sections_list_view
    from views.cemetery.alleys_list import build_alleys_list_view
    
    from views.graves.report_problem import build_report_problem_view
    from views.graves.signalements_list import build_signalements_list_view
    from views.graves.signalement_detail import build_signalement_detail_view
    
    
    from views.shared.placeholders import (
        build_cemeteries_view,
        build_sections_view,
        build_settings_view,
    )

    return [
        Route("/login", build_login_view, public=True),
        Route("/mfa", build_mfa_view, public=True),
        
        Route("/dashboard/admin", build_admin_dashboard_view, allowed_roles=(Role.ADMIN,)),
        Route("/dashboard/secretariat", build_secretariat_dashboard_view, allowed_roles=(Role.SECRETARIAT,)),
        Route("/dashboard/agent", build_agent_dashboard_view, allowed_roles=(Role.AGENT,)),
        Route("/dashboard/client", build_client_dashboard_view, allowed_roles=(Role.CLIENT,)),
        
        Route("/cimetiere/setup", build_initial_setup_view, allowed_roles=(Role.ADMIN,)),
        Route("/cimetiere/alleys", build_alleys_setup_view, allowed_roles=(Role.ADMIN,)),
        Route("/cimetiere/sections", build_sections_list_view, allowed_roles=(Role.ADMIN, Role.SECRETARIAT)),
        Route("/cimetiere/alleys-list", build_alleys_list_view, allowed_roles=(Role.ADMIN, Role.SECRETARIAT)),
        
        Route("/cemeteries", build_cemeteries_view, allowed_roles=(Role.ADMIN, Role.SECRETARIAT)),
        Route("/sections", build_sections_view, allowed_roles=(Role.ADMIN, Role.SECRETARIAT)),
        Route("/graves", build_graves_list_view, allowed_roles=(Role.ADMIN, Role.SECRETARIAT, Role.AGENT)),
        
        # ✅ CORRECTION : Ajout de Role.CLIENT pour éviter la redirection vers le dashboard si testé avec ce rôle
        Route("/graves/signaler", build_report_problem_view, allowed_roles=(Role.AGENT, Role.ADMIN, Role.SECRETARIAT, Role.CLIENT)),
        Route("/graves/signalements", build_signalements_list_view, allowed_roles=(Role.ADMIN, Role.SECRETARIAT, Role.AGENT)),
        Route("/graves/signalements/detail", build_signalement_detail_view, allowed_roles=(Role.ADMIN, Role.SECRETARIAT, Role.AGENT)),
        
        Route("/concessions", build_concessions_list_view, allowed_roles=(Role.ADMIN, Role.SECRETARIAT)),
        Route("/concessions/ready", build_concessions_ready_view, allowed_roles=(Role.ADMIN, Role.SECRETARIAT)),
        Route("/concessions/nouvelle", build_concession_create_view, allowed_roles=(Role.ADMIN, Role.SECRETARIAT)),
        Route("/concessions/detail", build_concession_detail_view, allowed_roles=(Role.ADMIN, Role.SECRETARIAT, Role.CLIENT)),
        Route("/concessions/renewal", build_concession_renewal_view, allowed_roles=(Role.ADMIN, Role.SECRETARIAT)),
        
        Route("/reservations", build_reservations_list_view, allowed_roles=(Role.ADMIN, Role.SECRETARIAT, Role.AGENT)),
        Route("/reservations/nouvelle", build_reservation_form_view, allowed_roles=(Role.CLIENT, Role.ADMIN, Role.SECRETARIAT)),
        Route("/exhumations", build_exhumations_list_view, allowed_roles=(Role.ADMIN, Role.SECRETARIAT, Role.AGENT)),
        Route("/inhumations", build_inhumations_list_view, allowed_roles=(Role.ADMIN, Role.SECRETARIAT, Role.AGENT)),
        Route("/finance", build_finance_admin_view, allowed_roles=(Role.ADMIN, Role.SECRETARIAT)),
        Route("/finance", build_finance_admin_view, allowed_roles=(Role.ADMIN, Role.SECRETARIAT)),
        Route("/inhumations", build_inhumations_list_view, allowed_roles=(Role.ADMIN, Role.SECRETARIAT, Role.AGENT)),
        Route("/inhumations/confirm", build_inhumation_confirm_view, allowed_roles=(Role.ADMIN, Role.SECRETARIAT, Role.AGENT)), # ✅ AJOUTÉ
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
    ]