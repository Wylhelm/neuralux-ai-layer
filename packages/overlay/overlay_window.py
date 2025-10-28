"""GTK4-based overlay window."""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')

from gi.repository import Gtk, Gdk, GLib
from typing import Callable, Optional
import structlog

from .config import OverlayConfig
from .search import suggest, Suggestion
from .conversation import (
    OverlayConversationHandler,
    ConversationHistoryWidget,
    ActionApprovalDialog,
)

logger = structlog.get_logger(__name__)


class OverlayWindow(Gtk.ApplicationWindow):
    """Main overlay window."""
    
    def __init__(self, app, config: OverlayConfig, on_command: Callable[[str], None], message_bus=None):
        """Initialize the overlay window."""
        super().__init__(application=app)
        
        self.config = config
        self.on_command = on_command
        self._active_app: Optional[str] = None
        self._message_bus = message_bus
        
        # Conversation handler (initialized later if message_bus available)
        self.conversation_handler: Optional[OverlayConversationHandler] = None
        self._conversation_mode_enabled = False
        self._pending_approval_dialog = None
        self._pending_approval_widget = None
        self._pending_approval_handlers = None  # {"approve": callable, "cancel": callable}
        
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
        self.mic_button.set_tooltip_text("Record voice with intelligent detection (/voice)")
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
            self.set_tts_enabled(bool(getattr(self.config, "tts_enabled_default", False)))
        except Exception:
            pass
        
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
        
        # Conversation mode toggle button
        self.conversation_toggle_button = Gtk.Button(label="💬")
        self.conversation_toggle_button.set_tooltip_text("Toggle conversational mode")
        try:
            self.conversation_toggle_button.connect("clicked", self._on_conversation_toggle)
        except Exception:
            pass
        controls_box.append(self.conversation_toggle_button)

        # Refresh button
        self.refresh_button = Gtk.Button(label="↻")
        self.refresh_button.set_tooltip_text("Refresh / Reset conversation")
        try:
            self.refresh_button.connect("clicked", self._on_refresh_clicked)
        except Exception:
            pass
        controls_box.append(self.refresh_button)

        # Image generation button
        self.image_gen_button = Gtk.Button(label="🎨")
        self.image_gen_button.set_tooltip_text("Generate image with AI (/generate)")
        try:
            self.image_gen_button.connect("clicked", self._on_image_gen_clicked)
        except Exception:
            pass
        controls_box.append(self.image_gen_button)

        main_box.append(controls_box)
        
        # Search entry
        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text("Type a command or question...")
        self.search_entry.set_size_request(-1, 50)
        self.search_entry.connect("activate", self._on_entry_activate)
        self.search_entry.connect("changed", self._on_entry_changed)
        main_box.append(self.search_entry)
        
        # Create stack for switching between results list and conversation view
        self.view_stack = Gtk.Stack()
        self.view_stack.set_vexpand(True)
        self.view_stack.set_margin_top(10)
        
        # Results list (scrollable) - Traditional mode
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_size_request(-1, 400)
        scrolled.set_vexpand(True)
        scrolled.get_style_context().add_class("results-scroller")
        
        # List box for results
        self.results_list = Gtk.ListBox()
        self.results_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.results_list.connect("row-activated", self._on_result_activated)
        scrolled.set_child(self.results_list)
        
        self.view_stack.add_named(scrolled, "results")
        
        # Conversation history widget - Conversational mode
        self.conversation_history = ConversationHistoryWidget()
        self.view_stack.add_named(self.conversation_history, "conversation")
        
        # Start with results view
        self.view_stack.set_visible_child_name("results")
        
        main_box.append(self.view_stack)
        
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
        self.status_label.set_markup("<span size='small' alpha='60%'>Press Esc to close</span>")
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
        
        # Image generation mode flag
        self._image_gen_mode = False
        
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
            if not hasattr(self, '_drag_handle'):
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
                            win = d.create_resource_object('window', xid)
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
                                win = d.create_resource_object('window', xid)
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
            conversation_css_path = Path(__file__).parent / "styles" / "conversation.css"
            if conversation_css_path.exists():
                with open(conversation_css_path, 'rb') as f:
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
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _on_mic_clicked(self, _button):
        """Handle mic button depending on mode (traditional vs conversational)."""
        try:
            if self._conversation_mode_enabled:
                # If an approval prompt is active AND handlers exist, run short approval flow
                approval_widget = getattr(self, "_pending_approval_widget", None)
                approval_handlers = getattr(self, "_pending_approval_handlers", None)
                if approval_widget is not None and approval_handlers:
                    self._voice_approve_flow()
                else:
                    self._start_conversational_voice_capture()
            else:
                # Traditional (non-conversational) mode delegates to CLI handler
                self.indicate_recording(True)
                self.on_command("/voice")
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

    def _on_image_gen_clicked(self, _button):
        """Start image generation in overlay."""
        try:
            self.clear_results()
            self.search_entry.set_text("")
            self.search_entry.set_placeholder_text("Describe the image you want to generate...")
            self.search_entry.grab_focus()
            self.set_status("Image generation mode - Enter your prompt and press Enter")
            # Set a flag for image gen mode
            self._image_gen_mode = True
        except Exception:
            pass
    
    def _on_entry_activate(self, entry):
        """Handle Enter key in search entry."""
        text = entry.get_text().strip()
        if text:
            # Check if in image generation mode
            if getattr(self, "_image_gen_mode", False):
                self._generate_image_inline(text)
                self._image_gen_mode = False
                entry.set_placeholder_text("Type a command or question...")
            # Check if in conversation mode
            elif self._conversation_mode_enabled and self.conversation_handler:
                self._process_conversational_input(text)
            else:
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
            logger.error("Error indicating recording state", error=str(e), exc_info=True)

    def _start_conversational_voice_capture(self):
        """Capture voice with VAD, run STT via message bus, and feed transcript to conversation handler."""
        try:
            # UI: show recording state
            self.indicate_recording(True)
        except Exception:
            pass

        import threading

        def _worker():
            try:
                # Check if audio service is available
                if not self._message_bus:
                    GLib.idle_add(lambda: (self.indicate_recording(False), self.show_toast("Message bus not connected")) or False)
                    return
            except Exception:
                pass
            
            try:
                # Attempt PyAudio capture with simple VAD similar to CLI
                try:
                    import pyaudio, wave, tempfile, struct
                    audio_format = pyaudio.paInt16
                    channels = 1
                    rate = 16000
                    chunk = 1024

                    p = pyaudio.PyAudio()
                    stream = p.open(format=audio_format, channels=channels, rate=rate, input=True, frames_per_buffer=chunk)
                    frames = []

                    # Pull VAD thresholds from overlay config
                    cfg_threshold = float(getattr(self.config, "vad_silence_threshold", 0.01))
                    silence_duration = float(getattr(self.config, "vad_silence_duration", 1.5))
                    # Allow user to configure silence duration via env
                    max_recording_time = int(getattr(self.config, "vad_max_recording_time", 15))
                    min_recording_time = int(getattr(self.config, "vad_min_recording_time", 1))

                    silence_frames = 0
                    silence_frame_count = int(rate / chunk * silence_duration)
                    total_frames = 0
                    max_frames = int(rate / chunk * max_recording_time)
                    min_frames = int(rate / chunk * min_recording_time)

                    speech_detected = False

                    # Dynamic noise calibration (first ~0.4s)
                    try:
                        calibration_frames = max(1, int(rate / chunk * 0.4))
                        noise_accum = 0.0
                        noise_count = 0
                        for _ in range(calibration_frames):
                            data0 = stream.read(chunk, exception_on_overflow=False)
                            frames.append(data0)
                            total_frames += 1
                            audio_cal = struct.unpack(f"{chunk}h", data0)
                            rms0 = (sum(x * x for x in audio_cal) / len(audio_cal)) ** 0.5
                            noise_accum += rms0
                            noise_count += 1
                        noise_rms = (noise_accum / max(1, noise_count)) if noise_count else 0.0
                        # If cfg_threshold < 1, treat as dynamic; else absolute RMS
                        dyn_factor = float(getattr(self.config, "vad_dynamic_factor", 1.8))
                        min_rms = int(getattr(self.config, "vad_min_rms", 120))
                        silence_threshold = max(int(noise_rms * dyn_factor), min_rms) if cfg_threshold < 1.0 else cfg_threshold
                    except Exception:
                        silence_threshold = int(getattr(self.config, "vad_min_rms", 120))

                    while total_frames < max_frames:
                        data = stream.read(chunk, exception_on_overflow=False)
                        frames.append(data)
                        total_frames += 1

                        audio_data = struct.unpack(f"{chunk}h", data)
                        rms = (sum(x * x for x in audio_data) / len(audio_data)) ** 0.5

                        if rms > silence_threshold:
                            speech_detected = True
                            silence_frames = 0
                        else:
                            silence_frames += 1
                            if silence_frames >= silence_frame_count and total_frames >= min_frames and speech_detected:
                                break

                    stream.stop_stream()
                    stream.close()
                    
                    if not speech_detected:
                        p.terminate()
                        GLib.idle_add(lambda: (self.indicate_recording(False), self.show_toast("No speech detected")) or False)
                        return

                    # Get sample size BEFORE terminating PyAudio
                    sample_width = p.get_sample_size(audio_format)
                    p.terminate()

                    # Persist to temp wav
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                        temp_path = f.name
                    wf = wave.open(temp_path, "wb")
                    wf.setnchannels(channels)
                    wf.setsampwidth(sample_width)
                    wf.setframerate(rate)
                    wf.writeframes(b"".join(frames))
                    wf.close()
                except Exception as rec_err:
                    GLib.idle_add(lambda: (self.indicate_recording(False), self.show_toast(f"Recording error: {rec_err}")) or False)
                    return

                # STT via Audio HTTP API (with fallbacks)
                transcript = ""
                try:
                    import httpx, os
                    # Get language from config
                    language = getattr(self.config, "stt_language", "en")
                    # First: with VAD filter
                    with open(temp_path, "rb") as f:
                        files = {"file": ("speech.wav", f, "audio/wav")}
                        resp = httpx.post(
                            "http://localhost:8006/stt/file",
                            params={"language": language, "vad_filter": "true"},
                            files=files,
                            timeout=60.0,
                        )
                    if resp.status_code == 200:
                        data = resp.json()
                        transcript = (data.get("text") or "").strip()
                    # Second: retry without VAD
                    if not transcript:
                        try:
                            with open(temp_path, "rb") as f2:
                                files2 = {"file": ("speech.wav", f2, "audio/wav")}
                                resp2 = httpx.post(
                                    "http://localhost:8006/stt/file",
                                    params={"language": language, "vad_filter": "false"},
                                    files=files2,
                                    timeout=60.0,
                                )
                            if resp2.status_code == 200:
                                data2 = resp2.json()
                                transcript = (data2.get("text") or "").strip()
                        except Exception:
                            pass
                    # Third: fallback to bus STT if still empty
                    if not transcript and self._message_bus:
                        try:
                            stt_fb = self._message_bus.request(
                                "ai.audio.stt",
                                {"audio_path": temp_path, "vad_filter": False, "language": language},
                                timeout=30.0,
                            )
                            try:
                                stt_fb = stt_fb if isinstance(stt_fb, dict) else stt_fb.result(30.0)
                            except Exception:
                                pass
                            if isinstance(stt_fb, dict) and "error" not in stt_fb:
                                transcript = (stt_fb.get("text") or "").strip()
                        except Exception:
                            pass
                finally:
                    try:
                        import os
                        os.unlink(temp_path)
                    except Exception:
                        pass

                # UI off for recording
                GLib.idle_add(lambda: self.indicate_recording(False) or False)

                if not transcript:
                    GLib.idle_add(lambda: self.show_toast("Didn't catch that") or False)
                    logger.warning("Voice capture: no transcript")
                    return

                # Feed into conversation handler with error protection
                logger.info("Voice capture: transcript received", length=len(transcript))
                
                def _safe_process():
                    try:
                        self.search_entry.set_text("")
                        self._process_conversational_input(transcript)
                    except Exception as proc_err:
                        logger.error("Error processing conversational input", error=str(proc_err), exc_info=True)
                        self.show_toast(f"Processing error: {proc_err}")
                        # Ensure we re-enable the mic button
                        self.indicate_recording(False)
                    return False
                
                GLib.idle_add(_safe_process)

            except Exception as e:
                logger.error("Voice capture error", error=str(e), exc_info=True)
                GLib.idle_add(lambda: (self.indicate_recording(False), self.show_toast(f"Voice error: {e}")) or False)

        threading.Thread(target=_worker, daemon=True).start()

    def _voice_approve_flow(self):
        """Short voice capture to detect approve/cancel during pending approval."""
        try:
            self.indicate_recording(True)
        except Exception:
            pass

        import threading

        def _worker():
            try:
                # Reuse conversational capture but bias to shorter min duration
                try:
                    import pyaudio, wave, tempfile, struct
                    audio_format = pyaudio.paInt16
                    channels = 1
                    rate = 16000
                    chunk = 1024
                    p = pyaudio.PyAudio()
                    stream = p.open(format=audio_format, channels=channels, rate=rate, input=True, frames_per_buffer=chunk)
                    frames = []

                    cfg_threshold = float(getattr(self.config, "vad_silence_threshold", 0.01))
                    silence_duration = 0.5  # shorter for approvals
                    max_recording_time = 6
                    min_recording_time = 0.6

                    silence_frames = 0
                    silence_frame_count = int(rate / chunk * silence_duration)
                    total_frames = 0
                    max_frames = int(rate / chunk * max_recording_time)
                    min_frames = int(rate / chunk * min_recording_time)
                    speech_detected = False

                    # Dynamic noise calibration (~0.3s) for approvals
                    try:
                        calibration_frames = max(1, int(rate / chunk * 0.3))
                        noise_accum = 0.0
                        noise_count = 0
                        for _ in range(calibration_frames):
                            data0 = stream.read(chunk, exception_on_overflow=False)
                            frames.append(data0)
                            total_frames += 1
                            audio_cal = struct.unpack(f"{chunk}h", data0)
                            rms0 = (sum(x * x for x in audio_cal) / len(audio_cal)) ** 0.5
                            noise_accum += rms0
                            noise_count += 1
                        noise_rms = (noise_accum / max(1, noise_count)) if noise_count else 0.0
                        dyn_factor = float(getattr(self.config, "vad_dynamic_factor", 1.8))
                        min_rms = int(getattr(self.config, "vad_min_rms", 120))
                        silence_threshold = max(int(noise_rms * dyn_factor), min_rms) if cfg_threshold < 1.0 else cfg_threshold
                    except Exception:
                        silence_threshold = int(getattr(self.config, "vad_min_rms", 120))

                    while total_frames < max_frames:
                        data = stream.read(chunk, exception_on_overflow=False)
                        frames.append(data)
                        total_frames += 1
                        audio_data = struct.unpack(f"{chunk}h", data)
                        rms = (sum(x * x for x in audio_data) / len(audio_data)) ** 0.5
                        if rms > silence_threshold:
                            speech_detected = True
                            silence_frames = 0
                        else:
                            silence_frames += 1
                            if silence_frames >= silence_frame_count and total_frames >= min_frames and speech_detected:
                                break

                    stream.stop_stream()
                    stream.close()

                    if not speech_detected:
                        p.terminate()
                        GLib.idle_add(lambda: (self.indicate_recording(False), self.show_toast("No speech detected")) or False)
                        return

                    # Get sample size BEFORE terminating PyAudio
                    sample_width = p.get_sample_size(audio_format)
                    p.terminate()

                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                        temp_path = f.name
                    wf = wave.open(temp_path, "wb")
                    wf.setnchannels(channels)
                    wf.setsampwidth(sample_width)
                    wf.setframerate(rate)
                    wf.writeframes(b"".join(frames))
                    wf.close()
                except Exception as rec_err:
                    GLib.idle_add(lambda: (self.indicate_recording(False), self.show_toast(f"Recording error: {rec_err}")) or False)
                    return

                # STT via Audio HTTP API (with fallbacks)
                transcript = ""
                try:
                    import httpx, os
                    # Get language from config
                    language = getattr(self.config, "stt_language", "en")
                    with open(temp_path, "rb") as f:
                        files = {"file": ("speech.wav", f, "audio/wav")}
                        resp = httpx.post(
                            "http://localhost:8006/stt/file",
                            params={"language": language, "vad_filter": "true"},
                            files=files,
                            timeout=30.0,
                        )
                    if resp.status_code == 200:
                        data = resp.json()
                        transcript = (data.get("text") or "").strip().lower()
                    # Retry without VAD if empty
                    if not transcript:
                        try:
                            with open(temp_path, "rb") as f2:
                                files2 = {"file": ("speech.wav", f2, "audio/wav")}
                                resp2 = httpx.post(
                                    "http://localhost:8006/stt/file",
                                    params={"language": language, "vad_filter": "false"},
                                    files=files2,
                                    timeout=30.0,
                                )
                            if resp2.status_code == 200:
                                data2 = resp2.json()
                                transcript = (data2.get("text") or "").strip().lower()
                        except Exception:
                            pass
                    # Final fallback to bus STT if still empty
                    if not transcript and self._message_bus:
                        try:
                            stt_fb = self._message_bus.request(
                                "ai.audio.stt",
                                {"audio_path": temp_path, "vad_filter": False, "language": language},
                                timeout=20.0,
                            )
                            try:
                                stt_fb = stt_fb if isinstance(stt_fb, dict) else stt_fb.result(20.0)
                            except Exception:
                                pass
                            if isinstance(stt_fb, dict) and "error" not in stt_fb:
                                transcript = (stt_fb.get("text") or "").strip().lower()
                        except Exception:
                            pass
                finally:
                    try:
                        import os
                        os.unlink(temp_path)
                    except Exception:
                        pass

                GLib.idle_add(lambda: self.indicate_recording(False) or False)

                if not transcript:
                    GLib.idle_add(lambda: self.show_toast("Didn't catch that") or False)
                    return

                def _decide():
                    try:
                        handlers = getattr(self, "_pending_approval_handlers", None)
                        if not handlers:
                            return False
                        txt = transcript
                        approve_words = ["approve", "yes", "go ahead", "proceed", "ok", "okay", "confirm", "do it"]
                        cancel_words = ["cancel", "no", "stop", "don't", "abort", "decline"]
                        if any(w in txt for w in approve_words):
                            handlers.get("approve", lambda: None)()
                            self._pending_approval_handlers = None
                            return False
                        if any(w in txt for w in cancel_words):
                            handlers.get("cancel", lambda: None)()
                            self._pending_approval_handlers = None
                            return False
                        self.show_toast("Say 'approve' or 'cancel'")
                    except Exception:
                        pass
                    return False

                GLib.idle_add(_decide)

            except Exception as e:
                GLib.idle_add(lambda: (self.indicate_recording(False), self.show_toast(f"Voice error: {e}")) or False)

        threading.Thread(target=_worker, daemon=True).start()

    def _speak(self, text: str):
        """Background TTS via audio service; best-effort playback."""
        if not text:
            return
        import threading

        # Lazily create a playback lock to prevent overlapping audio and hangs
        if not hasattr(self, "_tts_lock") or getattr(self, "_tts_lock", None) is None:
            try:
                self._tts_lock = threading.Lock()
            except Exception:
                self._tts_lock = None

        def _worker():
            import base64, tempfile, subprocess, os, shutil, httpx
            try:
                # Serialize playback to avoid driver/sink contention
                lock = getattr(self, "_tts_lock", None)
                acquired = False
                if lock is not None:
                    acquired = lock.acquire(blocking=False)
                    if not acquired:
                        # Another playback in progress; skip to avoid deadlock
                        logger.warning("TTS playback skipped: busy")
                        return

                try:
                    # Request TTS audio from audio service
                    resp = httpx.post(
                        "http://localhost:8006/tts",
                        json={"text": text, "output_format": "wav"},
                        timeout=30.0,
                    )
                    if resp.status_code != 200:
                        logger.error("TTS HTTP error", status=resp.status_code)
                        return
                    data = resp.json()
                    audio_b64 = data.get("audio_data", "")
                    if not audio_b64:
                        logger.error("TTS response missing audio_data")
                        return

                    audio_data = base64.b64decode(audio_b64)
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                        f.write(audio_data)
                        path = f.name

                    try:
                        # Try paplay with timeout, then aplay, then ffplay
                        played = False
                        try:
                            subprocess.run(["paplay", path], check=True, capture_output=True, timeout=20)
                            played = True
                        except subprocess.TimeoutExpired:
                            logger.error("TTS playback timed out", player="paplay")
                        except Exception as e:
                            logger.warning("paplay failed; falling back", error=str(e))

                        if not played:
                            try:
                                subprocess.run(["aplay", path], check=True, capture_output=True, timeout=20)
                                played = True
                            except subprocess.TimeoutExpired:
                                logger.error("TTS playback timed out", player="aplay")
                            except Exception as e:
                                logger.warning("aplay failed; falling back", error=str(e))

                        if not played and shutil.which("ffplay"):
                            try:
                                subprocess.run([
                                    "ffplay", "-nodisp", "-autoexit", "-loglevel", "error", path
                                ], check=True, capture_output=True, timeout=25)
                                played = True
                            except subprocess.TimeoutExpired:
                                logger.error("TTS playback timed out", player="ffplay")
                            except Exception as e:
                                logger.error("ffplay failed", error=str(e))

                        if not played:
                            logger.error("No audio player succeeded for TTS")
                    finally:
                        try:
                            os.unlink(path)
                        except Exception:
                            pass
                finally:
                    if lock is not None and acquired:
                        try:
                            lock.release()
                        except Exception:
                            pass
            except Exception as e:
                # Swallow exceptions to avoid UI disruption, but log for diagnostics
                try:
                    logger.error("TTS playback error", error=str(e))
                except Exception:
                    pass

        threading.Thread(target=_worker, daemon=True).start()

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
        if hasattr(self, '_current_model'):
            components.append(f"Model: {self._current_model}")
        
        # Join with bullets
        status_text = " • ".join(components)
        self.status_label.set_markup(f"<span size='small' alpha='60%'>{status_text}</span>")

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

    # Conversation Mode Methods -------------------------------------------
    
    def _init_conversation_handler(self):
        """Initialize the conversation handler."""
        try:
            if not self._message_bus:
                logger.warning("Cannot initialize conversation handler: no message bus")
                self._conversation_mode_enabled = False
                # Disable conversation toggle button
                if hasattr(self, 'conversation_toggle_button'):
                    self.conversation_toggle_button.set_sensitive(False)
                    self.conversation_toggle_button.set_tooltip_text("Conversation mode unavailable (message bus not connected)")
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
            logger.error("Failed to initialize conversation handler", error=str(e), exc_info=True)
            self._conversation_mode_enabled = False
            if hasattr(self, 'conversation_toggle_button'):
                self.conversation_toggle_button.set_sensitive(False)
                self.conversation_toggle_button.set_tooltip_text(f"Conversation mode error: {e}")
    
    def _on_refresh_clicked(self, button):
        """Handle refresh button click."""
        try:
            if self._conversation_mode_enabled and self.conversation_handler:
                # Clear any pending approval UI/state first
                try:
                    if getattr(self, "_pending_approval_widget", None):
                        try:
                            self.conversation_history.remove_widget(self._pending_approval_widget)
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
            else:
                # In traditional mode, refresh suggestions
                self.on_command("/refresh")
                self.show_toast("Refreshed")
        except Exception as e:
            logger.error("Failed to handle refresh", error=str(e))
            self.show_toast("Reset failed")
    
    def _on_conversation_toggle(self, button):
        """Toggle between conversation mode and traditional mode."""
        try:
            self._conversation_mode_enabled = not self._conversation_mode_enabled
            
            if self._conversation_mode_enabled:
                # Switch to conversation view
                self.view_stack.set_visible_child_name("conversation")
                self.conversation_toggle_button.set_label("📋")
                self.conversation_toggle_button.set_tooltip_text("Switch to traditional mode")
                self.search_entry.set_placeholder_text("Type your message...")
                self.set_status("Conversational mode active")
                self.show_toast("Conversational mode enabled")
                
                # Load existing history if available
                if self.conversation_handler:
                    self._load_conversation_history()
            else:
                # Switch to results view
                self.view_stack.set_visible_child_name("results")
                self.conversation_toggle_button.set_label("💬")
                self.conversation_toggle_button.set_tooltip_text("Switch to conversational mode")
                self.search_entry.set_placeholder_text("Type a command or question...")
                self.set_status("Traditional mode active")
                self.show_toast("Traditional mode enabled")
        except Exception as e:
            logger.error("Failed to toggle conversation mode", error=str(e))
    
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
            logger.error("Attempted to use conversation mode without handler initialized")
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
                                    action_details = action.get("result", {}).get("details", {})
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
                            
                            logger.info("TTS processing", 
                                       tts_enabled=True,
                                       has_actions=bool(actions_executed),
                                       action_count=len(actions_executed) if actions_executed else 0,
                                       has_llm_text=bool(llm_text))
                            
                            if actions_executed:
                                action_types = [a.get("action_type", "") for a in actions_executed]
                                logger.info("Action types detected", action_types=action_types)
                                
                                # For non-conversational actions, speak completion messages
                                if action_types:
                                    # Check if there's an LLM_GENERATE action (conversational response)
                                    if "llm_generate" in action_types:
                                        # Speak the actual AI response
                                        text_to_speak = llm_text
                                        logger.info("Speaking LLM response", length=len(text_to_speak) if text_to_speak else 0)
                                    else:
                                        # Speak completion message for actions
                                        action_names = {
                                            "command_execute": "Command executed successfully",
                                            "web_search": "Web search completed successfully",
                                            "document_query": "File search completed successfully",
                                            "image_generate": "Picture generated successfully",
                                            "image_save": "Image saved successfully",
                                            "ocr_capture": "Text extracted successfully",
                                        }
                                        
                                        # Use the first action type's completion message
                                        primary_action = action_types[0]
                                        text_to_speak = action_names.get(primary_action, "Action completed successfully")
                                        logger.info("Speaking action completion", action=primary_action, message=text_to_speak)
                            else:
                                # No actions - likely just conversation, speak the message
                                text_to_speak = llm_text
                                logger.info("Speaking conversational message", length=len(text_to_speak) if text_to_speak else 0)
                            
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
                    message = str(result.get("message", result.get("content", "Completed")))
                    self.conversation_history.add_assistant_message(message)
                    self.set_status("Ready")
            
            # Start async processing
            self.conversation_handler.process_message_async(user_input, _on_result)
            self.set_status("Processing...")

            # 35s watchdog: if no result, reset conversational engine
            def _watchdog():
                try:
                    if not finished[0]:
                        logger.error("Conversational response watchdog timeout - resetting handler")
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
                GLib.timeout_add_seconds(35, _watchdog)
            except Exception:
                pass
            
        except Exception as e:
            logger.error("Failed to process conversational input", error=str(e), exc_info=True)
            self.show_toast(f"Error: {e}")
    
    def _show_approval_dialog(self, approval_data: dict):
        """
        Show approval dialog for pending actions.
        
        Args:
            approval_data: Formatted approval data from conversation handler
        """
        try:
            actions = approval_data.get("actions", [])
            message = approval_data.get("message", "The AI wants to perform these actions:")
            
            # Store pending actions in the conversation handler
            if self.conversation_handler:
                self.conversation_handler._pending_actions = actions
            
            def on_approve():
                # Close any existing dialog and remove approval widget
                self._pending_approval_dialog = None
                if hasattr(self, '_pending_approval_widget') and self._pending_approval_widget:
                    try:
                        self.conversation_history.remove_widget(self._pending_approval_widget)
                    except Exception:
                        pass
                    self._pending_approval_widget = None
                
                # Show executing status
                loading = self.conversation_history.add_loading_indicator("Executing actions...")
                
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
                    logger.info("Execution result received", result_keys=list(result.keys()) if result else None)
                    
                    # Check if the result has action details
                    actions_executed = result.get("actions_executed", result.get("actions", []))
                    
                    logger.info(f"Actions to display: {len(actions_executed)}")
                    
                    # If there are executed actions, show them
                    if actions_executed:
                        for action in actions_executed:
                            logger.info("Adding action result", 
                                       action_type=action.get("action_type"),
                                       has_details=bool(action.get("details")),
                                       has_output="output" in action.get("details", {}))
                            self.conversation_history.add_action_result(action)
                    else:
                        logger.warning("No actions_executed in result!", result_keys=list(result.keys()))
                    
                    # Show summary message
                    message = result.get("message", result.get("explanation", "Actions completed!"))
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
                if hasattr(self, '_pending_approval_widget') and self._pending_approval_widget:
                    self.conversation_history.remove_widget(self._pending_approval_widget)
                    self._pending_approval_widget = None
                
                self.conversation_handler.cancel_pending_actions()
                self.conversation_history.add_assistant_message("Actions cancelled.")
                self.set_status("Ready")
                # Clear voice approval handlers
                self._pending_approval_handlers = None

            # Expose handlers for voice approval
            self._pending_approval_handlers = {"approve": on_approve, "cancel": on_cancel}
            
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
                action_text = action.get('description', action.get('action_type', 'Unknown action'))
                action_label = Gtk.Label(
                    label=f"• {action_text}",
                    wrap=True,
                    xalign=0
                )
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
        w.set_default_size(500, 450)
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
        
        # Separator
        sep = Gtk.Separator()
        vb.append(sep)
        
        # Image Generation Settings
        img_gen_label = Gtk.Label()
        img_gen_label.set_markup("<b>Image Generation</b>")
        img_gen_label.set_halign(Gtk.Align.START)
        vb.append(img_gen_label)
        
        # Image gen model
        img_model_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        img_model_row.append(Gtk.Label(label="Model:"))
        img_model_combo = _Gtk.ComboBoxText()
        for name in ["flux-schnell (fast)", "flux-dev (quality)", "sdxl-lightning"]:
            img_model_combo.append_text(name)
        img_model_default = current.get("image_gen_model", "flux-schnell")
        try:
            idx = ["flux-schnell", "flux-dev", "sdxl-lightning"].index(img_model_default)
            img_model_combo.set_active(idx)
        except Exception:
            img_model_combo.set_active(0)
        img_model_row.append(img_model_combo)
        vb.append(img_model_row)
        
        # Image size
        img_size_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        img_size_row.append(Gtk.Label(label="Size:"))
        img_size_combo = _Gtk.ComboBoxText()
        for size in ["512x512", "768x768", "1024x768", "768x1024", "1024x1024"]:
            img_size_combo.append_text(size)
        size_default = f"{current.get('image_gen_width', 1024)}x{current.get('image_gen_height', 1024)}"
        try:
            img_size_combo.set_active(["512x512", "768x768", "1024x768", "768x1024", "1024x1024"].index(size_default))
        except Exception:
            img_size_combo.set_active(4)  # 1024x1024
        img_size_row.append(img_size_combo)
        vb.append(img_size_row)
        
        # Steps
        img_steps_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        img_steps_row.append(Gtk.Label(label="Steps:"))
        img_steps_spin = Gtk.SpinButton()
        img_steps_spin.set_range(1, 50)
        img_steps_spin.set_increments(1, 5)
        img_steps_spin.set_value(current.get("image_gen_steps", 4))
        img_steps_row.append(img_steps_spin)
        vb.append(img_steps_row)

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
                
                # Image generation settings
                img_model_text = img_model_combo.get_active_text() or "flux-schnell (fast)"
                img_model = img_model_text.split(" ")[0]  # Extract model name
                self.on_command(f"/set image_gen.model {img_model}")
                
                img_size_text = img_size_combo.get_active_text() or "1024x1024"
                width, height = map(int, img_size_text.split("x"))
                self.on_command(f"/set image_gen.width {width}")
                self.on_command(f"/set image_gen.height {height}")
                
                steps = int(img_steps_spin.get_value())
                self.on_command(f"/set image_gen.steps {steps}")
                
                info.set_text("Applied. Models will reload if required.")
            except Exception as e:
                info.set_text(f"Failed to apply: {e}")
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
                # First apply, then save
                _apply(None)
                self.on_command("/settings.save")
                info.set_text("Saved defaults.")
                self.show_toast("Settings saved")
            except Exception as e:
                info.set_text(f"Failed to save: {e}")
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

    def _generate_image_inline(self, prompt: str):
        """Generate image and display in overlay results area."""
        try:
            self.clear_results()
            self.begin_busy("Generating image...")
            
            # Get settings from stored config
            try:
                from neuralux.memory import SessionStore
                from neuralux.config import NeuraluxConfig
                cfg = NeuraluxConfig()
                store = SessionStore(cfg)
                settings = store.load_settings(cfg.settings_path())
                
                width = settings.get("image_gen_width", 1024)
                height = settings.get("image_gen_height", 1024)
                steps = settings.get("image_gen_steps", 4)
                model = settings.get("image_gen_model", "flux-schnell")
            except Exception:
                width, height, steps, model = 1024, 1024, 4, "flux-schnell"
            
            # Show generation info
            self.add_result(
                "Generating Image",
                f"Prompt: {prompt}\nSize: {width}x{height}\nSteps: {steps}\nModel: {model}"
            )
            
            # Generate in background
            import threading
            def _gen_worker():
                try:
                    import httpx
                    import base64
                    from gi.repository import GdkPixbuf, GLib
                    
                    response = httpx.post(
                        "http://localhost:8005/v1/generate-image",
                        json={
                            "prompt": prompt,
                            "width": width,
                            "height": height,
                            "num_inference_steps": steps,
                            "model": model,
                        },
                        timeout=600.0,
                    )
                    response.raise_for_status()
                    result = response.json()
                    
                    image_b64 = result.get("image_bytes_b64")
                    if image_b64:
                        # Decode image
                        image_bytes = base64.b64decode(image_b64)
                        
                        # Save to temp file for display
                        import tempfile
                        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                            f.write(image_bytes)
                            temp_path = f.name
                        
                        def _show_result():
                            try:
                                self.clear_results()
                                
                                # Create outer box for image row
                                img_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
                                img_box.set_margin_top(8)
                                img_box.set_margin_bottom(8)
                                
                                # Show prompt above image
                                prompt_label = Gtk.Label()
                                prompt_label.set_markup(f'<b>"{prompt}"</b>')
                                prompt_label.set_wrap(True)
                                prompt_label.set_xalign(0.5)
                                prompt_label.set_margin_bottom(8)
                                img_box.append(prompt_label)
                                
                                # Load and display image
                                from gi.repository import GdkPixbuf, Gdk, Gio
                                
                                try:
                                    # Load pixbuf
                                    pixbuf = GdkPixbuf.Pixbuf.new_from_file(temp_path)
                                    
                                    # Scale to fit in overlay (max 400px height, maintain aspect ratio)
                                    orig_width = pixbuf.get_width()
                                    orig_height = pixbuf.get_height()
                                    
                                    max_height = 400
                                    if orig_height > max_height:
                                        scale = max_height / orig_height
                                        new_width = int(orig_width * scale)
                                        new_height = max_height
                                        pixbuf = pixbuf.scale_simple(new_width, new_height, GdkPixbuf.InterpType.BILINEAR)
                                    
                                    # Convert to texture
                                    texture = Gdk.Texture.new_for_pixbuf(pixbuf)
                                    
                                    # Create picture widget
                                    picture = Gtk.Picture()
                                    picture.set_paintable(texture)
                                    picture.set_size_request(pixbuf.get_width(), pixbuf.get_height())
                                    picture.set_halign(Gtk.Align.CENTER)
                                    picture.set_valign(Gtk.Align.CENTER)
                                    picture.set_can_shrink(False)
                                    img_box.append(picture)
                                    
                                    logger.info(f"Image loaded: {pixbuf.get_width()}x{pixbuf.get_height()}")
                                except Exception as img_err:
                                    logger.error(f"Image display error: {img_err}")
                                    err_label = Gtk.Label(label=f"Image loaded but display failed: {img_err}\nTemp file: {temp_path}")
                                    err_label.set_wrap(True)
                                    img_box.append(err_label)
                                
                                # Store texture for clipboard (need to keep reference)
                                stored_texture = texture if 'texture' in locals() else None
                                
                                # Buttons row
                                btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
                                btn_box.set_halign(Gtk.Align.CENTER)
                                btn_box.set_margin_top(8)
                                
                                # Save button (compact)
                                save_btn = Gtk.Button(label="💾 Save")
                                def _save(_b):
                                    self._save_generated_image(image_bytes, prompt)
                                save_btn.connect("clicked", _save)
                                btn_box.append(save_btn)
                                
                                # Copy to clipboard button
                                copy_btn = Gtk.Button(label="📋 Copy")
                                def _copy(_b):
                                    try:
                                        # Copy image to clipboard
                                        clipboard = Gdk.Display.get_default().get_clipboard()
                                        if stored_texture:
                                            clipboard.set_texture(stored_texture)
                                            self.show_toast("Image copied to clipboard!")
                                        else:
                                            self.show_toast("No texture available to copy")
                                    except Exception as e:
                                        self.show_toast(f"Copy failed: {e}")
                                copy_btn.connect("clicked", _copy)
                                btn_box.append(copy_btn)
                                
                                # Continue conversation button
                                continue_btn = Gtk.Button(label="💬 Continue Chat")
                                def _continue(_b):
                                    # Exit image gen mode and prepare for conversation
                                    self._image_gen_mode = False
                                    self.search_entry.set_placeholder_text("Ask about the image or enter new prompt...")
                                    self.search_entry.grab_focus()
                                    self.set_status("Chat about your image")
                                continue_btn.connect("clicked", _continue)
                                btn_box.append(continue_btn)
                                
                                img_box.append(btn_box)
                                
                                # Add to results as a row
                                row = Gtk.ListBoxRow()
                                row.set_child(img_box)
                                row.set_activatable(False)  # Don't activate on click
                                row.set_selectable(False)   # Don't select
                                self.results_list.append(row)
                                
                                # Make sure the row is visible
                                row.set_visible(True)
                                img_box.set_visible(True)
                                
                                logger.info("Image row added to results list")
                                
                                self.end_busy("✓ Image generated!")
                                self.show_toast("Image ready!")
                            except Exception as e:
                                self.end_busy(f"Display error: {e}")
                            return False
                        
                        GLib.idle_add(_show_result)
                    else:
                        GLib.idle_add(lambda: self.end_busy("No image returned") or False)
                        
                except Exception as e:
                    GLib.idle_add(lambda err=str(e): self.end_busy(f"Generation failed: {err}") or False)
            
            threading.Thread(target=_gen_worker, daemon=True).start()
            
        except Exception as e:
            self.end_busy(f"Error: {e}")
    
    def _save_generated_image(self, image_bytes: bytes, prompt: str):
        """Save generated image with file dialog."""
        try:
            from gi.repository import Gtk as _Gtk
            import re
            from datetime import datetime
            
            dialog = _Gtk.FileDialog()
            dialog.set_title("Save Generated Image")
            
            # Generate filename
            safe_prompt = re.sub(r'[^\w\s-]', '', prompt)[:50]
            safe_prompt = re.sub(r'[-\s]+', '_', safe_prompt)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_name = f"{safe_prompt}_{timestamp}.png"
            dialog.set_initial_name(default_name)
            
            def _on_save_finish(dialog, result):
                try:
                    file = dialog.save_finish(result)
                    if file:
                        path = file.get_path()
                        with open(path, "wb") as f:
                            f.write(image_bytes)
                        self.show_toast(f"Image saved!")
                        self.set_status(f"Saved to {path}")
                except Exception as e:
                    if "dismiss" not in str(e).lower():
                        self.show_toast(f"Save failed: {e}")
            
            dialog.save(self, None, _on_save_finish)
        except Exception as e:
            self.show_toast(f"Save error: {e}")
    
    def _show_old_image_gen_dialog(self):
        """Show image generation dialog with prompt input and generate button."""
        w = Gtk.Window(title="Generate Image with AI")
        w.set_transient_for(self)
        w.set_default_size(600, 450)
        
        vb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        vb.set_margin_top(12)
        vb.set_margin_bottom(12)
        vb.set_margin_start(12)
        vb.set_margin_end(12)

        # Title
        title = Gtk.Label()
        title.set_markup("<b>Generate Image with Flux AI</b>")
        title.set_halign(Gtk.Align.START)
        vb.append(title)

        # Prompt input (multiline)
        prompt_label = Gtk.Label(label="Prompt (describe the image):")
        prompt_label.set_halign(Gtk.Align.START)
        vb.append(prompt_label)
        
        scrolled_prompt = Gtk.ScrolledWindow()
        scrolled_prompt.set_size_request(-1, 100)
        prompt_text = Gtk.TextView()
        prompt_text.set_wrap_mode(Gtk.WrapMode.WORD)
        scrolled_prompt.set_child(prompt_text)
        vb.append(scrolled_prompt)

        # Settings row 1: Size
        size_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        size_row.append(Gtk.Label(label="Size:"))
        size_combo = Gtk.ComboBoxText()
        for size_option in ["1024x1024", "1024x768", "768x1024", "512x512"]:
            size_combo.append_text(size_option)
        size_combo.set_active(0)
        size_row.append(size_combo)
        
        # Model selection
        size_row.append(Gtk.Label(label="Model:"))
        model_combo = Gtk.ComboBoxText()
        for model_option in ["flux-schnell (fast)", "flux-dev (quality)", "sdxl-lightning"]:
            model_combo.append_text(model_option)
        model_combo.set_active(0)
        size_row.append(model_combo)
        vb.append(size_row)

        # Settings row 2: Steps
        steps_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        steps_row.append(Gtk.Label(label="Steps:"))
        steps_spin = Gtk.SpinButton()
        steps_spin.set_range(1, 50)
        steps_spin.set_increments(1, 5)
        steps_spin.set_value(4)
        steps_row.append(steps_spin)
        vb.append(steps_row)

        # Status label
        status_label = Gtk.Label(label="")
        vb.append(status_label)

        # Image preview placeholder
        image_preview = Gtk.Picture()
        image_preview.set_size_request(400, 400)
        image_preview.set_can_shrink(True)
        vb.append(image_preview)

        # Buttons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        gen_button = Gtk.Button(label="Generate")
        save_button = Gtk.Button(label="Save Image")
        save_button.set_sensitive(False)  # Disabled until image is generated
        close_button = Gtk.Button(label="Close")
        btn_box.append(gen_button)
        btn_box.append(save_button)
        btn_box.append(close_button)
        vb.append(btn_box)

        # Store generated image data
        generated_image_data = {"image_b64": None, "prompt": None}

        def _on_generate(_b):
            """Generate image using vision service."""
            try:
                status_label.set_text("Generating image...")
                gen_button.set_sensitive(False)
                
                # Get prompt
                buffer = prompt_text.get_buffer()
                prompt = buffer.get_text(
                    buffer.get_start_iter(),
                    buffer.get_end_iter(),
                    False
                )
                
                if not prompt.strip():
                    status_label.set_text("Error: Please enter a prompt")
                    gen_button.set_sensitive(True)
                    return
                
                # Get size
                size_text = size_combo.get_active_text() or "1024x1024"
                width, height = map(int, size_text.split("x"))
                
                # Get model
                model_text = model_combo.get_active_text() or "flux-schnell (fast)"
                model = model_text.split(" ")[0]  # Extract just the model name
                
                # Get steps
                steps = int(steps_spin.get_value())
                
                # Send generate command via on_command with special marker
                # We'll need to add handling for this in the main command handler
                cmd = f"/imagegen prompt=\"{prompt}\" width={width} height={height} model={model} steps={steps}"
                
                # Store prompt for save
                generated_image_data["prompt"] = prompt
                
                # Trigger generation (async via on_command)
                import threading
                def _generate_async():
                    try:
                        # Call the generation via NATS/REST
                        import httpx
                        import base64
                        from io import BytesIO
                        from gi.repository import GdkPixbuf, GLib
                        
                        # Start progress monitoring in a separate thread
                        progress_stop = threading.Event()
                        
                        def _monitor_progress():
                            """Monitor progress stream."""
                            try:
                                with httpx.stream("GET", "http://localhost:8005/v1/progress-stream", timeout=None) as stream:
                                    for line in stream.iter_lines():
                                        if progress_stop.is_set():
                                            break
                                        if line.startswith("data: "):
                                            msg = line[6:]  # Remove "data: " prefix
                                            def _update_status(message=msg):
                                                status_label.set_text(message)
                                                return False
                                            GLib.idle_add(_update_status)
                            except Exception:
                                pass
                        
                        progress_thread = threading.Thread(target=_monitor_progress, daemon=True)
                        progress_thread.start()
                        
                        try:
                            response = httpx.post(
                                "http://localhost:8005/v1/generate-image",
                                json={
                                    "prompt": prompt,
                                    "width": width,
                                    "height": height,
                                    "num_inference_steps": steps,
                                    "model": model,
                                },
                                timeout=600.0,  # 10 minutes timeout for first-time download
                            )
                            response.raise_for_status()
                            result = response.json()
                        finally:
                            # Stop progress monitoring
                            progress_stop.set()
                        
                        # Get image data
                        image_b64 = result.get("image_bytes_b64")
                        if image_b64:
                            # Store for save
                            generated_image_data["image_b64"] = image_b64
                            
                            # Decode and display
                            image_bytes = base64.b64decode(image_b64)
                            
                            # Load into pixbuf
                            loader = GdkPixbuf.PixbufLoader()
                            loader.write(image_bytes)
                            loader.close()
                            pixbuf = loader.get_pixbuf()
                            
                            # Update UI in main thread
                            def _update_ui():
                                try:
                                    from gi.repository import Gdk
                                    texture = Gdk.Texture.new_for_pixbuf(pixbuf)
                                    image_preview.set_paintable(texture)
                                    status_label.set_text("✓ Image generated successfully!")
                                    save_button.set_sensitive(True)
                                    gen_button.set_sensitive(True)
                                except Exception as e:
                                    status_label.set_text(f"Display error: {e}")
                                    gen_button.set_sensitive(True)
                                return False
                            GLib.idle_add(_update_ui)
                        else:
                            def _error():
                                status_label.set_text("Error: No image returned")
                                gen_button.set_sensitive(True)
                                return False
                            GLib.idle_add(_error)
                    except httpx.TimeoutException:
                        def _error():
                            status_label.set_text("Timeout: Generation took too long")
                            gen_button.set_sensitive(True)
                            return False
                        GLib.idle_add(_error)
                    except Exception as e:
                        def _error():
                            status_label.set_text(f"Generation failed: {str(e)}")
                            gen_button.set_sensitive(True)
                            return False
                        GLib.idle_add(_error)
                
                threading.Thread(target=_generate_async, daemon=True).start()
                
            except Exception as e:
                status_label.set_text(f"Error: {str(e)}")
                gen_button.set_sensitive(True)

        def _on_save(_b):
            """Save the generated image to disk."""
            try:
                if not generated_image_data.get("image_b64"):
                    status_label.set_text("No image to save")
                    return
                
                # Create save dialog
                from gi.repository import Gtk as _Gtk
                dialog = _Gtk.FileDialog()
                dialog.set_title("Save Generated Image")
                
                # Set default filename based on prompt
                import re
                from datetime import datetime
                prompt = generated_image_data.get("prompt", "image")
                safe_prompt = re.sub(r'[^\w\s-]', '', prompt)[:50]
                safe_prompt = re.sub(r'[-\s]+', '_', safe_prompt)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                default_name = f"{safe_prompt}_{timestamp}.png"
                dialog.set_initial_name(default_name)
                
                def _on_save_finish(dialog, result):
                    try:
                        file = dialog.save_finish(result)
                        if file:
                            path = file.get_path()
                            # Decode and save
                            import base64
                            image_bytes = base64.b64decode(generated_image_data["image_b64"])
                            with open(path, "wb") as f:
                                f.write(image_bytes)
                            status_label.set_text(f"Saved to {path}")
                            self.show_toast(f"Image saved!")
                    except Exception as e:
                        if "dismiss" not in str(e).lower():
                            status_label.set_text(f"Save failed: {str(e)}")
                
                dialog.save(w, None, _on_save_finish)
                
            except Exception as e:
                status_label.set_text(f"Save error: {str(e)}")

        def _on_close(_b):
            try:
                w.close()
            except Exception:
                pass

        try:
            gen_button.connect("clicked", _on_generate)
            save_button.connect("clicked", _on_save)
            close_button.connect("clicked", _on_close)
        except Exception:
            pass

        w.set_child(vb)
        try:
            w.present()
        except Exception:
            pass


class OverlayApplication(Gtk.Application):
    """GTK Application for the overlay."""
    
    def __init__(self, config: OverlayConfig, on_command: Callable[[str], None], message_bus=None):
        """Initialize the application."""
        super().__init__(application_id="com.neuralux.overlay")
        
        self.config = config
        self.on_command = on_command
        self.message_bus = message_bus
        self.window = None
    
    def do_activate(self):
        """Activate the application."""
        if not self.window:
            self.window = OverlayWindow(self, self.config, self.on_command, self.message_bus)
        
        self.window.present()

