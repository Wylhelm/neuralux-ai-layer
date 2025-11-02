"""System tray integration for the overlay using AyatanaAppIndicator.

This module is optional and degrades gracefully if the required
GTK/GIR bindings are not available on the system.
"""

from __future__ import annotations

from typing import Callable, Optional


class OverlayTray:
    """Create a tray icon with a small menu to control the overlay."""

    def __init__(self, on_toggle: Callable[[], None], on_quit: Callable[[], None], icon_name: str = "utilities-terminal", app_name: str = "Neuralux", on_about: Optional[Callable[[], None]] = None, on_settings: Optional[Callable[[], None]] = None):
        self.on_toggle = on_toggle
        self.on_quit = on_quit
        self.icon_name = icon_name
        self.app_name = app_name
        self.on_about = on_about or (lambda: None)
        self.on_settings = on_settings or (lambda: None)

        # Try to import GI components; if not available, no-op
        try:
            import gi  # type: ignore
            gi.require_version("Gtk", "4.0")
            gi.require_version("Gdk", "4.0")
            try:
                gi.require_version("AyatanaAppIndicator3", "0.1")
                from gi.repository import AyatanaAppIndicator3 as AppIndicator3  # type: ignore
            except (ValueError, ImportError):
                gi.require_version("AppIndicator3", "0.1")
                from gi.repository import AppIndicator3  # type: ignore
            from gi.repository import Gtk, GLib, Gio  # type: ignore
        except (ValueError, ImportError):
            self._enabled = False
            return

        self._enabled = True
        self._Gtk = Gtk
        self._GLib = GLib
        self._Gio = Gio
        self._AppIndicator3 = AppIndicator3
        self._indicator: Optional[object] = None
        self._menu: Optional[Gio.Menu] = None
        self._build_indicator()

    @property
    def enabled(self) -> bool:
        return getattr(self, "_enabled", False)

    def _build_indicator(self) -> None:
        """Build the indicator and menu using modern GMenu."""
        AppIndicator3 = self._AppIndicator3
        Gio = self._Gio

        try:
            self._indicator = AppIndicator3.Indicator.new(
                self.app_name.lower().replace(" ", "-") + "-overlay",
                self.icon_name,
                AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
            )
            self._indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

            # Build the menu model
            menu = Gio.Menu.new()
            
            # Create actions and connect them to callbacks
            # Note: Actions need to be added to the Gtk.Application instance
            # This tray implementation will create the menu, but the actions
            # must be connected by the main application that owns the lifecycle.
            # We will use a simple workaround here by directly calling callbacks
            # from menu item activations, which is less ideal but avoids
            # major refactoring of the application structure.
            
            # For this to work, we need to connect to the application's GMenu signals
            # A better approach is to pass the Gtk.Application object and add actions to it.
            # Given the constraints, we will stick to the Gtk.Menu approach but fix the API usage.
            # The root issue is that AppIndicator expects a Gtk.Menu, which is GTK3.
            # The AppIndicator/Ayatana library is based on GTK3's Gtk.Menu, which is not
            # available in a pure GTK4 application. This prevents us from creating a menu.
            # As a functional alternative, we will make the tray icon toggle the overlay
            # window on both left-click (primary) and right-click (secondary).
            
            # A proper fix would require a different tray icon library compatible with GTK4
            # or running the tray icon in a separate GTK3 process.

            # Connect the toggle function to the indicator's activation signals.
            self._indicator.connect("primary-activate", self._on_toggle_activate)
            self._indicator.connect("secondary-activate", self._on_toggle_activate)


        except Exception:
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

    def _on_about_activate(self, _item) -> None:
        try:
            self._GLib.idle_add(lambda: (self.on_about(), False))
        except Exception:
            pass

    def _on_settings_activate(self, _item) -> None:
        try:
            self._GLib.idle_add(lambda: (self.on_settings(), False))
        except Exception:
            pass
