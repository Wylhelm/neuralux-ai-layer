"""Result card for system command actions."""

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk
from typing import Dict, Any

class SystemCommandCard(Gtk.Box):
    """A card that displays the result of a system command."""
    
    def __init__(self, data: Dict[str, Any]):
        """
        Initialize the system command card.
        
        Args:
            data: Dictionary with system command results, expects keys like
                  'action', 'status', and 'processes' (for process lists).
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add_css_class("result-card")
        
        action = data.get("action", "Unknown Action")
        status = data.get("status", "Unknown Status")
        
        # Title
        title_label = Gtk.Label(label=f"System Command: {action}")
        title_label.set_halign(Gtk.Align.START)
        title_label.add_css_class("result-title")
        self.append(title_label)
        
        # Status
        status_label = Gtk.Label(label=f"Status: {status}")
        status_label.set_halign(Gtk.Align.START)
        self.append(status_label)
        
        # Process list (if available)
        if "processes" in data:
            processes = data["processes"]
            
            # Create a scrolled window for the process list
            scrolled = Gtk.ScrolledWindow()
            scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            scrolled.set_min_content_height(150)
            
            # Create a list view for the processes
            list_view = Gtk.ListView()
            
            # Create a model for the list view
            model = Gtk.StringList()
            for p in processes:
                model.append(f"{p.get('pid')}\t{p.get('username')}\t{p.get('cpu_percent'):.2f}%\t{p.get('memory_percent'):.2f}%\t{p.get('name')}")
            
            list_view.set_model(model)
            
            # Create a factory for the list view
            factory = Gtk.SignalListItemFactory()
            factory.connect("setup", self._setup_list_item)
            factory.connect("bind", self._bind_list_item)
            list_view.set_factory(factory)
            
            scrolled.set_child(list_view)
            self.append(scrolled)

    def _setup_list_item(self, factory, list_item):
        label = Gtk.Label()
        label.set_halign(Gtk.Align.START)
        list_item.set_child(label)

    def _bind_list_item(self, factory, list_item):
        label = list_item.get_child()
        label.set_label(list_item.get_item().get_string())
