"""GTK4-based overlay window."""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')

from gi.repository import Gtk, Gdk, GLib
from typing import Callable, Optional
import structlog

from .config import OverlayConfig
from .search import suggest, Suggestion

logger = structlog.get_logger(__name__)


class OverlayWindow(Gtk.ApplicationWindow):
    """Main overlay window."""
    
    def __init__(self, app, config: OverlayConfig, on_command: Callable[[str], None]):
        """Initialize the overlay window."""
        super().__init__(application=app)
        
        self.config = config
        self.on_command = on_command
        self._active_app: Optional[str] = None
        
        # Window properties
        self.set_title("Neuralux")
        self.set_default_size(config.window_width, config.window_height)
        self.set_resizable(False)
        
        # Make it a dialog-like window (always on top)
        self.set_decorated(False)  # No title bar
        try:
            self.set_keep_above(True)
        except Exception:
            pass
        try:
            # Ensure the window can take focus when shown
            self.set_focusable(True)
        except Exception:
            pass

        # Fullscreen option
        if config.fullscreen:
            try:
                self.maximize()
            except Exception:
                pass
        
        # Setup UI
        self._setup_ui()
        
        # Setup CSS for styling
        self._setup_styling()
        
        # Connect signals
        self.connect("close-request", self._on_close_request)
        # Key handling (Escape to close, arrow navigation potential)
        try:
            key_controller = Gtk.EventControllerKey()
            key_controller.connect("key-pressed", self._on_key_pressed)
            self.add_controller(key_controller)
        except Exception:
            pass
        
        logger.info("Overlay window created")
    
    def _setup_ui(self):
        """Setup the user interface."""
        # Outer container to center inner content
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        outer.set_hexpand(True)
        outer.set_vexpand(True)
        outer.set_halign(Gtk.Align.CENTER)
        outer.set_valign(Gtk.Align.CENTER)

        # Inner content box (fixed width to keep centered card look)
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        main_box.set_size_request(self.config.window_width, self.config.window_height)
        main_box.set_margin_top(20)
        main_box.set_margin_bottom(20)
        main_box.set_margin_start(20)
        main_box.set_margin_end(20)
        
        # Search entry
        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text("Type a command or question...")
        self.search_entry.set_size_request(-1, 50)
        self.search_entry.connect("activate", self._on_entry_activate)
        self.search_entry.connect("changed", self._on_entry_changed)
        main_box.append(self.search_entry)
        
        # Results list (scrollable)
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_size_request(-1, 400)
        scrolled.set_vexpand(True)
        scrolled.set_margin_top(10)
        scrolled.get_style_context().add_class("results-scroller")
        
        # List box for results
        self.results_list = Gtk.ListBox()
        self.results_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.results_list.connect("row-activated", self._on_result_activated)
        scrolled.set_child(self.results_list)
        
        main_box.append(scrolled)
        
        # Status bar at bottom
        self.status_label = Gtk.Label()
        self.status_label.set_markup("<span size='small' alpha='60%'>Press Esc to close</span>")
        self.status_label.set_margin_top(10)
        self.status_label.set_halign(Gtk.Align.CENTER)
        main_box.append(self.status_label)
        
        outer.append(main_box)
        self.set_child(outer)
        GLib.timeout_add_seconds(5, self._refresh_context)
    
    def _setup_styling(self):
        """Setup CSS styling."""
        css_provider = Gtk.CssProvider()
        css = b"""
        window {
            background: alpha(#1e1e2e, 0.95);
            border-radius: 12px;
        }
        
        entry {
            background: #313244;
            color: #cdd6f4;
            border: 2px solid #45475a;
            border-radius: 8px;
            padding: 12px;
            font-size: 16px;
        }
        
        entry:focus {
            border-color: #89b4fa;
        }
        
        .results-scroller,
        .results-scroller > viewport {
            background: transparent;
        }

        list {
            background: transparent;
        }
        
        list row {
            background: #262737; /* darker card */
            color: #e6edf3;
            border-radius: 8px;
            margin: 6px 0;
            padding: 12px;
        }
        
        list row:selected {
            background: #3a3c52;
        }
        
        list row:hover {
            background: #32344a;
        }
        
        label {
            color: #cdd6f4;
        }
        
        .result-title {
            font-weight: bold;
        }
        
        .result-content {
            font-family: monospace;
            color: #e6edf3; /* brighter for readability */
            font-size: 14px;
        }
        """
        css_provider.load_from_data(css)
        
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
    
    def _on_entry_activate(self, entry):
        """Handle Enter key in search entry."""
        text = entry.get_text().strip()
        if text:
            self.on_command(text)
            entry.set_text("")
    
    def _on_entry_changed(self, entry):
        """Handle text changes in search entry."""
        text = entry.get_text()
        logger.debug("Search text changed", text=text)
        self.clear_results()
        for s in suggest(text, max_results=self.config.max_results, threshold=self.config.fuzzy_threshold):
            self._add_suggestion_row(s)
    
    def _on_result_activated(self, list_box, row):
        """Handle selection of a result."""
        idx = row.get_index()
        child = row.get_child()
        payload = getattr(child, "payload", None)
        logger.debug("Result activated", row_index=idx)
        if payload and isinstance(payload, dict):
            # Dispatch to command handler via status bar prompt
            try:
                action_type = payload.get("type")
                if action_type == "llm_query":
                    self.on_command(payload.get("query", ""))
                elif action_type == "file_search":
                    # Prefix to drive filesystem search via CLI backend
                    self.on_command(f"/search {payload.get('query', '')}")
                elif action_type == "health_summary":
                    # Ask health via CLI backend
                    self.on_command("/health")
                else:
                    self.on_command(str(payload))
            except Exception:
                pass
    
    def _on_close_request(self, window):
        """Handle window close request."""
        self.hide()
        return True  # Prevent destruction

    def _on_key_pressed(self, controller, keyval, keycode, state):
        """Handle global key presses for the window."""
        try:
            if keyval == Gdk.KEY_Escape:
                self.hide()
                return True
        except Exception:
            pass
        return False
    
    def toggle_visibility(self):
        """Toggle window visibility."""
        if self.is_visible():
            self.hide()
        else:
            self.show()
            self.present()
            # Ensure we are on top and raised
            try:
                self.set_keep_above(True)
            except Exception:
                pass
            try:
                surface = self.get_surface()
                if surface is not None and hasattr(surface, "raise_"):
                    surface.raise_()
            except Exception:
                pass
            # X11: request ABOVE state from WM
            try:
                self._ensure_above_x11()
            except Exception:
                pass
            # Make modal briefly to defeat focus-stealing prevention on some WMs
            try:
                self.set_modal(True)
            except Exception:
                pass
            # Re-raise shortly after mapping to ensure we float above
            try:
                def _reraises():
                    try:
                        self.set_keep_above(True)
                        surf = self.get_surface()
                        if surf is not None and hasattr(surf, "raise_"):
                            surf.raise_()
                        self._ensure_above_x11()
                        self.present()
                        self.search_entry.grab_focus()
                    except Exception:
                        pass
                    return False
                GLib.timeout_add(100, _reraises)
            except Exception:
                pass
            # Position window at screen center (best-effort, primarily X11)
            try:
                display = Gdk.Display.get_default()
                monitor = display.get_primary_monitor()
                geometry = monitor.get_geometry()
                width = self.get_width()
                height = self.get_height()
                x = geometry.x + (geometry.width - width) // 2
                y = geometry.y + (geometry.height - height) // 2
                self.move(x, y)
            except Exception:
                pass
            self.search_entry.grab_focus()
    
    def add_result(self, title: str, subtitle: str = ""):
        """Add a result to the list."""
        row = Gtk.ListBoxRow()
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        
        title_label = Gtk.Label()
        title_label.set_markup(f"<b>{title}</b>")
        title_label.set_halign(Gtk.Align.START)
        title_label.get_style_context().add_class("result-title")
        box.append(title_label)
        
        if subtitle:
            # Use a selectable, wrapping label for content
            subtitle_label = Gtk.Label()
            subtitle_label.set_selectable(True)
            subtitle_label.set_wrap(True)
            subtitle_label.set_xalign(0.0)
            subtitle_label.set_text(subtitle)
            subtitle_label.get_style_context().add_class("result-content")
            box.append(subtitle_label)
        
        row.set_child(box)
        self.results_list.append(row)

    def _add_suggestion_row(self, s: Suggestion):
        row = Gtk.ListBoxRow()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)

        title_label = Gtk.Label()
        title_label.set_markup(f"<b>{Gtk.utils.escape(s.title)}</b>" if hasattr(Gtk, "utils") else f"<b>{s.title}</b>")
        title_label.set_halign(Gtk.Align.START)
        title_label.get_style_context().add_class("result-title")
        box.append(title_label)

        if s.subtitle:
            subtitle_label = Gtk.Label()
            subtitle_label.set_selectable(False)
            subtitle_label.set_wrap(True)
            subtitle_label.set_xalign(0.0)
            subtitle_label.set_text(s.subtitle)
            subtitle_label.get_style_context().add_class("result-content")
            box.append(subtitle_label)

        # Attach payload to the box for retrieval on activation
        setattr(box, "payload", s.payload)
        row.set_child(box)
        self.results_list.append(row)
    
    def clear_results(self):
        """Clear all results."""
        while True:
            row = self.results_list.get_row_at_index(0)
            if row is None:
                break
            self.results_list.remove(row)
    
    def set_status(self, text: str):
        """Set status bar text."""
        suffix = f" • {self._active_app}" if self._active_app else ""
        self.status_label.set_markup(f"<span size='small' alpha='60%'>{text}{suffix}</span>")

    def _refresh_context(self):
        """Update active application name (best-effort)."""
        try:
            app_name = self._detect_active_app()
            if app_name:
                self._active_app = app_name
                # Update status subtly without overriding main message when idle
                self.set_status("Ready")
        except Exception:
            pass
        return True

    def _detect_active_app(self) -> Optional[str]:
        """Detect active window/app (X11 best-effort)."""
        try:
            import subprocess
            # Try wmctrl (commonly available on X11)
            out = subprocess.check_output(["bash", "-lc", "wmctrl -lp | awk 'NR==1{print $3}'"], stderr=subprocess.DEVNULL, text=True)
            pid = out.strip()
            if pid.isdigit():
                cmd = subprocess.check_output(["bash", "-lc", f"ps -p {pid} -o comm="], stderr=subprocess.DEVNULL, text=True).strip()
                return cmd
        except Exception:
            pass
        return None

    def _ensure_above_x11(self):
        """Ask the X11 WM via EWMH to keep this window above."""
        try:
            from gi.repository import GdkX11  # type: ignore
            from Xlib import X, Xatom, display, protocol  # type: ignore
        except Exception:
            return

        surface = self.get_surface()
        if surface is None:
            return
        try:
            xid = GdkX11.X11Surface.get_xid(surface)
        except Exception:
            return

        d = display.Display()
        root = d.screen().root
        win = d.create_resource_object('window', xid)

        NET_WM_STATE = d.intern_atom('_NET_WM_STATE')
        NET_WM_STATE_ABOVE = d.intern_atom('_NET_WM_STATE_ABOVE')
        NET_WM_WINDOW_TYPE = d.intern_atom('_NET_WM_WINDOW_TYPE')
        NET_WM_WINDOW_TYPE_DIALOG = d.intern_atom('_NET_WM_WINDOW_TYPE_DIALOG')

        # Set a dialog type (commonly floats above normal windows)
        try:
            win.change_property(NET_WM_WINDOW_TYPE, Xatom.ATOM, 32, [NET_WM_WINDOW_TYPE_DIALOG])
        except Exception:
            pass

        # Send client message to add ABOVE state (1 = _NET_WM_STATE_ADD)
        try:
            ev = protocol.event.ClientMessage(
                window=win,
                client_type=NET_WM_STATE,
                data=(32, [1, NET_WM_STATE_ABOVE, 0, 0, 0])
            )
            mask = X.SubstructureRedirectMask | X.SubstructureNotifyMask
            root.send_event(ev, event_mask=mask)
            d.flush()
        except Exception:
            pass


class OverlayApplication(Gtk.Application):
    """GTK Application for the overlay."""
    
    def __init__(self, config: OverlayConfig, on_command: Callable[[str], None]):
        """Initialize the application."""
        super().__init__(application_id="com.neuralux.overlay")
        
        self.config = config
        self.on_command = on_command
        self.window = None
    
    def do_activate(self):
        """Activate the application."""
        if not self.window:
            self.window = OverlayWindow(self, self.config, self.on_command)
        
        self.window.present()

