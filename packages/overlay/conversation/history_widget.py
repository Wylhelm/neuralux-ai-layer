"""Conversation history widget with scrollable message list."""

import gi
gi.require_version('Gtk', '4.0')

from gi.repository import Gtk, GLib
from typing import List, Dict, Any, Optional
from datetime import datetime

import structlog

from .message_bubble import MessageBubble, ActionResultCard

logger = structlog.get_logger(__name__)


class ConversationHistoryWidget(Gtk.Box):
    """
    Scrollable conversation history widget.
    
    Displays:
    - User and assistant message bubbles
    - Action result cards
    - Loading indicators
    - Empty state
    """
    
    def __init__(self):
        """Initialize conversation history widget."""
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        
        # Message storage
        self.messages = []
        
        # Add CSS class
        self.add_css_class("conversation-history")
        
        # Build UI
        self._build_ui()
    
    def _build_ui(self):
        """Build the history widget UI."""
        # Scrolled window for messages
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.add_css_class("conversation-scroller")
        
        # Messages container (vertical box)
        self.messages_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.messages_box.set_valign(Gtk.Align.START)
        scrolled.set_child(self.messages_box)
        
        self.append(scrolled)
        
        # Store scrolled window for auto-scroll
        self._scrolled = scrolled
        
        # Show empty state
        self._show_empty_state()
    
    def _show_empty_state(self):
        """Show empty state when no messages."""
        empty_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        empty_box.set_valign(Gtk.Align.CENTER)
        empty_box.set_halign(Gtk.Align.CENTER)
        empty_box.set_vexpand(True)
        
        # Icon
        icon_label = Gtk.Label(label="💬")
        icon_label.add_css_class("empty-icon")
        empty_box.append(icon_label)
        
        # Message
        msg_label = Gtk.Label(label="Start a conversation!")
        msg_label.add_css_class("empty-message")
        empty_box.append(msg_label)
        
        # Hint
        hint_label = Gtk.Label()
        hint_label.set_markup(
            '<span alpha="60%">Try: "create a file" or "generate an image"</span>'
        )
        hint_label.add_css_class("empty-hint")
        empty_box.append(hint_label)
        
        self._empty_state = empty_box
        self.messages_box.append(empty_box)
    
    def _remove_empty_state(self):
        """Remove empty state when adding first message."""
        if hasattr(self, '_empty_state') and self._empty_state:
            self.messages_box.remove(self._empty_state)
            self._empty_state = None
    
    def add_user_message(self, content: str, timestamp: Optional[float] = None):
        """
        Add a user message to the conversation.
        
        Args:
            content: Message content
            timestamp: Unix timestamp (defaults to now)
        """
        self._remove_empty_state()
        
        bubble = MessageBubble("user", content, timestamp)
        self.messages_box.append(bubble)
        self.messages.append({
            "role": "user",
            "content": content,
            "timestamp": timestamp or datetime.now().timestamp(),
        })
        
        # Auto-scroll to bottom
        self._scroll_to_bottom()
    
    def add_assistant_message(self, content: str, timestamp: Optional[float] = None):
        """
        Add an assistant message to the conversation.
        
        Args:
            content: Message content
            timestamp: Unix timestamp (defaults to now)
        """
        self._remove_empty_state()
        
        bubble = MessageBubble("assistant", content, timestamp)
        self.messages_box.append(bubble)
        self.messages.append({
            "role": "assistant",
            "content": content,
            "timestamp": timestamp or datetime.now().timestamp(),
        })
        
        # Auto-scroll to bottom
        self._scroll_to_bottom()
    
    def add_action_result(self, action_result: Dict[str, Any]):
        """
        Add an action result card to the conversation.
        
        Args:
            action_result: Action result dictionary
        """
        self._remove_empty_state()
        
        card = ActionResultCard(action_result)
        self.messages_box.append(card)
        
        # Auto-scroll to bottom
        self._scroll_to_bottom()
    
    def add_loading_indicator(self, message: str = "Thinking..."):
        """
        Add a loading indicator.
        
        Args:
            message: Loading message
            
        Returns:
            The loading indicator widget (for removal later)
        """
        self._remove_empty_state()
        
        loading_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        loading_box.set_halign(Gtk.Align.START)
        loading_box.set_margin_start(12)
        loading_box.set_margin_top(8)
        loading_box.add_css_class("loading-indicator")
        
        # Spinner
        spinner = Gtk.Spinner()
        spinner.set_spinning(True)
        loading_box.append(spinner)
        
        # Message
        label = Gtk.Label(label=message)
        label.set_opacity(0.7)
        loading_box.append(label)
        
        self.messages_box.append(loading_box)
        self._scroll_to_bottom()
        
        return loading_box
    
    def add_widget(self, widget):
        """Add a custom widget to the messages box."""
        try:
            self.messages_box.append(widget)
            self._scroll_to_bottom()
        except Exception as e:
            logger.error("Failed to add widget", error=str(e))
    
    def remove_widget(self, widget):
        """Remove a widget from the messages box."""
        try:
            self.messages_box.remove(widget)
        except Exception as e:
            logger.error("Failed to remove widget", error=str(e))
    
    def clear_history(self):
        """Clear all messages from the conversation."""
        # Remove all children
        child = self.messages_box.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.messages_box.remove(child)
            child = next_child
        
        self.messages.clear()
        self._show_empty_state()
    
    def load_history(self, turns: List[Dict[str, Any]]):
        """
        Load conversation history from turns.
        
        Args:
            turns: List of conversation turns
        """
        self.clear_history()
        
        for turn in turns:
            role = turn.get("role", "user")
            content = turn.get("content", "")
            timestamp = turn.get("timestamp", datetime.now().timestamp())
            
            if role == "user":
                self.add_user_message(content, timestamp)
            else:
                self.add_assistant_message(content, timestamp)
    
    def _scroll_to_bottom(self):
        """Scroll to the bottom of the conversation."""
        def _do_scroll():
            try:
                adj = self._scrolled.get_vadjustment()
                adj.set_value(adj.get_upper() - adj.get_page_size())
            except Exception as e:
                logger.error("Failed to scroll", error=str(e))
            return False
        
        # Delay scroll to ensure content is rendered
        GLib.timeout_add(50, _do_scroll)
    
    @property
    def has_messages(self) -> bool:
        """Check if there are any messages."""
        return len(self.messages) > 0

