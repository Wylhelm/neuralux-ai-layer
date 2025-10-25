"""System tray integration for the overlay using AyatanaAppIndicator.

This module is optional and degrades gracefully if the required
GTK/GIR bindings are not available on the system.
"""

from __future__ import annotations

from typing import Callable, Optional


class OverlayTray:
    """Create a tray icon with a small menu to control the overlay."""

    def __init__(self, on_toggle: Callable[[], None], on_quit: Callable[[], None], icon_name: str = "utilities-terminal", app_name: str = "Neuralux"):
        self.on_toggle = on_toggle
        self.on_quit = on_quit
        self.icon_name = icon_name
        self.app_name = app_name

        # Try to import GI components; if not available, no-op
        try:
            import gi  # type: ignore
            gi.require_version("Gtk", "4.0")
            gi.require_version("Gdk", "4.0")
            # Ayatana namespace first, then fallback to AppIndicator3
            try:
                gi.require_version("AyatanaAppIndicator3", "0.1")
                from gi.repository import AyatanaAppIndicator3 as AppIndicator3  # type: ignore
            except Exception:
                gi.require_version("AppIndicator3", "0.1")
                from gi.repository import AppIndicator3  # type: ignore
            from gi.repository import Gtk, GLib  # type: ignore
        except Exception:
            # Missing dependencies; silently disable tray
            self._enabled = False
            return

        self._enabled = True
        self._Gtk = Gtk
        self._GLib = GLib
        self._AppIndicator3 = AppIndicator3

        self._indicator: Optional[object] = None
        self._menu: Optional[Gtk.Menu] = None  # type: ignore

        self._build_indicator()

    @property
    def enabled(self) -> bool:
        return getattr(self, "_enabled", False)

    def _build_indicator(self) -> None:
        AppIndicator3 = self._AppIndicator3
        Gtk = self._Gtk

        try:
            self._indicator = AppIndicator3.Indicator.new(
                self.app_name.lower().replace(" ", "-") + "-overlay",
                self.icon_name,
                AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
            )
            # ACTIVE shows the icon, PASSIVE hides it
            self._indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

            # Build the menu
            menu = Gtk.Menu()

            # Toggle item
            toggle_item = Gtk.MenuItem.new_with_label("Toggle Overlay")
            toggle_item.connect("activate", self._on_toggle_activate)
            menu.append(toggle_item)

            # Separator
            menu.append(Gtk.SeparatorMenuItem.new())

            # Quit item
            quit_item = Gtk.MenuItem.new_with_label("Quit")
            quit_item.connect("activate", self._on_quit_activate)
            menu.append(quit_item)

            menu.show()
            self._indicator.set_menu(menu)
            self._menu = menu
        except Exception:
            # If anything fails, disable tray at runtime
            self._enabled = False

    # Signal handlers -----------------------------------------------------
    def _on_toggle_activate(self, _item) -> None:
        try:
            # Ensure UI operations occur on the GTK main loop
            self._GLib.idle_add(lambda: (self.on_toggle(), False))
        except Exception:
            pass

    def _on_quit_activate(self, _item) -> None:
        try:
            self._GLib.idle_add(lambda: (self.on_quit(), False))
        except Exception:
            pass


