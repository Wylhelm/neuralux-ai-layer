"""External tray helper for the Neuralux overlay (Gtk3 + AppIndicator3).

This helper is launched as a separate process to avoid Gtk4/AppIndicator
compatibility issues. It communicates with the overlay via NATS subjects:

- ui.overlay.toggle -> request the overlay to toggle visibility
- ui.overlay.quit   -> request the overlay to quit

Usage:
  python -m overlay.tray_helper
"""

from __future__ import annotations

import os
import sys
import asyncio
from typing import Optional


def _get_nats_url() -> str:
    return os.environ.get("NEURALUX_NATS_URL", os.environ.get("NATS_URL", "nats://localhost:4222"))


def _get_app_name() -> str:
    return os.environ.get("NEURALUX_APP_NAME", os.environ.get("OVERLAY_APP_NAME", "Neuralux"))


def _get_tray_icon() -> str:
    return os.environ.get("NEURALUX_TRAY_ICON", os.environ.get("OVERLAY_TRAY_ICON", "auto"))


async def _publish(subject: str) -> None:
    try:
        import nats  # type: ignore
    except Exception:
        return
    try:
        nc = await nats.connect(servers=[_get_nats_url()])
        await nc.publish(subject, b"{}")
        await nc.drain()
    except Exception:
        pass


def _publish_sync(subject: str) -> None:
    try:
        asyncio.run(_publish(subject))
    except Exception:
        pass


def main() -> int:
    try:
        import gi  # type: ignore
        gi.require_version("Gtk", "3.0")
        try:
            gi.require_version("AyatanaAppIndicator3", "0.1")
            from gi.repository import AyatanaAppIndicator3 as AppIndicator3  # type: ignore
        except Exception:
            gi.require_version("AppIndicator3", "0.1")
            from gi.repository import AppIndicator3  # type: ignore
        from gi.repository import Gtk  # type: ignore
    except Exception:
        # Missing GI/AppIndicator; indicate failure
        sys.stderr.write("Tray helper: GI/AppIndicator not available\n")
        return 1

    app_name = _get_app_name()
    icon = _get_tray_icon()
    if icon == "auto":
        # Try to use bundled icon if available; fallback to a generic
        default_icon_path = os.path.join(os.path.dirname(__file__), "assets", "neuralux-tray.svg")
        icon = default_icon_path if os.path.exists(default_icon_path) else "utilities-terminal"

    indicator = AppIndicator3.Indicator.new(
        app_name.lower().replace(" ", "-") + "-overlay",
        icon,
        AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
    )
    indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

    menu = Gtk.Menu()

    toggle_item = Gtk.MenuItem.new_with_label("Toggle Overlay")
    toggle_item.connect("activate", lambda _i: _publish_sync("ui.overlay.toggle"))
    menu.append(toggle_item)

    # Settings
    settings_item = Gtk.MenuItem.new_with_label("Settings")
    settings_item.connect("activate", lambda _i: _publish_sync("ui.overlay.settings"))
    menu.append(settings_item)

    # Quit above About
    quit_item = Gtk.MenuItem.new_with_label("Quit Overlay")
    def _quit(_i):
        _publish_sync("ui.overlay.quit")
        Gtk.main_quit()
    quit_item.connect("activate", _quit)
    menu.append(quit_item)

    # About at bottom
    about_item = Gtk.MenuItem.new_with_label("About Neuralux")
    about_item.connect("activate", lambda _i: _publish_sync("ui.overlay.about"))
    menu.append(about_item)

    menu.show_all()
    indicator.set_menu(menu)

    Gtk.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


