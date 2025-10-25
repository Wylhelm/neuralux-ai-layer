"""GTK4-based overlay window."""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')

from gi.repository import Gtk, Gdk, GLib
from typing import Callable, Optional
import structlog

from config import OverlayConfig

logger = structlog.get_logger(__name__)


class OverlayWindow(Gtk.ApplicationWindow):
    """Main overlay window."""
    
    def __init__(self, app, config: OverlayConfig, on_command: Callable[[str], None]):
        """Initialize the overlay window."""
        super().__init__(application=app)
        
        self.config = config
        self.on_command = on_command
        
        # Window properties
        self.set_title("Neuralux")
        self.set_default_size(config.window_width, config.window_height)
        self.set_resizable(False)
        
        # Make it a dialog-like window (centered, always on top)
        self.set_decorated(False)  # No title bar
        
        # Setup UI
        self._setup_ui()
        
        # Setup CSS for styling
        self._setup_styling()
        
        # Connect signals
        self.connect("close-request", self._on_close_request)
        
        logger.info("Overlay window created")
    
    def _setup_ui(self):
        """Setup the user interface."""
        # Main container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
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
        
        self.set_child(main_box)
    
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
        
        listbox {
            background: transparent;
        }
        
        listbox row {
            background: #313244;
            color: #cdd6f4;
            border-radius: 6px;
            margin: 4px 0;
            padding: 10px;
        }
        
        listbox row:selected {
            background: #45475a;
        }
        
        listbox row:hover {
            background: #3e4051;
        }
        
        label {
            color: #cdd6f4;
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
            self.hide()
            entry.set_text("")
    
    def _on_entry_changed(self, entry):
        """Handle text changes in search entry."""
        text = entry.get_text()
        # TODO: Update results based on fuzzy search
        logger.debug("Search text changed", text=text)
    
    def _on_result_activated(self, list_box, row):
        """Handle selection of a result."""
        # TODO: Execute selected action
        logger.debug("Result activated", row_index=row.get_index())
        self.hide()
    
    def _on_close_request(self, window):
        """Handle window close request."""
        self.hide()
        return True  # Prevent destruction
    
    def toggle_visibility(self):
        """Toggle window visibility."""
        if self.is_visible():
            self.hide()
        else:
            self.show()
            self.present()
            self.search_entry.grab_focus()
    
    def add_result(self, title: str, subtitle: str = ""):
        """Add a result to the list."""
        row = Gtk.ListBoxRow()
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        
        title_label = Gtk.Label()
        title_label.set_markup(f"<b>{title}</b>")
        title_label.set_halign(Gtk.Align.START)
        box.append(title_label)
        
        if subtitle:
            subtitle_label = Gtk.Label()
            subtitle_label.set_markup(f"<span size='small' alpha='70%'>{subtitle}</span>")
            subtitle_label.set_halign(Gtk.Align.START)
            box.append(subtitle_label)
        
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
        self.status_label.set_markup(f"<span size='small' alpha='60%'>{text}</span>")


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

