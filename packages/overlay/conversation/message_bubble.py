"""Message bubble component for conversation display."""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('GdkPixbuf', '2.0')

from gi.repository import Gtk, Pango, GdkPixbuf
from datetime import datetime
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)


class MessageBubble(Gtk.Box):
    """
    A message bubble widget for displaying user or assistant messages.
    
    Features:
    - Visual distinction between user and assistant
    - Timestamp display
    - Markdown-like formatting support
    - Copy button
    - Selectable text
    """
    
    def __init__(self, role: str, content: str, timestamp: Optional[float] = None):
        """
        Initialize a message bubble.
        
        Args:
            role: "user" or "assistant"
            content: Message content
            timestamp: Unix timestamp (defaults to now)
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        
        self.role = role
        self.content = content
        self.timestamp = timestamp or datetime.now().timestamp()
        
        # Add CSS classes for styling
        self.add_css_class("message-bubble")
        self.add_css_class(f"message-{role}")
        
        # Set alignment based on role
        if role == "user":
            self.set_halign(Gtk.Align.END)
        else:
            self.set_halign(Gtk.Align.START)
        
        # Set maximum width (60% of parent)
        self.set_hexpand(False)
        self.set_size_request(350, -1)  # Min width 350px
        self.set_margin_start(12)
        self.set_margin_end(12)
        self.set_margin_top(4)
        self.set_margin_bottom(4)
        
        # Build UI
        self._build_ui()
    
    def _build_ui(self):
        """Build the message bubble UI."""
        # Main content box
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        content_box.set_margin_top(8)
        content_box.set_margin_bottom(8)
        content_box.set_margin_start(12)
        content_box.set_margin_end(12)
        
        # Header with role indicator and timestamp
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        # Role label
        role_label = Gtk.Label()
        role_text = "You" if self.role == "user" else "AI"
        role_label.set_markup(f"<b>{role_text}</b>")
        role_label.set_halign(Gtk.Align.START)
        role_label.set_opacity(0.7)
        header_box.append(role_label)
        
        # Spacer
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        header_box.append(spacer)
        
        # Timestamp
        time_str = datetime.fromtimestamp(self.timestamp).strftime("%H:%M")
        time_label = Gtk.Label(label=time_str)
        time_label.set_halign(Gtk.Align.END)
        time_label.set_opacity(0.5)
        time_label.add_css_class("timestamp")
        header_box.append(time_label)
        
        content_box.append(header_box)
        
        # Message content
        content_label = Gtk.Label()
        content_label.set_text(self.content)
        content_label.set_wrap(True)
        content_label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        content_label.set_xalign(0.0)
        content_label.set_selectable(True)
        content_label.set_can_focus(False)  # Don't steal focus when selecting
        content_label.add_css_class("message-content")
        content_box.append(content_label)
        
        # Copy button (small, in corner)
        if len(self.content) > 20:  # Only show for longer messages
            copy_btn = Gtk.Button(label="📋")
            copy_btn.set_tooltip_text("Copy message")
            copy_btn.add_css_class("copy-button")
            copy_btn.connect("clicked", self._on_copy_clicked)
            copy_btn.set_halign(Gtk.Align.END)
            content_box.append(copy_btn)
        
        self.append(content_box)
    
    def _on_copy_clicked(self, button):
        """Handle copy button click."""
        try:
            from gi.repository import Gdk
            
            display = Gdk.Display.get_default()
            clipboard = display.get_clipboard()
            clipboard.set(self.content)
            
            # Visual feedback
            button.set_label("✓")
            from gi.repository import GLib
            def _reset():
                button.set_label("📋")
                return False
            GLib.timeout_add(1000, _reset)
            
        except Exception as e:
            logger.error("Failed to copy to clipboard", error=str(e))


class ActionResultCard(Gtk.Box):
    """
    Display card for an action result.
    
    Shows details about an executed action including:
    - Action type and description
    - Status (success/failure)
    - Result details
    - Quick actions (open, copy, etc.)
    """
    
    def __init__(self, action_result: dict):
        """
        Initialize action result card.
        
        Args:
            action_result: Dictionary with action details
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        
        self.action_result = action_result
        
        # Add CSS class
        self.add_css_class("action-card")
        
        # Status-based styling
        success = action_result.get("success", True)
        self.add_css_class("action-success" if success else "action-failed")
        
        # Set margins - Ultra Compact
        self.set_margin_start(6)
        self.set_margin_end(6)
        self.set_margin_top(2)
        self.set_margin_bottom(2)
        
        # Build UI
        self._build_ui()
    
    def _build_ui(self):
        """Build the action card UI."""
        # Card container
        card_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        card_box.set_margin_top(4)
        card_box.set_margin_bottom(4)
        card_box.set_margin_start(6)
        card_box.set_margin_end(6)
        
        # Header with icon and action type
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        
        # Status icon
        success = self.action_result.get("success", True)
        icon = "✅" if success else "❌"
        icon_label = Gtk.Label(label=icon)
        header_box.append(icon_label)
        
        # Action type/description
        action_type = self.action_result.get("action_type", "Action")
        description = self.action_result.get("description", "")
        title_label = Gtk.Label()
        title_label.set_markup(f"<b>{action_type}</b>")
        title_label.set_halign(Gtk.Align.START)
        title_label.set_hexpand(True)
        header_box.append(title_label)
        
        card_box.append(header_box)
        
        # Description if available
        if description:
            desc_label = Gtk.Label(label=description)
            desc_label.set_wrap(True)
            desc_label.set_xalign(0.0)
            desc_label.set_opacity(0.8)
            card_box.append(desc_label)
        
        # Result details (expandable) - check both 'details' and 'result' keys
        result_data = self.action_result.get("details", self.action_result.get("result", {}))
        
        # Format the result based on type
        if result_data:
            # Handle different result types
            if isinstance(result_data, dict):
                # For command output - extract stdout properly
                output_text = None
                if "stdout" in result_data:
                    output_text = result_data.get("stdout", "")
                elif "output" in result_data:
                    output_text = result_data.get("output", "")
                
                if output_text:
                    # Create scrollable text view for long output
                    scrolled = Gtk.ScrolledWindow()
                    scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
                    scrolled.set_min_content_height(100)   # Show at least 100px
                    scrolled.set_max_content_height(500)   # Much larger! Up to 500px
                    scrolled.set_propagate_natural_height(True)
                    scrolled.set_vexpand(False)
                    
                    text_view = Gtk.TextView()
                    text_view.set_editable(False)
                    text_view.set_cursor_visible(False)
                    text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
                    text_view.set_left_margin(6)
                    text_view.set_right_margin(6)
                    text_view.set_top_margin(4)
                    text_view.set_bottom_margin(4)
                    text_view.get_buffer().set_text(output_text)  # Show full output!
                    text_view.add_css_class("action-details")
                    
                    scrolled.set_child(text_view)
                    card_box.append(scrolled)
                
                # For image generation - larger preview
                elif "image_path" in result_data:
                    image_path = result_data.get("image_path", "")
                    img_label = Gtk.Label(label=f"📷 Image: {image_path}")
                    img_label.set_xalign(0.0)
                    img_label.set_selectable(True)
                    card_box.append(img_label)
                    
                    # Try to show the image preview - larger size
                    try:
                        from pathlib import Path
                        if Path(image_path).exists():
                            # Get window width to scale appropriately
                            # Use 400x400 max, but preserve aspect ratio
                            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                                image_path,
                                width=400,
                                height=400,
                                preserve_aspect_ratio=True
                            )
                            image_widget = Gtk.Image.new_from_pixbuf(pixbuf)
                            image_widget.set_margin_top(6)
                            image_widget.set_margin_bottom(6)
                            
                            # Add a frame around the image
                            frame = Gtk.Frame()
                            frame.set_child(image_widget)
                            frame.add_css_class("image-preview")
                            card_box.append(frame)
                    except Exception as e:
                        logger.debug(f"Could not load image preview: {e}")
                
                # For LLM generation - show more content
                elif "content" in result_data:
                    content = result_data.get("content", "")
                    if content:
                        # Use scrollable for long content
                        if len(content) > 500:
                            scrolled = Gtk.ScrolledWindow()
                            scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
                            scrolled.set_min_content_height(80)
                            scrolled.set_max_content_height(400)  # Larger for LLM content
                            scrolled.set_propagate_natural_height(True)
                            scrolled.set_vexpand(False)
                            
                            text_view = Gtk.TextView()
                            text_view.set_editable(False)
                            text_view.set_cursor_visible(False)
                            text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
                            text_view.set_left_margin(6)
                            text_view.set_right_margin(6)
                            text_view.set_top_margin(4)
                            text_view.set_bottom_margin(4)
                            text_view.get_buffer().set_text(content)
                            text_view.add_css_class("action-details")
                            
                            scrolled.set_child(text_view)
                            card_box.append(scrolled)
                        else:
                            # Short content, just show as label
                            details_label = Gtk.Label()
                            details_label.set_text(content)
                            details_label.set_wrap(True)
                            details_label.set_xalign(0.0)
                            details_label.set_selectable(True)
                            details_label.add_css_class("action-details")
                            card_box.append(details_label)
                
                # Generic dict display - but DON'T show if it's command output
                elif "command" not in result_data:
                    # Only show dict if it's not a command result
                    details_label = Gtk.Label()
                    details_label.set_text(str(result_data)[:200])
                    details_label.set_wrap(True)
                    details_label.set_xalign(0.0)
                    details_label.set_selectable(True)
                    details_label.add_css_class("action-details")
                    card_box.append(details_label)
            else:
                # Non-dict result
                details_label = Gtk.Label()
                details_label.set_text(str(result_data)[:200])
                details_label.set_wrap(True)
                details_label.set_xalign(0.0)
                details_label.set_selectable(True)
                details_label.add_css_class("action-details")
                card_box.append(details_label)
        
        # Show error if present
        error = self.action_result.get("error")
        if error:
            error_label = Gtk.Label(label=f"❌ Error: {error}")
            error_label.set_wrap(True)
            error_label.set_xalign(0.0)
            error_label.add_css_class("action-details")
            error_label.set_opacity(0.9)
            card_box.append(error_label)
        
        self.append(card_box)

