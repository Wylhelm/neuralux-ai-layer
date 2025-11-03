"""GTK4-based overlay window."""

import asyncio
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")

from gi.repository import Gtk, Gdk, GLib
from typing import Callable, Optional, List
import structlog

from .config import OverlayConfig
from .search import suggest, Suggestion
from .voice_handler import VoiceHandler
from .dialogs import AboutDialog, SettingsDialog
from .conversation import (
    OverlayConversationHandler,
    ConversationHistoryWidget,
    ActionApprovalDialog,
)

logger = structlog.get_logger(__name__)


class OverlayWindow(Gtk.ApplicationWindow):
    """Main overlay window."""

    def __init__(
        self,
        app,
        config: OverlayConfig,
        on_command: Callable[[str], None],
        message_bus=None,
    ):
        """Initialize the overlay window."""
        super().__init__(application=app)

        self.config = config
        self.on_command = on_command
        self._active_app: Optional[str] = None
        self._message_bus = message_bus

        # Voice handler for capture and TTS
        self.voice_handler = VoiceHandler(config, message_bus)

        # Conversation handler (initialized later if message_bus available)
        self.conversation_handler: Optional[OverlayConversationHandler] = None
        self._conversation_mode_enabled = True
        self._pending_approval_dialog = None
        self._pending_approval_widget = None
        self._pending_approval_handlers = (
            None  # {"approve": callable, "cancel": callable}
        )

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

    # ============================================================
    # INITIALIZATION & SETUP
    # ============================================================

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

        # Drag handle (title bar area)
        drag_handle = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        drag_handle.set_size_request(-1, 30)
        drag_handle.set_halign(Gtk.Align.FILL)
        drag_handle_label = Gtk.Label(label="≡ Neuralux ≡")
        drag_handle_label.set_halign(Gtk.Align.CENTER)
        drag_handle_label.get_style_context().add_class("drag-handle")
        drag_handle.append(drag_handle_label)
        main_box.append(drag_handle)

        # Store drag handle for controller
        self._drag_handle = drag_handle

        # Top controls (voice + speaker + session/history/ocr)
        controls_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        controls_box.set_halign(Gtk.Align.END)

        # Mic button
        self._recording = False
        self.mic_button = Gtk.Button(label="🎤")
        self.mic_button.set_tooltip_text(
            "Record voice with intelligent detection (/voice)"
        )
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
        # Initialize TTS state from config default
        try:
            self.set_tts_enabled(
                bool(getattr(self.config, "tts_enabled_default", False))
            )
        except Exception:
            pass

        # History button
        self.history_button = Gtk.Button(label="🕘")
        self.history_button.set_tooltip_text("Show conversation history (/history)")
        try:
            self.history_button.connect(
                "clicked", lambda _b: self.on_command("/history")
            )
        except Exception:
            pass
        controls_box.append(self.history_button)

        # OCR select region button
        self.ocr_select_button = Gtk.Button(label="🔲")
        self.ocr_select_button.set_tooltip_text(
            "Select screen region for OCR (/ocr select)"
        )
        try:
            self.ocr_select_button.connect(
                "clicked", lambda _b: self.on_command("/ocr select")
            )
        except Exception:
            pass
        controls_box.append(self.ocr_select_button)


        # Refresh button
        self.refresh_button = Gtk.Button(label="↻")
        self.refresh_button.set_tooltip_text("Refresh / Reset conversation")
        try:
            self.refresh_button.connect("clicked", self._on_refresh_clicked)
        except Exception:
            pass
        controls_box.append(self.refresh_button)

        main_box.append(controls_box)

        # Search entry
        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text("Type your message...")
        self.search_entry.set_size_request(-1, 50)
        self.search_entry.connect("activate", self._on_entry_activate)
        main_box.append(self.search_entry)

        # Conversation history widget
        self.conversation_history = ConversationHistoryWidget()
        self.conversation_history.set_vexpand(True)
        self.conversation_history.set_margin_top(10)
        main_box.append(self.conversation_history)

        # Status bar at bottom with spinner
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        status_box.set_halign(Gtk.Align.CENTER)
        self.spinner = Gtk.Spinner()
        try:
            # Spinner size controlled by CSS (32x32px)
            self.spinner.set_spinning(False)
        except Exception:
            pass
        status_box.append(self.spinner)
        self.status_label = Gtk.Label()
        self.status_label.set_markup(
            "<span size='small' alpha='60%'>Press Esc to close</span>"
        )
        status_box.append(self.status_label)
        status_box.set_margin_top(10)
        main_box.append(status_box)

        # Track current model name
        self._current_model = "llama-3.2-3b"  # Default, will be fetched

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

        # Drag state for moving window
        self._drag_active = False
        self._drag_start_x = 0
        self._drag_start_y = 0

        # Add drag controller for window movement
        self._setup_drag_controller()

        GLib.timeout_add_seconds(5, self._refresh_context)

        # Initialize conversation handler if message_bus available
        if self._message_bus:
            self._init_conversation_handler()

    def _setup_drag_controller(self):
        """Setup drag controller to make window movable via drag handle."""
        try:
            if not hasattr(self, "_drag_handle"):
                return

            # Create gesture for dragging on the handle
            drag_gesture = Gtk.GestureDrag()
            drag_gesture.set_button(1)  # Left mouse button

            window_start_pos = [0, 0]  # Store window position at drag start

            def on_drag_begin(gesture, start_x, start_y):
                try:
                    self._drag_active = True

                    # Get current window position (X11)
                    try:
                        from gi.repository import GdkX11

                        surface = self.get_surface()
                        if surface and isinstance(surface, GdkX11.X11Surface):
                            xid = GdkX11.X11Surface.get_xid(surface)
                            from Xlib import display

                            d = display.Display()
                            win = d.create_resource_object("window", xid)
                            geom = win.get_geometry()
                            window_start_pos[0] = geom.x
                            window_start_pos[1] = geom.y
                    except Exception:
                        pass
                except Exception:
                    pass

            def on_drag_update(gesture, offset_x, offset_y):
                try:
                    if self._drag_active:
                        # Move window (X11)
                        try:
                            from gi.repository import GdkX11

                            surface = self.get_surface()
                            if surface and isinstance(surface, GdkX11.X11Surface):
                                xid = GdkX11.X11Surface.get_xid(surface)
                                from Xlib import display

                                d = display.Display()
                                win = d.create_resource_object("window", xid)
                                new_x = int(window_start_pos[0] + offset_x)
                                new_y = int(window_start_pos[1] + offset_y)
                                win.configure(x=new_x, y=new_y)
                                d.flush()
                        except Exception:
                            pass
                except Exception:
                    pass

            def on_drag_end(gesture, offset_x, offset_y):
                try:
                    self._drag_active = False
                except Exception:
                    pass

            drag_gesture.connect("drag-begin", on_drag_begin)
            drag_gesture.connect("drag-update", on_drag_update)
            drag_gesture.connect("drag-end", on_drag_end)

            # Add controller to drag handle
            self._drag_handle.add_controller(drag_gesture)

            # Change cursor on hover
            motion_controller = Gtk.EventControllerMotion()

            def on_enter(_ctrl, _x, _y):
                try:
                    self._drag_handle.set_cursor_from_name("grab")
                except Exception:
                    pass

            def on_leave(_ctrl):
                try:
                    self._drag_handle.set_cursor_from_name("default")
                except Exception:
                    pass

            motion_controller.connect("enter", on_enter)
            motion_controller.connect("leave", on_leave)
            self._drag_handle.add_controller(motion_controller)

            logger.info("Drag controller setup for window movement")
        except Exception as e:
            logger.error("Failed to setup drag controller", error=str(e))

    def _setup_styling(self):
        """Setup CSS styling."""
        css_provider = Gtk.CssProvider()

        # Load conversation styles from external file
        try:
            from pathlib import Path

            conversation_css_path = (
                Path(__file__).parent / "styles" / "conversation.css"
            )
            if conversation_css_path.exists():
                with open(conversation_css_path, "rb") as f:
                    conversation_css = f.read()
            else:
                conversation_css = b""
        except Exception as e:
            logger.warning(f"Could not load conversation.css: {e}")
            conversation_css = b""

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
        
        spinner {
            min-width: 32px;
            min-height: 32px;
        }
        
        .drag-handle {
            color: #89b4fa;
            font-size: 14px;
            opacity: 0.7;
            padding: 4px;
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
        
        .toast { 
            background: #1f2937; 
            color: #e5e7eb; 
            border-radius: 8px; 
            padding: 8px 14px; 
        }
        """

        # Combine main CSS with conversation CSS
        full_css = css + b"\n" + conversation_css
        css_provider.load_from_data(full_css)

        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    # ============================================================
    # UI EVENT HANDLERS
    # ============================================================

    def _on_mic_clicked(self, _button):
        """Handle mic button click for conversational voice capture."""
        try:
            # If an approval prompt is active AND handlers exist, run short approval flow
            approval_widget = getattr(self, "_pending_approval_widget", None)
            approval_handlers = getattr(self, "_pending_approval_handlers", None)
            if approval_widget is not None and approval_handlers:
                self._voice_approve_flow()
            else:
                self._start_conversational_voice_capture()
        except Exception:
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
            # Always use conversational input processing
            if self.conversation_handler:
                self._process_conversational_input(text)
            else:
                # Fallback if handler is not ready
                self.show_toast("Conversation handler not ready.")
            entry.set_text("")


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

    # ============================================================
    # WINDOW VISIBILITY & MANAGEMENT
    # ============================================================

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
            # Fetch current model name
            self.update_model_name()
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
                self.set_status("Listening... (I'll detect when you're done)")
                self.mic_button.set_sensitive(False)
                logger.debug("Recording started")
            else:
                self.mic_button.set_label("🎤")
                self.set_status("Ready")
                self.mic_button.set_sensitive(True)
                logger.debug("Recording stopped")
        except Exception as e:
            logger.error(
                "Error indicating recording state", error=str(e), exc_info=True
            )

    # ============================================================
    # VOICE & TTS
    # ============================================================

    def _start_conversational_voice_capture(self):
        """Capture voice with VAD, run STT via message bus, and feed transcript to conversation handler."""

        def on_transcript(transcript):
            """Handle transcript from voice capture."""
            try:
                self.search_entry.set_text("")
                self._process_conversational_input(transcript)
            except Exception as proc_err:
                logger.error(
                    "Error processing conversational input",
                    error=str(proc_err),
                    exc_info=True,
                )
                self.show_toast(f"Processing error: {proc_err}")
                self.indicate_recording(False)

        def on_error(error_msg):
            """Handle voice capture error."""
            self.show_toast(error_msg)

        def on_recording_state(is_recording):
            """Update recording state in UI."""
            self.indicate_recording(is_recording)

        # Use voice handler to capture
        self.voice_handler.capture_voice(
            on_transcript=on_transcript,
            on_error=on_error,
            on_recording_state=on_recording_state,
            short_mode=False,
        )

    def _voice_approve_flow(self):
        """Short voice capture to detect approve/cancel during pending approval."""

        def on_transcript(transcript):
            """Handle transcript and check for approval keywords."""
            try:
                handlers = getattr(self, "_pending_approval_handlers", None)
                if not handlers:
                    return

                txt = transcript.lower()
                approve_words = [
                    "approve",
                    "yes",
                    "go ahead",
                    "proceed",
                    "ok",
                    "okay",
                    "confirm",
                    "do it",
                ]
                cancel_words = ["cancel", "no", "stop", "don't", "abort", "decline"]

                if any(w in txt for w in approve_words):
                    handlers.get("approve", lambda: None)()
                    self._pending_approval_handlers = None
                elif any(w in txt for w in cancel_words):
                    handlers.get("cancel", lambda: None)()
                    self._pending_approval_handlers = None
                else:
                    self.show_toast("Say 'approve' or 'cancel'")
            except Exception:
                pass

        def on_error(error_msg):
            """Handle voice capture error."""
            self.show_toast(error_msg)

        def on_recording_state(is_recording):
            """Update recording state in UI."""
            self.indicate_recording(is_recording)

        # Use voice handler with short mode for approvals
        self.voice_handler.capture_voice(
            on_transcript=on_transcript,
            on_error=on_error,
            on_recording_state=on_recording_state,
            short_mode=True,
        )

    def _speak(self, text: str):
        """Background TTS via audio service; best-effort playback."""
        self.voice_handler.speak(text)

    # ============================================================
    # RESULTS DISPLAY (CONVERSATIONAL)
    # ============================================================

    def add_result(self, title: str, content: str = "", payload: Optional[dict] = None):
        """
        Add a result to the conversation history.
        Compatibility method for legacy overlay API.
        
        Args:
            title: Title/header for the result
            content: Content/subtitle text
            payload: Optional payload for clickable results (currently not used)
        """
        self._remove_empty_state()
        
        # Format as assistant message
        if content:
            message = f"**{title}**\n{content}"
        else:
            message = title
        
        self.conversation_history.add_assistant_message(message)
    
    def clear_results(self):
        """Clear all results from the conversation history."""
        self.conversation_history.clear_history()
    
    def add_buttons_row(self, title: str, buttons: List[tuple]):
        """
        Add a row of buttons to the conversation history.
        
        Args:
            title: Title/header for the button row
            buttons: List of (label, command) tuples
        """
        try:
            from gi.repository import Gtk
            
            # Create a box for the button row
            button_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            button_box.set_margin_top(12)
            button_box.set_margin_bottom(8)
            
            # Add title label
            title_label = Gtk.Label()
            title_label.set_markup(f"<b>{title}</b>")
            title_label.set_halign(Gtk.Align.START)
            title_label.set_margin_start(12)
            button_box.append(title_label)
            
            # Create horizontal box for buttons
            buttons_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            buttons_hbox.set_halign(Gtk.Align.START)
            buttons_hbox.set_margin_start(12)
            buttons_hbox.set_margin_top(4)
            
            # Add buttons
            for label, command in buttons:
                btn = Gtk.Button(label=label)
                # Use a factory function to properly capture the command in the closure
                def make_handler(cmd):
                    return lambda w: self.on_command(cmd)
                btn.connect("clicked", make_handler(command))
                buttons_hbox.append(btn)
            
            button_box.append(buttons_hbox)
            
            # Add to conversation history
            self.conversation_history.add_widget(button_box)
        except Exception as e:
            logger.error("Failed to add button row", error=str(e))

    def _remove_empty_state(self):
        """Remove empty state if present (wrapper for conversation history)."""
        if hasattr(self.conversation_history, '_empty_state'):
            self.conversation_history._remove_empty_state()

    # ============================================================
    # STATUS & UI UPDATES
    # ============================================================

    def set_status(self, text: str):
        """Set status bar text with app name and model info."""
        # Build status components
        components = []

        # Always add Neuralux as application name
        components.append("Neuralux")

        # Add status text
        components.append(text)

        # Add active application if available
        if self._active_app:
            components.append(f"App: {self._active_app}")

        # Add model name
        if hasattr(self, "_current_model"):
            components.append(f"Model: {self._current_model}")

        # Join with bullets
        status_text = " • ".join(components)
        self.status_label.set_markup(
            f"<span size='small' alpha='60%'>{status_text}</span>"
        )

    def update_model_name(self):
        """Fetch and update the current model name from LLM service."""
        try:
            import httpx

            response = httpx.get("http://localhost:8000/v1/models", timeout=2.0)
            if response.status_code == 200:
                data = response.json()
                model_name = data.get("name", "unknown")
                # Simplify model name for display
                if "llama" in model_name.lower():
                    if "3.2" in model_name:
                        self._current_model = "Llama-3.2-3B"
                    else:
                        self._current_model = "Llama"
                elif "mistral" in model_name.lower():
                    if "7b" in model_name.lower():
                        self._current_model = "Mistral-7B"
                    else:
                        self._current_model = "Mistral"
                else:
                    # Use first part of model name
                    self._current_model = model_name.split("-")[0].capitalize()
        except Exception:
            # Keep current or default
            pass

    def begin_busy(self, text: str = "Thinking..."):
        """Show spinner and status text."""
        try:
            self.spinner.set_spinning(True)
            self.spinner.set_visible(True)
        except Exception:
            pass
        self.set_status(text)

    def end_busy(self, text: str = "Ready"):
        """Hide spinner and set final status text."""
        try:
            self.spinner.set_spinning(False)
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

    # ============================================================
    # CONTEXT & APP DETECTION
    # ============================================================

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
            out = subprocess.check_output(
                ["bash", "-lc", cmd], stderr=subprocess.DEVNULL, text=True
            )
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
            pid = subprocess.check_output(
                ["bash", "-lc", cmd], stderr=subprocess.DEVNULL, text=True
            ).strip()
            if pid.isdigit():
                pname = subprocess.check_output(
                    ["bash", "-lc", f"ps -p {pid} -o comm="],
                    stderr=subprocess.DEVNULL,
                    text=True,
                ).strip()
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
        win = d.create_resource_object("window", xid)

        NET_WM_STATE = d.intern_atom("_NET_WM_STATE")
        NET_WM_STATE_ABOVE = d.intern_atom("_NET_WM_STATE_ABOVE")
        NET_WM_STATE_FOCUSED = d.intern_atom("_NET_WM_STATE_FOCUSED")
        NET_WM_WINDOW_TYPE = d.intern_atom("_NET_WM_WINDOW_TYPE")
        NET_WM_WINDOW_TYPE_DIALOG = d.intern_atom("_NET_WM_WINDOW_TYPE_DIALOG")
        NET_WM_WINDOW_TYPE_UTILITY = d.intern_atom("_NET_WM_WINDOW_TYPE_UTILITY")

        # Set window type to utility+dialog (commonly floats above normal windows)
        try:
            win.change_property(
                NET_WM_WINDOW_TYPE,
                Xatom.ATOM,
                32,
                [NET_WM_WINDOW_TYPE_UTILITY, NET_WM_WINDOW_TYPE_DIALOG],
            )
        except Exception:
            pass

        # Send client message to add ABOVE state (1 = _NET_WM_STATE_ADD)
        try:
            ev = protocol.event.ClientMessage(
                window=win,
                client_type=NET_WM_STATE,
                data=(
                    32,
                    [1, NET_WM_STATE_ABOVE, 0, 1, 0],
                ),  # source=1 means application
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

    # Conversation Mode Methods -------------------------------------------

    # ============================================================
    # CONVERSATION MODE
    # ============================================================

    def _init_conversation_handler(self):
        """Initialize the conversation handler."""
        try:
            # Subscribe to agent suggestions
            if self._message_bus:
                loop = asyncio.get_event_loop()
                loop.create_task(self._message_bus.subscribe("agent.suggestion", self._handle_suggestion))

            if not self._message_bus:
                logger.warning("Cannot initialize conversation handler: no message bus")
                self._conversation_mode_enabled = False
                # Disable conversation toggle button
                if hasattr(self, "conversation_toggle_button"):
                    self.conversation_toggle_button.set_sensitive(False)
                    self.conversation_toggle_button.set_tooltip_text(
                        "Conversation mode unavailable (message bus not connected)"
                    )
                return

            self.conversation_handler = OverlayConversationHandler(
                message_bus=self._message_bus,
                session_id=None,  # Will use default overlay session
                on_approval_needed=self._handle_approval_needed,
                on_action_complete=self._handle_action_complete,
                on_error=self._handle_conversation_error,
            )

            logger.info("Conversation handler initialized successfully")
        except Exception as e:
            logger.error(
                "Failed to initialize conversation handler", error=str(e), exc_info=True
            )
            self._conversation_mode_enabled = False
            if hasattr(self, "conversation_toggle_button"):
                self.conversation_toggle_button.set_sensitive(False)
                self.conversation_toggle_button.set_tooltip_text(
                    f"Conversation mode error: {e}"
                )

    def _on_refresh_clicked(self, button):
        """Handle refresh button click."""
        try:
            if self.conversation_handler:
                # Clear any pending approval UI/state first
                try:
                    if getattr(self, "_pending_approval_widget", None):
                        try:
                            self.conversation_history.remove_widget(
                                self._pending_approval_widget
                            )
                        except Exception:
                            pass
                        self._pending_approval_widget = None
                    self._pending_approval_handlers = None
                    self._pending_approval_dialog = None
                    # Also cancel pending actions in handler (best-effort)
                    try:
                        self.conversation_handler.cancel_pending_actions()
                    except Exception:
                        pass
                except Exception:
                    pass
                # In conversation mode, reset the conversation
                self.conversation_handler.reset_conversation()
                self.conversation_history.clear_history()
                self.show_toast("✨ Conversation reset!")
                self.set_status("Ready")
                logger.info("Conversation reset via refresh button")
        except Exception as e:
            logger.error("Failed to handle refresh", error=str(e))
            self.show_toast("Reset failed")


    def _load_conversation_history(self):
        """Load conversation history into the view."""
        try:
            if not self.conversation_handler:
                return

            turns = self.conversation_handler.get_conversation_history()
            self.conversation_history.load_history(turns)
            logger.info(f"Loaded {len(turns)} conversation turns")
        except Exception as e:
            logger.error("Failed to load conversation history", error=str(e))

    def _process_conversational_input(self, user_input: str):
        """
        Process user input in conversational mode.

        Args:
            user_input: The user's message
        """
        if not self.conversation_handler:
            self.show_toast("Conversation mode unavailable - message bus not connected")
            self.conversation_history.add_assistant_message(
                "⚠️ Conversation mode is not available. Make sure services are running: 'make start-all'"
            )
            logger.error(
                "Attempted to use conversation mode without handler initialized"
            )
            return

        try:
            # Add user message to history immediately
            self.conversation_history.add_user_message(user_input)

            # Show loading indicator
            loading = self.conversation_history.add_loading_indicator("Thinking...")
            # Watchdog to recover if async callback never arrives
            finished = [False]

            # Process message asynchronously
            def _on_result(result, error):
                # Remove loading indicator
                self.conversation_history.remove_widget(loading)
                finished[0] = True

                if error:
                    logger.error("Conversation processing error", error=str(error))
                    self.conversation_history.add_assistant_message(
                        f"Sorry, an error occurred: {str(error)}"
                    )
                    self.set_status("Error")
                    return

                # Format and display result
                formatted = self.conversation_handler.format_result_for_display(result)
                result_type = formatted.get("type", "unknown")

                # Log for debugging
                logger.info(f"Displaying result type: {result_type}")

                if result_type == "needs_approval":
                    # Show approval dialog
                    self._show_approval_dialog(formatted)
                    self.conversation_history.add_assistant_message(
                        "I've planned some actions that need your approval."
                    )

                elif result_type == "response" or result_type == "success":
                    # Handle both "response" and "success" result types
                    message = formatted.get("message", result.get("message", "Done!"))

                    # If there's LLM-generated text, use that as the message
                    llm_text = None
                    if "last_generated_text" in result:
                        message = result["last_generated_text"]
                        llm_text = message
                    elif "content" in result:
                        message = result["content"]
                        llm_text = message

                    # Get actions list
                    actions_list = (
                        formatted.get("actions_executed")
                        or formatted.get("actions")
                        or result.get("actions_executed")
                        or result.get("actions")
                        or []
                    )

                    # For responses with actions, check if it's an llm_generate action
                    if actions_list:
                        for action in actions_list:
                            if action.get("action_type") == "llm_generate":
                                # Use the LLM-generated content from the action result
                                action_details = action.get("details", {})
                                if not action_details:
                                    action_details = action.get("result", {}).get(
                                        "details", {}
                                    )
                                llm_content = action_details.get("content", "")
                                if llm_content:
                                    message = llm_content
                                    llm_text = llm_content
                                break
                    elif message:
                        # No actions - simple conversational response
                        llm_text = message

                    self.conversation_history.add_assistant_message(message)

                    # Add action result cards
                    # Prefer formatted actions list; fall back to raw result keys
                    actions_executed = (
                        formatted.get("actions_executed")
                        or formatted.get("actions")
                        or result.get("actions_executed")
                        or result.get("actions")
                        or []
                    )

                    # Auto TTS for conversational replies (best-effort)
                    try:
                        if getattr(self, "_tts_enabled", False):
                            # Determine what to speak based on action types
                            text_to_speak = None

                            logger.info(
                                "TTS processing",
                                tts_enabled=True,
                                has_actions=bool(actions_executed),
                                action_count=(
                                    len(actions_executed) if actions_executed else 0
                                ),
                                has_llm_text=bool(llm_text),
                            )

                            if actions_executed:
                                action_types = [
                                    a.get("action_type", "") for a in actions_executed
                                ]
                                logger.info(
                                    "Action types detected", action_types=action_types
                                )

                                # For non-conversational actions, speak completion messages
                                if action_types:
                                    # Check if there's an LLM_GENERATE action (conversational response)
                                    if "llm_generate" in action_types:
                                        # Speak the actual AI response
                                        text_to_speak = llm_text
                                        logger.info(
                                            "Speaking LLM response",
                                            length=(
                                                len(text_to_speak)
                                                if text_to_speak
                                                else 0
                                            ),
                                        )
                                    else:
                                        # Speak completion message for actions
                                        action_names = {
                                            "command_execute": "Command executed successfully",
                                            "web_search": "Web search completed successfully",
                                            "document_query": "File search completed successfully",
                                            "ocr_capture": "Text extracted successfully",
                                        }

                                        # Use the first action type's completion message
                                        primary_action = action_types[0]
                                        text_to_speak = action_names.get(
                                            primary_action,
                                            "Action completed successfully",
                                        )
                                        logger.info(
                                            "Speaking action completion",
                                            action=primary_action,
                                            message=text_to_speak,
                                        )
                            else:
                                # No actions - likely just conversation, speak the message
                                text_to_speak = llm_text
                                logger.info(
                                    "Speaking conversational message",
                                    length=len(text_to_speak) if text_to_speak else 0,
                                )

                            if text_to_speak:
                                logger.info("Calling _speak", text=text_to_speak[:50])
                                self._speak(text_to_speak[:220])
                            else:
                                logger.warning("TTS enabled but no text to speak")
                    except Exception as e:
                        logger.error("TTS error", error=str(e), exc_info=True)

                    # Add action result cards (but skip llm_generate since it's shown as message bubble)
                    for action in actions_executed:
                        # Don't show LLM generation as a separate card - it's already in the message bubble
                        if action.get("action_type") != "llm_generate":
                            self.conversation_history.add_action_result(action)

                    self.set_status("Ready")

                elif result_type == "error":
                    error_msg = formatted.get("message", "An error occurred")
                    self.conversation_history.add_assistant_message(error_msg)
                    self.set_status("Error")

                else:
                    # Unknown result type - display whatever we have
                    logger.warning(f"Unknown result type: {result_type}")
                    message = str(
                        result.get("message", result.get("content", "Completed"))
                    )
                    self.conversation_history.add_assistant_message(message)
                    self.set_status("Ready")

            # Start async processing
            self.conversation_handler.process_message_async(user_input, _on_result)
            self.set_status("Processing...")

            # Check if this is a music generation request - use extended watchdog timeout
            lower_input = user_input.lower()
            is_music_request = any(phrase in lower_input for phrase in [
                "generate music", "generate a song", "generate song",
                "create music", "create a song", "create song",
                "make music", "make a song", "make song",
                "compose music", "compose a song", "compose song",
                "song about", "music about"
            ])
            
            # Extended watchdog timeout for music generation (340 seconds = 5.67 minutes)
            watchdog_timeout = 340 if is_music_request else 35

            # Watchdog: if no result, reset conversational engine
            def _watchdog():
                try:
                    if not finished[0]:
                        logger.error(
                            "Conversational response watchdog timeout - resetting handler"
                        )
                        try:
                            self.conversation_history.remove_widget(loading)
                        except Exception:
                            pass
                        try:
                            self.conversation_handler.reset_conversation()
                        except Exception:
                            pass
                        self.conversation_history.add_assistant_message(
                            "Sorry, that took too long. I've reset the voice engine; please try again."
                        )
                        self.set_status("Ready")
                except Exception:
                    pass
                return False

            try:
                GLib.timeout_add_seconds(watchdog_timeout, _watchdog)
            except Exception:
                pass

        except Exception as e:
            logger.error(
                "Failed to process conversational input", error=str(e), exc_info=True
            )
            self.show_toast(f"Error: {e}")

    def _show_approval_dialog(self, approval_data: dict):
        """
        Show approval dialog for pending actions.

        Args:
            approval_data: Formatted approval data from conversation handler
        """
        try:
            actions = approval_data.get("actions", [])
            message = approval_data.get(
                "message", "The AI wants to perform these actions:"
            )

            # Store pending actions in the conversation handler
            if self.conversation_handler:
                self.conversation_handler._pending_actions = actions

            def on_approve():
                # Close any existing dialog and remove approval widget
                self._pending_approval_dialog = None
                if (
                    hasattr(self, "_pending_approval_widget")
                    and self._pending_approval_widget
                ):
                    try:
                        self.conversation_history.remove_widget(
                            self._pending_approval_widget
                        )
                    except Exception:
                        pass
                    self._pending_approval_widget = None

                # Show executing status
                loading = self.conversation_history.add_loading_indicator(
                    "Executing actions..."
                )

                def _on_execute_result(result, error):
                    # Remove loading indicator
                    self.conversation_history.remove_widget(loading)

                    if error:
                        self.conversation_history.add_assistant_message(
                            f"Execution failed: {str(error)}"
                        )
                        self.set_status("Ready")
                        return

                    # Display results
                    logger.info(
                        "Execution result received",
                        result_keys=list(result.keys()) if result else None,
                    )

                    # Check if the result has action details
                    actions_executed = result.get(
                        "actions_executed", result.get("actions", [])
                    )

                    logger.info(f"Actions to display: {len(actions_executed)}")

                    # If there are executed actions, show them
                    if actions_executed:
                        for action in actions_executed:
                            logger.info(
                                "Adding action result",
                                action_type=action.get("action_type"),
                                has_details=bool(action.get("details")),
                                has_output="output" in action.get("details", {}),
                            )
                            self.conversation_history.add_action_result(action)
                    else:
                        logger.warning(
                            "No actions_executed in result!",
                            result_keys=list(result.keys()),
                        )

                    # Show summary message
                    message = result.get(
                        "message", result.get("explanation", "Actions completed!")
                    )
                    if message and message != "Actions completed!":
                        self.conversation_history.add_assistant_message(message)

                    self.set_status("Ready")
                    self.show_toast("✓ Done!")

                # Execute approved actions
                self.conversation_handler.approve_and_execute_async(_on_execute_result)
                # Clear voice approval handlers
                self._pending_approval_handlers = None

            def on_cancel():
                # Remove approval widget from conversation
                if (
                    hasattr(self, "_pending_approval_widget")
                    and self._pending_approval_widget
                ):
                    self.conversation_history.remove_widget(
                        self._pending_approval_widget
                    )
                    self._pending_approval_widget = None

                self.conversation_handler.cancel_pending_actions()
                self.conversation_history.add_assistant_message("Actions cancelled.")
                self.set_status("Ready")
                # Clear voice approval handlers
                self._pending_approval_handlers = None

            # Expose handlers for voice approval
            self._pending_approval_handlers = {
                "approve": on_approve,
                "cancel": on_cancel,
            }

            # Create inline approval UI instead of separate dialog
            approval_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            approval_box.add_css_class("approval-card")
            approval_box.set_margin_top(2)
            approval_box.set_margin_bottom(2)
            approval_box.set_margin_start(6)
            approval_box.set_margin_end(6)

            # Message label
            msg_label = Gtk.Label(label=message, wrap=True, xalign=0)
            msg_label.add_css_class("approval-message")
            approval_box.append(msg_label)

            # Actions list
            actions_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            actions_box.add_css_class("approval-actions-list")
            actions_box.set_margin_start(6)

            for i, action in enumerate(actions, 1):
                action_text = action.get(
                    "description", action.get("action_type", "Unknown action")
                )
                action_label = Gtk.Label(label=f"• {action_text}", wrap=True, xalign=0)
                action_label.add_css_class("approval-action-item")
                actions_box.append(action_label)

            approval_box.append(actions_box)

            # Buttons
            buttons_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            buttons_box.set_halign(Gtk.Align.END)
            buttons_box.set_margin_top(4)
            buttons_box.add_css_class("approval-buttons")

            cancel_btn = Gtk.Button(label="✕ Cancel")
            cancel_btn.add_css_class("approval-cancel-btn")
            cancel_btn.add_css_class("destructive-action")
            cancel_btn.connect("clicked", lambda btn: on_cancel())

            approve_btn = Gtk.Button(label="✓ Approve & Execute")
            approve_btn.add_css_class("approval-approve-btn")
            approve_btn.add_css_class("suggested-action")
            approve_btn.connect("clicked", lambda btn: on_approve())

            buttons_box.append(cancel_btn)
            buttons_box.append(approve_btn)
            approval_box.append(buttons_box)

            # Add to conversation history
            self.conversation_history.add_widget(approval_box)
            self._pending_approval_widget = approval_box

        except Exception as e:
            logger.error("Failed to show approval dialog", error=str(e), exc_info=True)

    def _handle_approval_needed(self, action):
        """Callback when an action needs approval."""
        # This is called from the handler - we handle it in _show_approval_dialog
        pass

    def _handle_action_complete(self, action):
        """Callback when an action completes."""
        logger.info("Action completed", action_type=action.get("action_type"))

    def _handle_conversation_error(self, error):
        """Callback for conversation errors."""
        logger.error("Conversation error", error=str(error))
        self.show_toast(f"Error: {error}")

    async def _handle_suggestion(self, suggestion):
        """Handle incoming suggestions from the agent by creating an interactive card."""
        if not isinstance(suggestion, dict):
            return

        title = suggestion.get("title") or "Suggestion"
        message = suggestion.get("message") or ""
        actions = suggestion.get("actions") or []

        def _create_suggestion_card():
            try:
                card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
                card.add_css_class("assistant-message-box") # Reuse existing style
                card.set_margin_top(4)
                card.set_margin_bottom(4)

                # Title
                title_label = Gtk.Label(xalign=0)
                title_label.set_markup(f"<b>🧠 {GLib.markup_escape_text(title)}</b>")
                card.append(title_label)

                # Message
                if message:
                    msg_label = Gtk.Label(label=message, xalign=0, wrap=True)
                    msg_label.set_margin_top(4)
                    card.append(msg_label)

                # Action buttons
                if isinstance(actions, list) and actions:
                    buttons_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
                    buttons_box.set_margin_top(8)
                    
                    for action in actions:
                        label = action.get("label")
                        command = action.get("command")
                        if label and command:
                            button = Gtk.Button(label=label)
                            button.add_css_class("suggested-action")
                            button.set_halign(Gtk.Align.START)
                            button.connect("clicked", self._on_suggestion_action_clicked, command)
                            buttons_box.append(button)
                    
                    card.append(buttons_box)

                self.conversation_history.add_widget(card)
                self.show_toast(f"New suggestion: {title}", 4000)

            except Exception as e:
                logger.error("Failed to render suggestion card", error=str(e), exc_info=True)
            return False

        GLib.idle_add(_create_suggestion_card)

    def _on_suggestion_action_clicked(self, button, command):
        """Handle click on a suggestion action button."""
        if command:
            # Hide the parent card of the button that was clicked
            try:
                parent = button.get_parent()
                if parent:
                    parent.set_visible(False)
            except Exception:
                pass
            
            logger.info(f"Executing suggested command: {command}")
            self._process_conversational_input(command)

    # Dialogs -------------------------------------------------------------

    # ============================================================
    # DIALOGS
    # ============================================================

    def show_about_dialog(self):
        """Show a native About dialog if available, otherwise a simple window."""
        AboutDialog.show(self, self.config)

    def show_settings_window(self):
        """Show a settings window bound to persisted values and using overlay commands to apply."""
        """Show a settings window bound to persisted values and using overlay commands to apply."""
        SettingsDialog.show(
            self,
            self.config,
            self.on_command,
            self.begin_busy,
            self.end_busy,
            self.show_toast,
            self.set_status,
        )


class OverlayApplication(Gtk.Application):
    """GTK Application for the overlay."""

    def __init__(
        self, config: OverlayConfig, on_command: Callable[[str], None], message_bus=None
    ):
        """Initialize the application."""
        super().__init__(application_id="com.neuralux.overlay")

        self.config = config
        self.on_command = on_command
        self.message_bus = message_bus
        self.window = None

    def do_activate(self):
        """Activate the application."""
        if not self.window:
            self.window = OverlayWindow(
                self, self.config, self.on_command, self.message_bus
            )

        self.window.present()
