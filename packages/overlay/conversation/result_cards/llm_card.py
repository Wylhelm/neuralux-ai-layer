"""LLM generation result card."""

import gi
gi.require_version('Gtk', '4.0')

from gi.repository import Gtk
from typing import Dict, Any

import structlog

logger = structlog.get_logger(__name__)


class LLMGenerationCard(Gtk.Box):
    """
    Display card for LLM-generated content.
    
    Shows:
    - Generated text
    - Token count / word count
    - Generation time
    - Copy and save buttons
    """
    
    def __init__(self, llm_result: Dict[str, Any]):
        """
        Initialize LLM generation card.
        
        Args:
            llm_result: Dictionary with LLM generation details
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        
        self.llm_result = llm_result
        
        # Add CSS class
        self.add_css_class("action-card")
        self.add_css_class("llm-card")
        self.add_css_class("action-success")
        
        # Set margins
        self.set_margin_start(12)
        self.set_margin_end(12)
        self.set_margin_top(4)
        self.set_margin_bottom(4)
        
        # Build UI
        self._build_ui()
    
    def _build_ui(self):
        """Build the LLM card UI."""
        # Card container
        card_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card_box.set_margin_top(8)
        card_box.set_margin_bottom(8)
        card_box.set_margin_start(12)
        card_box.set_margin_end(12)
        
        # Header
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        # Icon
        icon_label = Gtk.Label(label="🤖")
        header_box.append(icon_label)
        
        # Title
        title_label = Gtk.Label()
        title_label.set_markup("<b>Generated Content</b>")
        title_label.set_halign(Gtk.Align.START)
        title_label.set_hexpand(True)
        header_box.append(title_label)
        
        card_box.append(header_box)
        
        # Prompt (if available)
        prompt = self.llm_result.get("prompt", "")
        if prompt and len(prompt) < 200:
            prompt_label = Gtk.Label()
            prompt_label.set_markup(f'<i>Prompt: "{prompt}"</i>')
            prompt_label.set_wrap(True)
            prompt_label.set_xalign(0.0)
            prompt_label.set_opacity(0.7)
            prompt_label.set_margin_top(4)
            card_box.append(prompt_label)
        
        # Generated text (scrollable)
        text = self.llm_result.get("text", "")
        if text:
            scrolled = Gtk.ScrolledWindow()
            scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            scrolled.set_max_content_height(300)
            scrolled.set_propagate_natural_height(True)
            scrolled.set_margin_top(8)
            
            text_view = Gtk.TextView()
            text_view.set_editable(False)
            text_view.set_wrap_mode(Gtk.WrapMode.WORD)
            text_view.add_css_class("llm-text")
            
            buffer = text_view.get_buffer()
            buffer.set_text(text, -1)
            
            scrolled.set_child(text_view)
            card_box.append(scrolled)
        
        # Stats row
        stats_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        stats_box.set_margin_top(6)
        
        # Word count
        word_count = len(text.split())
        words_label = Gtk.Label(label=f"Words: {word_count}")
        words_label.set_opacity(0.6)
        stats_box.append(words_label)
        
        # Tokens (if available)
        tokens = self.llm_result.get("tokens", 0)
        if tokens > 0:
            tokens_label = Gtk.Label(label=f"Tokens: ~{tokens}")
            tokens_label.set_opacity(0.6)
            stats_box.append(tokens_label)
        
        # Generation time (if available)
        gen_time = self.llm_result.get("generation_time", 0)
        if gen_time > 0:
            time_label = Gtk.Label(label=f"Time: {gen_time:.1f}s")
            time_label.set_opacity(0.6)
            stats_box.append(time_label)
        
        card_box.append(stats_box)
        
        # Button row
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_box.set_margin_top(8)
        
        # Copy button
        copy_btn = Gtk.Button(label="📋 Copy")
        copy_btn.set_tooltip_text("Copy text to clipboard")
        copy_btn.connect("clicked", lambda _: self._copy_text(text))
        btn_box.append(copy_btn)
        
        # Save button
        save_btn = Gtk.Button(label="💾 Save")
        save_btn.set_tooltip_text("Save to file")
        save_btn.connect("clicked", lambda _: self._save_to_file(text))
        btn_box.append(save_btn)
        
        card_box.append(btn_box)
        
        self.append(card_box)
    
    def _copy_text(self, text: str):
        """Copy text to clipboard."""
        try:
            from gi.repository import Gdk
            
            display = Gdk.Display.get_default()
            clipboard = display.get_clipboard()
            clipboard.set(text)
            
            logger.info("Text copied to clipboard")
        except Exception as e:
            logger.error("Failed to copy text", error=str(e))
    
    def _save_to_file(self, text: str):
        """Save text to file."""
        try:
            from gi.repository import Gtk as _Gtk
            from datetime import datetime
            
            dialog = _Gtk.FileDialog()
            dialog.set_title("Save Generated Text")
            
            # Default filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dialog.set_initial_name(f"generated_{timestamp}.txt")
            
            def _on_save_finish(dialog, result):
                try:
                    file = dialog.save_finish(result)
                    if file:
                        path = file.get_path()
                        with open(path, "w") as f:
                            f.write(text)
                        logger.info(f"Text saved to {path}")
                except Exception as e:
                    if "dismiss" not in str(e).lower():
                        logger.error(f"Save failed: {e}")
            
            # Get root window
            root = self.get_root()
            dialog.save(root, None, _on_save_finish)
            
        except Exception as e:
            logger.error("Failed to save text", error=str(e))

