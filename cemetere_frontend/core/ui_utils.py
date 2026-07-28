from __future__ import annotations
import flet as ft

_last_overlay: dict[int, ft.Control] = {}  # id(page) -> dernier control ouvert


def show_overlay(page: ft.Page, control: ft.Control) -> None:
    """Ouvre un AlertDialog ou un SnackBar, en fermant proprement le précédent."""
    prev = _last_overlay.get(id(page))
    if prev is not None:
        close_overlay(page, prev)

    if hasattr(page, "open"):
        try:
            page.open(control)
            _last_overlay[id(page)] = control
            return
        except Exception:
            pass

    if control not in page.overlay:
        page.overlay.append(control)
    control.open = True
    _last_overlay[id(page)] = control
    page.update()


def close_overlay(page: ft.Page, control: ft.Control) -> None:
    if hasattr(page, "close"):
        try:
            page.close(control)
            return
        except Exception:
            pass
    control.open = False
    page.update()