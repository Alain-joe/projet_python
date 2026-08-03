"""
views/shared/navigation.py — Barre de navigation avec indicateur de notifications.
Compatible Flet 0.86.3

CORRECTIONS APPLIQUÉES :
- Entrées spécifiques pour le rôle CLIENT (déjà présent).
- Détection de largeur centralisée et sécurisée (déjà présent).
- Suppression totale de la tentative page.open()/page.close() pour le
  NavigationDrawer — assignation directe uniquement (déjà présent).
- Container mélangé dans le drawer retiré (déjà présent).
- ✅ BUG RACINE TROUVÉ ET CORRIGÉ : build_app_bar() faisait
  page.drawer = drawer, mais core/router.py construit ensuite une
  NOUVELLE ft.View sans jamais lui passer ce tiroir via son propre
  paramètre drawer=. Sur cette build de Flet, le tiroir doit être
  attaché explicitement à la View rendue, page.drawer seul ne suffit
  pas. build_app_bar() retourne maintenant un tuple (appbar, drawer),
  et build_navigation() l'expose dans le dict retourné sous la clé
  "drawer", pour que router.py puisse l'attacher à la View.
"""
from __future__ import annotations
from dataclasses import dataclass
import flet as ft
from core.auth import AuthState, Role
from core.theme import Colors, get_device_type


@dataclass
class NavItem:
    label: str
    icon: str
    route: str
    allowed_roles: tuple[Role, ...] | None = None


NAV_ITEMS: list[NavItem] = [
    NavItem("Tableau de bord", ft.Icons.DASHBOARD, "/dashboard/admin", allowed_roles=(Role.ADMIN,)),
    NavItem("Tableau de bord", ft.Icons.DASHBOARD, "/dashboard/secretariat", allowed_roles=(Role.SECRETARIAT,)),
    NavItem("Tableau de bord", ft.Icons.DASHBOARD, "/dashboard/agent", allowed_roles=(Role.AGENT,)),
    NavItem("Tableau de bord", ft.Icons.DASHBOARD, "/dashboard/client", allowed_roles=(Role.CLIENT,)),

    NavItem("Mon Profil", ft.Icons.PERSON, "/profil"),
    NavItem("Carte interactive", ft.Icons.MAP, "/carte"),

    NavItem("Mes réservations", ft.Icons.EVENT_NOTE, "/reservations/mine", allowed_roles=(Role.CLIENT,)),
    NavItem("Mes exhumations", ft.Icons.UNARCHIVE, "/exhumations/client", allowed_roles=(Role.CLIENT,)),
    NavItem("Mes paiements", ft.Icons.PAYMENTS, "/finance/client-paiements", allowed_roles=(Role.CLIENT,)),

    NavItem("Réservations", ft.Icons.EVENT_NOTE, "/reservations", allowed_roles=(Role.ADMIN, Role.SECRETARIAT, Role.AGENT)),
    NavItem("Concessions", ft.Icons.DESCRIPTION, "/concessions", allowed_roles=(Role.ADMIN, Role.SECRETARIAT)),
    NavItem("Concessions à créer", ft.Icons.PENDING_ACTIONS, "/concessions/ready", allowed_roles=(Role.ADMIN, Role.SECRETARIAT)),
    NavItem("Sépultures", ft.Icons.LOCATION_ON, "/graves", allowed_roles=(Role.ADMIN, Role.SECRETARIAT, Role.AGENT)),
    NavItem("Signalements Caveaux", ft.Icons.WARNING, "/graves/signalements", allowed_roles=(Role.ADMIN, Role.AGENT)),
    NavItem("Exhumations", ft.Icons.UNARCHIVE, "/exhumations", allowed_roles=(Role.ADMIN, Role.SECRETARIAT, Role.AGENT)),
    NavItem("Inhumations", ft.Icons.HISTORY, "/inhumations", allowed_roles=(Role.ADMIN, Role.SECRETARIAT, Role.AGENT)),
    NavItem("Finances", ft.Icons.ACCOUNT_BALANCE_WALLET, "/finance", allowed_roles=(Role.ADMIN, Role.SECRETARIAT)),
    NavItem("Alertes", ft.Icons.NOTIFICATIONS_ACTIVE, "/alerts", allowed_roles=(Role.ADMIN, Role.SECRETARIAT)),
    NavItem("Rapports", ft.Icons.BAR_CHART, "/reports", allowed_roles=(Role.ADMIN, Role.SECRETARIAT)),
    NavItem("Journal d'Audit", ft.Icons.RECEIPT_LONG, "/logs", allowed_roles=(Role.ADMIN, Role.SECRETARIAT)),
    NavItem("Notifications", ft.Icons.NOTIFICATIONS, "/notifications"),
    NavItem("Config. Cimetière", ft.Icons.SETTINGS, "/cimetiere/config", allowed_roles=(Role.ADMIN,)),
    NavItem("Utilisateurs", ft.Icons.GROUP, "/users", allowed_roles=(Role.ADMIN,)),
]


def get_page_width(page: ft.Page) -> int:
    width = getattr(page, "width", None)
    if not width and hasattr(page, "window") and page.window is not None:
        width = getattr(page.window, "width", None)
    return int(width) if width else 1200


def _visible_items(auth: AuthState) -> list[NavItem]:
    return [item for item in NAV_ITEMS if item.allowed_roles is None or auth.role in item.allowed_roles]


def _go(page: ft.Page, route: str) -> None:
    if page.route != route:
        page.go(route)


def _open_drawer(page: ft.Page, drawer: ft.NavigationDrawer) -> None:
    """Assignation directe uniquement — seule méthode fiable observée sur
    cette build de Flet pour un NavigationDrawer."""
    page.drawer = drawer
    drawer.open = True
    page.update()


def _close_drawer(page: ft.Page, drawer: ft.NavigationDrawer) -> None:
    """Symétrique de _open_drawer, assignation directe uniquement."""
    drawer.open = False
    page.update()


def side_rail(page: ft.Page, auth: AuthState, unread_count: int = 0) -> ft.Control:
    items = _visible_items(auth)
    current = page.route

    def build_tile(item: NavItem) -> ft.Control:
        is_active = item.route == current

        content_row = ft.Row(
            [
                ft.Icon(item.icon, color=Colors.TEXT_ON_DARK if is_active else Colors.TEXT, size=20),
                ft.Text(item.label, color=Colors.TEXT_ON_DARK if is_active else Colors.TEXT, size=13, weight=ft.FontWeight.W_600 if is_active else ft.FontWeight.NORMAL),
            ],
            spacing=12,
        )

        if item.route == "/notifications" and unread_count > 0:
            content_row.controls.append(
                ft.Container(
                    content=ft.Text(str(unread_count), size=10, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
                    bgcolor=ft.Colors.RED_700,
                    border_radius=10,
                    padding=ft.Padding(left=6, top=2, right=6, bottom=2),
                )
            )

        return ft.Container(
            content=content_row,
            padding=ft.Padding(left=14, top=10, right=14, bottom=10),
            bgcolor=Colors.PRIMARY if is_active else None,
            border_radius=8,
            ink=True,
            on_click=lambda _, r=item.route: _go(page, r),
        )

    return ft.Container(
        content=ft.Column(
            [
                ft.Row([
                    ft.Icon(ft.Icons.PARK, color=Colors.PRIMARY, size=24),
                    ft.Text("Cimetière Connect", size=16, weight=ft.FontWeight.W_700, color=Colors.PRIMARY)
                ], spacing=8),
                ft.Container(height=12),
                ft.Column(
                    [build_tile(item) for item in items],
                    scroll=ft.ScrollMode.AUTO,
                    expand=True,
                    spacing=2,
                ),
                ft.Divider(height=1, color=Colors.BORDER),
                ft.Container(
                    content=ft.Row(
                        [ft.Icon(ft.Icons.LOGOUT, size=18, color=Colors.ERROR), ft.Text("Déconnexion", size=13, color=Colors.ERROR)],
                        spacing=8,
                    ),
                    padding=ft.Padding(left=14, top=10, right=14, bottom=10),
                    ink=True,
                    on_click=lambda _: (auth.logout(), page.go("/login")),
                ),
            ],
            spacing=4,
            expand=True,
        ),
        width=240,
        padding=16,
        bgcolor="#FFFFFF",
        border=ft.Border.only(right=ft.BorderSide(1, Colors.BORDER)),
    )


def build_app_bar(page: ft.Page, auth: AuthState, unread_count: int = 0) -> tuple[ft.AppBar, ft.NavigationDrawer]:
    """
    Retourne (appbar, drawer). Le drawer doit être attaché explicitement
    au paramètre drawer= de la ft.View par l'appelant (core/router.py) —
    page.drawer seul ne suffit pas sur cette build de Flet, c'est ce qui
    empêchait le tiroir de s'ouvrir malgré un _open_drawer() correct.
    """
    items = _visible_items(auth)

    drawer = ft.NavigationDrawer(
        controls=[
            ft.NavigationDrawerDestination(icon=item.icon, label=item.label) for item in items
        ],
    )

    def on_drawer_change(e: ft.ControlEvent) -> None:
        index = e.control.selected_index
        if index is not None and 0 <= index < len(items):
            _go(page, items[index].route)
            _close_drawer(page, drawer)

    drawer.on_change = on_drawer_change

    bell_icon = ft.Icons.NOTIFICATIONS_ACTIVE if unread_count > 0 else ft.Icons.NOTIFICATIONS

    def go_to_notifications(e):
        page.go("/notifications")

    bell_button = ft.Stack(
        controls=[
            ft.IconButton(icon=bell_icon, tooltip="Voir les notifications", on_click=go_to_notifications),
            ft.Container(
                content=ft.Text(str(unread_count), size=9, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
                bgcolor=ft.Colors.RED_700,
                border_radius=8,
                padding=ft.Padding(left=4, top=1, right=4, bottom=1),
                top=2,
                right=2,
            ) if unread_count > 0 else ft.Container(),
        ]
    )

    appbar = ft.AppBar(
        title=ft.Text("Cimetière Connect", weight=ft.FontWeight.W_700, color=Colors.PRIMARY),
        bgcolor="#FFFFFF",
        leading=ft.IconButton(ft.Icons.MENU, on_click=lambda _: _open_drawer(page, drawer)),
        actions=[
            bell_button,
            ft.IconButton(ft.Icons.LOGOUT, tooltip="Se déconnecter", on_click=lambda _: (auth.logout(), page.go("/login"))),
        ],
    )

    return appbar, drawer


def build_navigation(page: ft.Page, auth: AuthState) -> dict:
    unread_count = 0
    try:
        data = auth.api.get("/notifications/notifications/unread-count")
        if isinstance(data, dict):
            unread_count = data.get("non_lues", 0)
    except Exception:
        pass

    device = get_device_type(get_page_width(page))

    if device == "mobile":
        appbar, drawer = build_app_bar(page, auth, unread_count)
        return {"appbar": appbar, "rail": None, "drawer": drawer}
    return {"appbar": None, "rail": side_rail(page, auth, unread_count), "drawer": None}