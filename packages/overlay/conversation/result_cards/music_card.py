import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gst', '1.0')
from gi.repository import Gtk, Gst, GLib
from typing import Dict, Any
from pathlib import Path
import structlog
import os

logger = structlog.get_logger(__name__)

class MusicCard(Gtk.Box):
    """Card for displaying music generation results with playback controls."""
    
    def __init__(self, result: Dict[str, Any]):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.result = result
        
        # Initialize GStreamer
        Gst.init(None)
        self.player = Gst.ElementFactory.make("playbin", "player")
        if not self.player:
            logger.error("Failed to create GStreamer playbin")
        
        # Player state
        self.is_playing = False
        self.is_paused = False
        
        # Get file path from result (handles both music_generate and music_save)
        # Check multiple possible locations where the file path might be stored
        details = result.get("details", {}) or {}
        self.file_path = (
            result.get("file_path") or 
            result.get("saved_path") or 
            details.get("file_path") or
            details.get("saved_path") or
            details.get("original_path") or  # Fallback to original_path
            ""
        )
        
        self.add_css_class("action-card")
        self.add_css_class("music-card")
        self.add_css_class("action-success")
        self.set_margin_start(12)
        self.set_margin_end(12)
        self.set_margin_top(4)
        self.set_margin_bottom(4)
        
        self._build_ui()
        
        # Set up audio file if available
        if self.file_path and os.path.exists(self.file_path):
            uri = f"file://{os.path.abspath(self.file_path)}"
            self.player.set_property("uri", uri)
            logger.info("Music file loaded", path=self.file_path, uri=uri)

    def _build_ui(self):
        """Build the music card UI with playback controls."""
        card_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card_box.set_margin_top(8)
        card_box.set_margin_bottom(8)
        card_box.set_margin_start(12)
        card_box.set_margin_end(12)

        # Header
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        icon_label = Gtk.Label(label="🎵")
        header_box.append(icon_label)
        title_label = Gtk.Label()
        title_label.set_markup("<b>Generated Music</b>")
        title_label.set_halign(Gtk.Align.START)
        title_label.set_hexpand(True)
        header_box.append(title_label)
        card_box.append(header_box)

        # Prompt (if available)
        prompt = self.result.get("prompt", "")
        if not prompt:
            prompt = self.result.get("details", {}).get("prompt", "")
        
        if prompt:
            prompt_label = Gtk.Label()
            prompt_label.set_markup(f'<i>"{prompt}"</i>')
            prompt_label.set_wrap(True)
            prompt_label.set_xalign(0.0)
            prompt_label.set_margin_top(4)
            card_box.append(prompt_label)

        # File path (if available)
        if self.file_path:
            from pathlib import Path
            file_name = Path(self.file_path).name
            path_label = Gtk.Label()
            path_label.set_markup(f'<span size="small" opacity="0.7">📁 {file_name}</span>')
            path_label.set_wrap(True)
            path_label.set_xalign(0.0)
            path_label.set_margin_top(4)
            card_box.append(path_label)

        # Playback controls
        controls_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        controls_box.set_halign(Gtk.Align.CENTER)
        controls_box.set_margin_top(12)
        
        # Play/Pause button (toggles)
        self.play_pause_button = Gtk.Button(label="▶ Play")
        self.play_pause_button.connect("clicked", self._toggle_play_pause)
        self.play_pause_button.set_tooltip_text("Play or pause audio")
        controls_box.append(self.play_pause_button)

        # Stop button
        stop_button = Gtk.Button(label="⏹ Stop")
        stop_button.connect("clicked", self._stop_music)
        stop_button.set_tooltip_text("Stop audio")
        controls_box.append(stop_button)
        
        # Open file button
        open_button = Gtk.Button(label="📂 Open")
        open_button.connect("clicked", self._open_file)
        open_button.set_tooltip_text("Open file location")
        controls_box.append(open_button)
        
        card_box.append(controls_box)
        self.append(card_box)

    def _toggle_play_pause(self, widget):
        """Toggle between play and pause."""
        if not self.file_path or not os.path.exists(self.file_path):
            logger.warning("Music file not available", path=self.file_path)
            return
        
        try:
            if self.is_playing:
                # Currently playing - pause it
                ret = self.player.set_state(Gst.State.PAUSED)
                if ret == Gst.StateChangeReturn.SUCCESS:
                    self.is_playing = False
                    self.is_paused = True
                    self.play_pause_button.set_label("▶ Play")
                    logger.info("Music paused")
            else:
                # Not playing - start playing
                ret = self.player.set_state(Gst.State.PLAYING)
                if ret == Gst.StateChangeReturn.SUCCESS:
                    self.is_playing = True
                    self.is_paused = False
                    self.play_pause_button.set_label("⏸ Pause")
                    logger.info("Music playing", path=self.file_path)
                else:
                    logger.error("Failed to start playback", state_change=ret)
        except Exception as e:
            logger.error("Error toggling play/pause", error=str(e))

    def _stop_music(self, widget):
        """Stop the music playback."""
        try:
            ret = self.player.set_state(Gst.State.NULL)
            if ret == Gst.StateChangeReturn.SUCCESS:
                self.is_playing = False
                self.is_paused = False
                self.play_pause_button.set_label("▶ Play")
                logger.info("Music stopped")
        except Exception as e:
            logger.error("Error stopping music", error=str(e))

    def _open_file(self, widget):
        """Open the file location in file manager."""
        try:
            import subprocess
            if self.file_path:
                file_dir = os.path.dirname(self.file_path)
                # Use xdg-open to open the directory
                subprocess.Popen(["xdg-open", file_dir])
                logger.info("Opened file location", path=file_dir)
        except Exception as e:
            logger.error("Error opening file location", error=str(e))
