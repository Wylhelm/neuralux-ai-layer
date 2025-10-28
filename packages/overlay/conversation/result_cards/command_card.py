"""Command output result card."""

import gi
gi.require_version('Gtk', '4.0')

from gi.repository import Gtk, Pango
from typing import Dict, Any

import structlog

logger = structlog.get_logger(__name__)


class CommandOutputCard(Gtk.Box):
    """
    Display card for command execution results.
    
    Shows:
    - Command that was executed
    - Exit code
    - Standard output
    - Standard error (if any)
    - Expandable/collapsible output
    - Copy button
    """
    
    def __init__(self, command_result: Dict[str, Any]):
        """
        Initialize command output card.
        
        Args:
            command_result: Dictionary with command execution details
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        
        self.command_result = command_result
        self._expanded = False
        
        # Add CSS class
        self.add_css_class("action-card")
        self.add_css_class("command-card")
        
        # Status-based styling
        exit_code = command_result.get("exit_code", 0)
        if exit_code == 0:
            self.add_css_class("action-success")
        else:
            self.add_css_class("action-failed")
        
        # Set margins
        self.set_margin_start(12)
        self.set_margin_end(12)
        self.set_margin_top(4)
        self.set_margin_bottom(4)
        
        # Build UI
        self._build_ui()
    
    def _build_ui(self):
        """Build the command card UI."""
        # Card container
        card_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card_box.set_margin_top(8)
        card_box.set_margin_bottom(8)
        card_box.set_margin_start(12)
        card_box.set_margin_end(12)
        
        # Header
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        # Icon
        icon_label = Gtk.Label(label="💻")
        header_box.append(icon_label)
        
        # Title
        title_label = Gtk.Label()
        title_label.set_markup("<b>Command Output</b>")
        title_label.set_halign(Gtk.Align.START)
        title_label.set_hexpand(True)
        header_box.append(title_label)
        
        # Exit code badge
        exit_code = self.command_result.get("exit_code", 0)
        badge_text = f"Exit: {exit_code}"
        badge_label = Gtk.Label(label=badge_text)
        badge_label.add_css_class("exit-code-badge")
        if exit_code == 0:
            badge_label.set_markup(f'<span color="#4CAF50">✓ {badge_text}</span>')
        else:
            badge_label.set_markup(f'<span color="#F44336">✗ {badge_text}</span>')
        header_box.append(badge_label)
        
        card_box.append(header_box)
        
        # Command line
        command = self.command_result.get("command", "")
        if command:
            cmd_label = Gtk.Label()
            cmd_label.set_markup(f'<span font_family="monospace">$ {command}</span>')
            cmd_label.set_wrap(True)
            cmd_label.set_xalign(0.0)
            cmd_label.set_selectable(True)
            cmd_label.set_margin_top(4)
            card_box.append(cmd_label)
        
        # Output section (expandable)
        stdout = self.command_result.get("stdout", "")
        stderr = self.command_result.get("stderr", "")
        
        if stdout or stderr:
            # Output preview/full view
            output_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            output_box.set_margin_top(8)
            
            # Create scrolled window for output
            scrolled = Gtk.ScrolledWindow()
            scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            scrolled.set_propagate_natural_height(True)
            scrolled.add_css_class("command-output-scroller")
            
            # Output text
            output_text = Gtk.TextView()
            output_text.set_editable(False)
            output_text.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
            output_text.set_monospace(True)
            output_text.add_css_class("command-output")
            
            # Set content
            buffer = output_text.get_buffer()
            if stdout:
                buffer.insert(buffer.get_end_iter(), stdout, -1)
            if stderr:
                if stdout:
                    buffer.insert(buffer.get_end_iter(), "\n--- stderr ---\n", -1)
                buffer.insert(buffer.get_end_iter(), stderr, -1)
            
            scrolled.set_child(output_text)
            output_box.append(scrolled)
            
            # Button row
            btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            btn_box.set_margin_top(4)
            
            # Copy button
            copy_btn = Gtk.Button(label="📋 Copy")
            copy_btn.set_tooltip_text("Copy output to clipboard")
            copy_btn.connect("clicked", lambda _: self._copy_output(stdout + stderr))
            btn_box.append(copy_btn)

            # Expand button
            expand_btn = Gtk.Button(label="⛶ Expand")
            expand_btn.set_tooltip_text("Open full output in a window")
            expand_btn.connect("clicked", lambda _: self._show_full_output(stdout, stderr))
            btn_box.append(expand_btn)
            
            output_box.append(btn_box)
            card_box.append(output_box)
        
        self.append(card_box)
    
    def _copy_output(self, text: str):
        """Copy output to clipboard."""
        try:
            from gi.repository import Gdk
            
            display = Gdk.Display.get_default()
            clipboard = display.get_clipboard()
            clipboard.set(text)
            
            logger.info("Output copied to clipboard")
        except Exception as e:
            logger.error("Failed to copy output", error=str(e))

    def _show_full_output(self, stdout: str, stderr: str):
        """Show the full command output in a resizable window."""
        try:
            # Build text content
            content = stdout or ""
            if stderr:
                if content:
                    content += "\n--- stderr ---\n"
                content += stderr

            # Create window
            window = Gtk.Window()
            window.set_title("Command Output")
            window.set_default_size(1100, 800)
            window.set_modal(True)
            try:
                window.maximize()
            except Exception:
                pass

            root = self.get_root()
            if root and hasattr(window, 'set_transient_for'):
                try:
                    window.set_transient_for(root)
                except Exception:
                    pass

            # Scrolled text view
            scrolled = Gtk.ScrolledWindow()
            scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
            scrolled.set_hexpand(True)
            scrolled.set_vexpand(True)
            text_view = Gtk.TextView()
            text_view.set_editable(False)
            text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
            text_view.set_monospace(True)
            text_view.add_css_class("command-output")
            buffer = text_view.get_buffer()
            buffer.insert(buffer.get_end_iter(), content, -1)
            scrolled.set_child(text_view)

            # Buttons row
            btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            btn_box.set_margin_top(6)
            btn_box.set_margin_bottom(6)
            btn_box.set_margin_start(6)
            btn_box.set_margin_end(6)

            copy_btn = Gtk.Button(label="📋 Copy")
            copy_btn.connect("clicked", lambda *_: self._copy_output(content))
            btn_box.append(copy_btn)

            close_btn = Gtk.Button(label="✕ Close")
            close_btn.connect("clicked", lambda *_: window.close())
            btn_box.append(close_btn)

            # Container
            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            vbox.set_margin_top(8)
            vbox.set_margin_bottom(8)
            vbox.set_margin_start(8)
            vbox.set_margin_end(8)
            vbox.append(scrolled)
            vbox.append(btn_box)

            window.set_child(vbox)
            window.present()
        except Exception as e:
            logger.error("Failed to show full output", error=str(e))

