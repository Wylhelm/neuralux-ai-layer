"""Action approval dialog component."""

import gi
gi.require_version('Gtk', '4.0')

from gi.repository import Gtk
from typing import List, Dict, Any, Callable, Optional

import structlog

logger = structlog.get_logger(__name__)


class ActionApprovalDialog(Gtk.Window):
    """
    Modal dialog for approving planned actions.
    
    Shows:
    - List of planned actions
    - Which actions need approval
    - Action parameters and details
    - Approve/Cancel buttons
    """
    
    def __init__(
        self,
        parent: Gtk.Window,
        actions: List[Dict[str, Any]],
        message: str = "The AI wants to perform these actions:",
        on_approve: Optional[Callable] = None,
        on_cancel: Optional[Callable] = None,
    ):
        """
        Initialize approval dialog.
        
        Args:
            parent: Parent window
            actions: List of action dictionaries
            message: Explanation message
            on_approve: Callback when approved
            on_cancel: Callback when cancelled
        """
        super().__init__()
        
        self.actions = actions
        self.on_approve = on_approve
        self.on_cancel = on_cancel
        
        # Window settings
        self.set_title("Action Approval")
        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_default_size(600, 500)
        
        # Add CSS class
        self.add_css_class("approval-dialog")
        
        # Build UI
        self._build_ui(message)
        
        # Connect signals
        self.connect("close-request", self._on_close_request)
    
    def _build_ui(self, message: str):
        """Build the approval dialog UI."""
        # Main container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        main_box.set_margin_top(16)
        main_box.set_margin_bottom(16)
        main_box.set_margin_start(16)
        main_box.set_margin_end(16)
        
        # Title with icon
        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        title_icon = Gtk.Label(label="🤖")
        title_icon.add_css_class("approval-icon")
        title_box.append(title_icon)
        
        title_label = Gtk.Label()
        title_label.set_markup("<b>Approval Required</b>")
        title_label.set_halign(Gtk.Align.START)
        title_label.add_css_class("approval-title")
        title_box.append(title_label)
        
        main_box.append(title_box)
        
        # Explanation message
        msg_label = Gtk.Label(label=message)
        msg_label.set_wrap(True)
        msg_label.set_xalign(0.0)
        msg_label.set_margin_bottom(8)
        main_box.append(msg_label)
        
        # Scrolled window for actions
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        
        # Actions list
        actions_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        actions_box.set_margin_top(8)
        actions_box.set_margin_bottom(8)
        actions_box.add_css_class("approval-actions-list")
        
        # Count actions needing approval
        approval_count = 0
        
        for i, action in enumerate(self.actions, 1):
            action_widget = self._create_action_widget(i, action)
            actions_box.append(action_widget)
            
            if action.get("needs_approval", False):
                approval_count += 1
        
        scrolled.set_child(actions_box)
        main_box.append(scrolled)
        
        # Warning if destructive actions
        if approval_count > 0:
            warning_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            warning_box.add_css_class("approval-warning")
            
            warning_icon = Gtk.Label(label="⚠️")
            warning_box.append(warning_icon)
            
            warning_label = Gtk.Label()
            warning_label.set_markup(
                f"<b>{approval_count}</b> action(s) marked 🔒 will modify your system"
            )
            warning_label.set_wrap(True)
            warning_label.set_xalign(0.0)
            warning_box.append(warning_label)
            
            main_box.append(warning_box)
        
        # Button box
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_box.set_halign(Gtk.Align.END)
        btn_box.set_margin_top(8)
        
        # Cancel button
        cancel_btn = Gtk.Button(label="✗ Cancel")
        cancel_btn.connect("clicked", self._on_cancel_clicked)
        cancel_btn.add_css_class("cancel")
        btn_box.append(cancel_btn)
        
        # Approve button
        approve_btn = Gtk.Button(label="✓ Approve All")
        approve_btn.connect("clicked", self._on_approve_clicked)
        approve_btn.add_css_class("approve")
        btn_box.append(approve_btn)
        
        main_box.append(btn_box)
        
        self.set_child(main_box)
    
    def _create_action_widget(self, index: int, action: Dict[str, Any]) -> Gtk.Box:
        """
        Create a widget for displaying an action.
        
        Args:
            index: Action index (1-based)
            action: Action dictionary
            
        Returns:
            Widget for the action
        """
        action_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        action_box.add_css_class("approval-action-item")
        
        needs_approval = action.get("needs_approval", False)
        if needs_approval:
            action_box.add_css_class("approval-action-needs-approval")
        else:
            action_box.add_css_class("approval-action-auto")
        
        # Header with index and type
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        # Checkbox icon
        checkbox = Gtk.Label(label="☑")
        checkbox.add_css_class("action-checkbox")
        header_box.append(checkbox)
        
        # Index
        index_label = Gtk.Label(label=f"{index}.")
        index_label.add_css_class("action-index")
        header_box.append(index_label)
        
        # Action type
        action_type = action.get("action_type", "unknown")
        type_label = Gtk.Label()
        type_label.set_markup(f"<b>{action_type}</b>")
        type_label.set_halign(Gtk.Align.START)
        type_label.set_hexpand(True)
        header_box.append(type_label)
        
        # Approval badge
        badge = "🔒" if needs_approval else "✅"
        badge_label = Gtk.Label(label=badge)
        header_box.append(badge_label)
        
        action_box.append(header_box)
        
        # Status text
        status_text = "Requires approval" if needs_approval else "No approval needed"
        status_label = Gtk.Label(label=status_text)
        status_label.set_halign(Gtk.Align.START)
        status_label.set_opacity(0.7)
        status_label.set_margin_start(32)  # Indent under checkbox
        action_box.append(status_label)
        
        # Description
        description = action.get("description", "")
        if description:
            desc_label = Gtk.Label(label=description)
            desc_label.set_wrap(True)
            desc_label.set_xalign(0.0)
            desc_label.set_margin_start(32)
            desc_label.set_margin_top(4)
            action_box.append(desc_label)
        
        # Parameters (collapsed by default, can expand)
        params = action.get("params", {})
        if params and len(params) > 0:
            params_str = ", ".join(f"{k}={v}" for k, v in list(params.items())[:3])
            if len(params) > 3:
                params_str += f" (+{len(params) - 3} more)"
            
            params_label = Gtk.Label()
            params_label.set_markup(f'<span font_family="monospace" size="small">{params_str}</span>')
            params_label.set_wrap(True)
            params_label.set_xalign(0.0)
            params_label.set_margin_start(32)
            params_label.set_margin_top(2)
            params_label.set_opacity(0.6)
            action_box.append(params_label)
        
        return action_box
    
    def _on_approve_clicked(self, button):
        """Handle approve button click."""
        if self.on_approve:
            self.on_approve()
        self.close()
    
    def _on_cancel_clicked(self, button):
        """Handle cancel button click."""
        if self.on_cancel:
            self.on_cancel()
        self.close()
    
    def _on_close_request(self, window):
        """Handle window close request."""
        if self.on_cancel:
            self.on_cancel()
        return False  # Allow close

