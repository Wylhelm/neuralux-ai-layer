import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gst', '1.0')
from gi.repository import Gtk, Gst
from typing import Dict, Any
import structlog

logger = structlog.get_logger(__name__)

class MusicCard(Gtk.Box):
    """Card for displaying music generation results."""
    def __init__(self, result: Dict[str, Any]):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.result = result
        self.player = Gst.ElementFactory.make("playbin", "player")
        
        self.add_css_class("action-card")
        self.add_css_class("music-card")
        self.set_margin_start(12)
        self.set_margin_end(12)
        self.set_margin_top(4)
        self.set_margin_bottom(4)
        
        self._build_ui()

    def _build_ui(self):
        card_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card_box.set_margin_top(8)
        card_box.set_margin_bottom(8)
        card_box.set_margin_start(12)
        card_box.set_margin_end(12)

        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        icon_label = Gtk.Label(label="🎵")
        header_box.append(icon_label)
        title_label = Gtk.Label()
        title_label.set_markup("<b>Generated Music</b>")
        title_label.set_halign(Gtk.Align.START)
        header_box.append(title_label)
        card_box.append(header_box)

        prompt = self.result.get("prompt", "Music")
        file_path = self.result.get("file_path", "")

        prompt_label = Gtk.Label()
        prompt_label.set_markup(f'<i>"{prompt}"</i>')
        prompt_label.set_wrap(True)
        prompt_label.set_xalign(0.0)
        card_box.append(prompt_label)

        path_label = Gtk.Label(label=f"Saved to: {file_path}")
        path_label.set_wrap(True)
        path_label.set_xalign(0.0)
        card_box.append(path_label)

        controls_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        controls_box.set_halign(Gtk.Align.CENTER)
        
        play_button = Gtk.Button(label="▶ Play")
        play_button.connect("clicked", self.play_music)
        controls_box.append(play_button)

        pause_button = Gtk.Button(label="⏸ Pause")
        pause_button.connect("clicked", self.pause_music)
        controls_box.append(pause_button)

        stop_button = Gtk.Button(label="⏹ Stop")
        stop_button.connect("clicked", self.stop_music)
        controls_box.append(stop_button)
        
        card_box.append(controls_box)
        self.append(card_box)

        if file_path:
            self.player.set_property("uri", f"file://{file_path}")

    def play_music(self, widget):
        self.player.set_state(Gst.State.PLAYING)

    def pause_music(self, widget):
        self.player.set_state(Gst.State.PAUSED)

    def stop_music(self, widget):
        self.player.set_state(Gst.State.NULL)
