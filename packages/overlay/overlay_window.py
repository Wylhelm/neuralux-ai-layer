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

        # Top controls (voice + speaker + session/history/ocr)
        controls_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        controls_box.set_halign(Gtk.Align.END)

        # Mic button
        self._recording = False
        self.mic_button = Gtk.Button(label="🎤")
        self.mic_button.set_tooltip_text("Record voice (/voice)")
        try:
            self.mic_button.connect("clicked", self._on_mic_clicked)
        except Exception:
            pass
        controls_box.append(self.mic_button)

        # Speaker button (TTS toggle)
        self._tts_enabled = False
        self.speaker_button = Gtk.Button(label="🔇")
        self.speaker_button.set_tooltip_text("Toggle auto TTS (/tts toggle)")
        try:
            self.speaker_button.connect("clicked", self._on_speaker_clicked)
        except Exception:
            pass
        controls_box.append(self.speaker_button)
        
        # New chat button
        self.new_chat_button = Gtk.Button(label="🆕")
        self.new_chat_button.set_tooltip_text("Start new conversation (/fresh)")
        try:
            self.new_chat_button.connect("clicked", lambda _b: self.on_command("/fresh"))
        except Exception:
            pass
        controls_box.append(self.new_chat_button)

        # History button
        self.history_button = Gtk.Button(label="🕘")
        self.history_button.set_tooltip_text("Show conversation history (/history)")
        try:
            self.history_button.connect("clicked", lambda _b: self.on_command("/history"))
        except Exception:
            pass
        controls_box.append(self.history_button)

        # OCR select region button
        self.ocr_select_button = Gtk.Button(label="🔲")
        self.ocr_select_button.set_tooltip_text("Select screen region for OCR (/ocr select)")
        try:
            self.ocr_select_button.connect("clicked", lambda _b: self.on_command("/ocr select"))
        except Exception:
            pass
        controls_box.append(self.ocr_select_button)

        # Refresh button
        self.refresh_button = Gtk.Button(label="↻")
        self.refresh_button.set_tooltip_text("Refresh suggestions (/refresh)")
        try:
            self.refresh_button.connect("clicked", lambda _b: self.on_command("/refresh"))
        except Exception:
            pass
        controls_box.append(self.refresh_button)

        main_box.append(controls_box)
        
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
        
        # Status bar at bottom with spinner
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        status_box.set_halign(Gtk.Align.CENTER)
        self.spinner = Gtk.Spinner()
        try:
            self.spinner.set_spinning(False)
        except Exception:
            pass
        status_box.append(self.spinner)
        self.status_label = Gtk.Label()
        self.status_label.set_markup("<span size='small' alpha='60%'>Press Esc to close</span>")
        status_box.append(self.status_label)
        status_box.set_margin_top(10)
        main_box.append(status_box)

        # Toast overlay (simple revealer at bottom)
        self.toast_revealer = Gtk.Revealer()
        self.toast_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_UP)
        self.toast_revealer.set_reveal_child(False)
        toast_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        toast_box.set_halign(Gtk.Align.CENTER)
        toast_box.get_style_context().add_class("toast")
        self.toast_label = Gtk.Label(label="")
        toast_box.append(self.toast_label)
        self.toast_revealer.set_child(toast_box)
        main_box.append(self.toast_revealer)
        
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

        /* Buttons: improve contrast on dark background */
        button {
            background: #43465a;
            color: #cdd6f4;
            border: 1px solid #565a73;
            border-radius: 8px;
            padding: 6px 12px;
        }
        button:hover {
            background: #50536a;
            border-color: #89b4fa;
        }
        button:focus {
            border-color: #89b4fa;
        }
        /* Approval buttons with explicit accent colors */
        .approve {
            background: #224034;
            color: #d9fbe5;
            border-color: #2ea043;
        }
        .approve:hover { background: #28503f; }
        .cancel {
            background: #4a2b2b;
            color: #f6d0d0;
            border-color: #d73a49;
        }
        .cancel:hover { background: #5a3131; }
        """
        css_provider.load_from_data(css)
        
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        # Extra CSS for toast
        try:
            extra = b"""
            .toast { background: #1f2937; color: #e5e7eb; border-radius: 8px; padding: 8px 14px; }
            """
            css_provider.load_from_data(css + extra)
        except Exception:
            pass

    def _on_mic_clicked(self, _button):
        """Start a single-turn voice capture via on_command."""
        try:
            # Optimistically set recording state in UI
            self.indicate_recording(True)
            self.on_command("/voice")
        except Exception:
            # Revert on failure
            try:
                self.indicate_recording(False)
            except Exception:
                pass

    def _on_speaker_clicked(self, _button):
        """Toggle auto TTS via on_command and update UI."""
        try:
            self.on_command("/tts toggle")
            # Actual state will be synced by handler; do local optimistic toggle
            self.set_tts_enabled(not getattr(self, "_tts_enabled", False))
        except Exception:
            pass
    
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
                elif action_type == "open":
                    # Queue an approval to open the file
                    path = payload.get("path", "")
                    if path:
                        self.on_command(f"/queue_open {path}")
                elif action_type == "overlay_command":
                    # Run a raw overlay command string (e.g., /copy, /summarize)
                    cmd = payload.get("command", "").strip()
                    if cmd:
                        self.on_command(cmd)
                elif action_type == "sequence":
                    # Run a sequence of commands in order (best-effort)
                    cmds = payload.get("commands") or []
                    try:
                        for c in cmds:
                            if isinstance(c, str) and c.strip():
                                self.on_command(c)
                    except Exception:
                        pass
                elif action_type == "ocr_action":
                    # Dispatch to run OCR via CLI backend
                    self.on_command("/ocr window")
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
            # Ensure we are on top and raised - CRITICAL for overlay behavior
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
            # X11: request ABOVE state from WM immediately
            try:
                self._ensure_above_x11()
            except Exception:
                pass
            # Aggressively re-raise and re-apply stacking hints multiple times
            # to work around window manager focus-stealing prevention
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
                # Apply at multiple intervals to catch window manager delays
                GLib.timeout_add(50, _reraises)
                GLib.timeout_add(100, _reraises)
                GLib.timeout_add(200, _reraises)
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

    def show_overlay(self):
        """Ensure the overlay is visible and focused."""
        if not self.is_visible():
            self.toggle_visibility()
        else:
            # Re-apply stacking when already visible
            try:
                self.set_keep_above(True)
                self.present()
                surface = self.get_surface()
                if surface is not None and hasattr(surface, "raise_"):
                    surface.raise_()
                self._ensure_above_x11()
            except Exception:
                pass
            # Re-raise after a short delay to ensure we're on top
            try:
                def _reraise_again():
                    try:
                        self.set_keep_above(True)
                        surf = self.get_surface()
                        if surf is not None and hasattr(surf, "raise_"):
                            surf.raise_()
                        self._ensure_above_x11()
                        self.present()
                    except Exception:
                        pass
                    return False
                GLib.timeout_add(50, _reraise_again)
            except Exception:
                pass

    def hide_overlay(self):
        """Hide the overlay window."""
        try:
            self.hide()
        except Exception:
            pass
    
    def set_tts_enabled(self, enabled: bool):
        """Update speaker toggle state (icon and tooltip)."""
        try:
            self._tts_enabled = bool(enabled)
            if self._tts_enabled:
                self.speaker_button.set_label("🔊")
                self.speaker_button.set_tooltip_text("Auto TTS: ON (click to disable)")
            else:
                self.speaker_button.set_label("🔇")
                self.speaker_button.set_tooltip_text("Auto TTS: OFF (click to enable)")
        except Exception:
            pass

    def indicate_recording(self, active: bool):
        """Indicate recording state on the mic button and status bar."""
        try:
            self._recording = bool(active)
            if self._recording:
                self.mic_button.set_label("⏺️")
                self.set_status("Listening...")
                self.mic_button.set_sensitive(False)
            else:
                self.mic_button.set_label("🎤")
                self.set_status("Ready")
                self.mic_button.set_sensitive(True)
        except Exception:
            pass

    def add_result(self, title: str, subtitle: str = "", payload: Optional[dict] = None):
        """Add a result to the list.
        Optionally attach a payload dict to make the row actionable.
        """
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
        
        if payload and isinstance(payload, dict):
            setattr(box, "payload", payload)
        
        row.set_child(box)
        self.results_list.append(row)

    def show_pending_action(self, title: str, summary: str = ""):
        """Show a pending action row with Approve/Cancel buttons."""
        # Insert a row with buttons
        row = Gtk.ListBoxRow()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        title_label = Gtk.Label()
        title_label.set_markup(f"<b>{title}</b>")
        title_label.set_halign(Gtk.Align.START)
        box.append(title_label)

        if summary:
            summary_label = Gtk.Label()
            summary_label.set_wrap(True)
            summary_label.set_xalign(0.0)
            summary_label.set_text(summary)
            summary_label.get_style_context().add_class("result-content")
            box.append(summary_label)

        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        approve = Gtk.Button(label="Approve")
        cancel = Gtk.Button(label="Cancel")
        try:
            approve.connect("clicked", lambda _b: self.on_command("/approve"))
            cancel.connect("clicked", lambda _b: self.on_command("/cancel"))
        except Exception:
            pass
        try:
            approve.get_style_context().add_class("approve")
            cancel.get_style_context().add_class("cancel")
        except Exception:
            pass
        buttons.append(approve)
        buttons.append(cancel)
        box.append(buttons)

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

    def add_buttons_row(self, title: str, buttons: list[tuple[str, str]]):
        """Add a row with a title and a horizontal list of clickable buttons.
        Each button is defined as (label, command_string) and will dispatch via on_command.
        """
        row = Gtk.ListBoxRow()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        title_label = Gtk.Label()
        title_label.set_markup(f"<b>{title}</b>")
        title_label.set_halign(Gtk.Align.START)
        box.append(title_label)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        for label, cmd in buttons:
            btn = Gtk.Button(label=label)
            try:
                btn.connect("clicked", lambda _b, c=cmd: self.on_command(c))
            except Exception:
                pass
            btn_box.append(btn)
        box.append(btn_box)

        row.set_child(box)
        self.results_list.append(row)
    
    def set_status(self, text: str):
        """Set status bar text."""
        suffix = f" • {self._active_app}" if self._active_app else ""
        self.status_label.set_markup(f"<span size='small' alpha='60%'>{text}{suffix}</span>")

    def begin_busy(self, text: str = "Working..."):
        """Show spinner and status text."""
        try:
            if hasattr(self.spinner, "start"):
                self.spinner.start()
        except Exception:
            pass
        self.set_status(text)

    def end_busy(self, text: str = "Ready"):
        """Hide spinner and set final status text."""
        try:
            if hasattr(self.spinner, "stop"):
                self.spinner.stop()
        except Exception:
            pass
        self.set_status(text)

    def show_toast(self, text: str, timeout_ms: int = 2500):
        try:
            self.toast_label.set_text(text)
            self.toast_revealer.set_reveal_child(True)
            def _hide():
                try:
                    self.toast_revealer.set_reveal_child(False)
                except Exception:
                    pass
                return False
            GLib.timeout_add(timeout_ms, _hide)
        except Exception:
            pass

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
        """Detect active window/app more reliably (X11 best-effort; safe fallback)."""
        try:
            import subprocess
            # Prefer xdotool + xprop when available
            cmd = "set -e; W=$(xdotool getactivewindow 2>/dev/null || true); if [ -n \"$W\" ]; then P=$(xprop -id $W _NET_WM_PID 2>/dev/null | awk -F' = ' '{print $2}'); if [ -n \"$P\" ]; then ps -p $P -o comm=; exit 0; fi; fi; echo -n"  # noqa: E501
            out = subprocess.check_output(["bash", "-lc", cmd], stderr=subprocess.DEVNULL, text=True)
            name = (out or "").strip()
            if name:
                return name
        except Exception:
            pass
        try:
            import subprocess
            # Fallback: parse wmctrl to match active window id
            cmd = (
                "set -e; W=$(xprop -root _NET_ACTIVE_WINDOW 2>/dev/null | awk -F'# ' '{print $2}' | sed 's/0x/0x/'); "
                "wmctrl -lp | awk -v wid=$W 'tolower($1)==tolower(wid){print $3; exit}'"
            )
            pid = subprocess.check_output(["bash", "-lc", cmd], stderr=subprocess.DEVNULL, text=True).strip()
            if pid.isdigit():
                pname = subprocess.check_output(["bash", "-lc", f"ps -p {pid} -o comm="], stderr=subprocess.DEVNULL, text=True).strip()
                if pname:
                    return pname
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
        NET_WM_STATE_FOCUSED = d.intern_atom('_NET_WM_STATE_FOCUSED')
        NET_WM_WINDOW_TYPE = d.intern_atom('_NET_WM_WINDOW_TYPE')
        NET_WM_WINDOW_TYPE_DIALOG = d.intern_atom('_NET_WM_WINDOW_TYPE_DIALOG')
        NET_WM_WINDOW_TYPE_UTILITY = d.intern_atom('_NET_WM_WINDOW_TYPE_UTILITY')

        # Set window type to utility+dialog (commonly floats above normal windows)
        try:
            win.change_property(NET_WM_WINDOW_TYPE, Xatom.ATOM, 32, 
                              [NET_WM_WINDOW_TYPE_UTILITY, NET_WM_WINDOW_TYPE_DIALOG])
        except Exception:
            pass

        # Send client message to add ABOVE state (1 = _NET_WM_STATE_ADD)
        try:
            ev = protocol.event.ClientMessage(
                window=win,
                client_type=NET_WM_STATE,
                data=(32, [1, NET_WM_STATE_ABOVE, 0, 1, 0])  # source=1 means application
            )
            mask = X.SubstructureRedirectMask | X.SubstructureNotifyMask
            root.send_event(ev, event_mask=mask)
            d.flush()
        except Exception:
            pass
        
        # Also try to set the state property directly as a fallback
        try:
            win.change_property(NET_WM_STATE, Xatom.ATOM, 32, [NET_WM_STATE_ABOVE])
            d.flush()
        except Exception:
            pass

    # Dialogs -------------------------------------------------------------
    def show_about_dialog(self):
        """Show a native About dialog if available, otherwise a simple window."""
        try:
            # Try Gtk.AboutDialog (GTK4)
            if hasattr(Gtk, "AboutDialog"):
                d = Gtk.AboutDialog()
                d.set_program_name("Neuralux")
                try:
                    import importlib
                    ver = importlib.import_module("overlay").__version__  # type: ignore
                except Exception:
                    ver = "0.1.0"
                d.set_version(ver)
                # Logo
                try:
                    import os as _os
                    from gi.repository import Gio, Gdk  # type: ignore
                    logo_path = str(__import__("pathlib").Path(__file__).parent / "assets" / "neuralux-tray.svg")
                    if _os.path.exists(logo_path):
                        try:
                            # Prefer native GTK4 paintable via Gdk.Texture
                            tex = Gdk.Texture.new_from_file(Gio.File.new_for_path(logo_path))
                            d.set_logo(tex)
                        except Exception:
                            # Fallback to pixbuf → texture
                            from gi.repository import GdkPixbuf  # type: ignore
                            pb = GdkPixbuf.Pixbuf.new_from_file_at_size(logo_path, 196, 196)
                            try:
                                tex2 = Gdk.Texture.new_for_pixbuf(pb)
                                d.set_logo(tex2)
                            except Exception:
                                pass
                except Exception:
                    pass
                d.set_comments("Neuralux AI Layer – Desktop assistant overlay")
                d.set_modal(True)
                d.set_transient_for(self)
                d.show()
                return
        except Exception:
            pass
        # Fallback simple window
        try:
            w = Gtk.Window(title=f"About {self.config.app_name}")
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            box.set_margin_top(16)
            box.set_margin_bottom(16)
            box.set_margin_start(16)
            box.set_margin_end(16)
            lab = Gtk.Label(label=f"{self.config.app_name}\nVersion 0.1.0")
            lab.set_halign(Gtk.Align.CENTER)
            box.append(lab)
            w.set_child(box)
            w.set_transient_for(self)
            w.present()
        except Exception:
            pass

    def show_settings_window(self):
        """Show a settings window bound to persisted values and using overlay commands to apply."""
        try:
            from neuralux.memory import SessionStore  # type: ignore
            from neuralux.config import NeuraluxConfig  # type: ignore
            cfg = NeuraluxConfig()
            store = SessionStore(cfg)
            current = store.load_settings(cfg.settings_path())
        except Exception:
            current = {}

        llm_default = current.get("llm_model", "llama-3.2-3b-instruct-q4_k_m.gguf")
        stt_default = current.get("stt_model", "medium")

        w = Gtk.Window(title="Settings")
        w.set_transient_for(self)
        w.set_default_size(480, 280)
        vb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vb.set_margin_top(12)
        vb.set_margin_bottom(12)
        vb.set_margin_start(12)
        vb.set_margin_end(12)

        # LLM model
        llm_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        llm_row.append(Gtk.Label(label="LLM model file:"))
        llm_entry = Gtk.Entry()
        llm_entry.set_text(llm_default)
        llm_row.append(llm_entry)
        vb.append(llm_row)

        # Quick model family selection
        fam_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        fam_row.append(Gtk.Label(label="Quick select:"))
        btn_llama = Gtk.Button(label="Llama 3B")
        btn_mistral = Gtk.Button(label="Mistral 7B")
        try:
            btn_llama.connect("clicked", lambda _b: llm_entry.set_text("llama-3.2-3b-instruct-q4_k_m.gguf"))
            btn_mistral.connect("clicked", lambda _b: llm_entry.set_text("mistral-7b-instruct-q4_k_m.gguf"))
        except Exception:
            pass
        fam_row.append(btn_llama)
        fam_row.append(btn_mistral)
        vb.append(fam_row)

        # Download Mistral helper
        dl_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        dl_btn = Gtk.Button(label="Download Mistral 7B Q4_K_M")
        dl_note = Gtk.Label(label="(downloads to models/; size ~4GB)")
        dl_row.append(dl_btn)
        dl_row.append(dl_note)
        vb.append(dl_row)

        # STT model
        stt_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        stt_row.append(Gtk.Label(label="STT model:"))
        from gi.repository import Gtk as _Gtk  # keep namespace
        stt_combo = _Gtk.ComboBoxText()
        for name in ["tiny", "base", "small", "medium", "large"]:
            stt_combo.append_text(name)
        try:
            stt_combo.set_active(["tiny","base","small","medium","large"].index(stt_default) if stt_default in ["tiny","base","small","medium","large"] else 3)
        except Exception:
            pass
        stt_row.append(stt_combo)
        vb.append(stt_row)

        # Status label
        info = Gtk.Label(label="")
        vb.append(info)

        # Buttons
        btns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        apply_btn = Gtk.Button(label="Apply")
        save_btn = Gtk.Button(label="Save Defaults")
        close_btn = Gtk.Button(label="Close")
        btns.append(apply_btn)
        btns.append(save_btn)
        btns.append(close_btn)
        vb.append(btns)

        def _apply(_b):
            try:
                self.begin_busy("Applying settings…")
            except Exception:
                pass
            # Apply via overlay commands so existing logic triggers service calls
            try:
                self.on_command(f"/set llm.model {llm_entry.get_text().strip()}")
                sel = stt_combo.get_active_text()
                if sel:
                    self.on_command(f"/set stt.model {sel}")
                info.set_text("Applied. Models will reload if required.")
            except Exception:
                info.set_text("Failed to apply.")
            finally:
                try:
                    self.end_busy("Ready")
                except Exception:
                    pass

        def _save(_b):
            try:
                self.begin_busy("Saving settings…")
            except Exception:
                pass
            try:
                self.on_command("/settings.save")
                info.set_text("Saved defaults.")
                self.show_toast("Settings saved")
            except Exception:
                info.set_text("Failed to save.")
            finally:
                try:
                    self.end_busy("Ready")
                except Exception:
                    pass

        def _close(_b):
            try:
                w.close()
            except Exception:
                pass

        try:
            apply_btn.connect("clicked", _apply)
            save_btn.connect("clicked", _save)
            close_btn.connect("clicked", _close)
        except Exception:
            pass

        # Background download logic
        def _download_mistral(_b):
            try:
                self.begin_busy("Downloading Mistral 7B…")
            except Exception:
                pass
            import threading, os
            from pathlib import Path as _P
            def _worker():
                url = "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
                # Target path in repo models/
                try:
                    base = (_P(__file__).parent.parent.parent / "models").resolve()
                except Exception:
                    base = _P.home() / "models"
                base.mkdir(parents=True, exist_ok=True)
                target = base / "mistral-7b-instruct-q4_k_m.gguf"
                try:
                    import httpx
                    with httpx.stream("GET", url, follow_redirects=True, timeout=None) as r:
                        r.raise_for_status()
                        total = int(r.headers.get("content-length", "0")) or None
                        downloaded = 0
                        with open(target, "wb") as f:
                            for chunk in r.iter_bytes(chunk_size=1_048_576):
                                if chunk:
                                    f.write(chunk)
                                    downloaded += len(chunk)
                                    if total:
                                        pct = int(downloaded * 100 / total)
                                        GLib.idle_add(lambda p=pct: self.set_status(f"Downloading Mistral… {p}%"))
                    GLib.idle_add(lambda: (llm_entry.set_text(target.name), self.show_toast("Mistral downloaded"), self.end_busy("Ready")))
                except Exception as e:
                    GLib.idle_add(lambda: (self.end_busy("Ready"), self.show_toast(f"Download failed: {e}")))
            threading.Thread(target=_worker, daemon=True).start()

        try:
            dl_btn.connect("clicked", _download_mistral)
        except Exception:
            pass

        w.set_child(vb)
        try:
            w.present()
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

