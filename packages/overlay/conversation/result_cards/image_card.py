"""Image generation result card."""

import gi
gi.require_version('Gtk', '4.0')

from gi.repository import Gtk
from typing import Dict, Any

import structlog

logger = structlog.get_logger(__name__)


class ImageGenerationCard(Gtk.Box):
    """
    Display card for AI-generated images.
    
    Shows:
    - Generated image preview
    - Prompt used
    - Model and generation settings
    - Save, copy, and regenerate buttons
    """
    
    def __init__(self, image_result: Dict[str, Any]):
        """
        Initialize image generation card.
        
        Args:
            image_result: Dictionary with image generation details
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        
        self.image_result = image_result
        
        # Add CSS class
        self.add_css_class("action-card")
        self.add_css_class("image-card")
        self.add_css_class("action-success")
        
        # Set margins
        self.set_margin_start(12)
        self.set_margin_end(12)
        self.set_margin_top(4)
        self.set_margin_bottom(4)
        
        # Build UI
        self._build_ui()
    
    def _build_ui(self):
        """Build the image card UI."""
        # Card container
        card_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card_box.set_margin_top(8)
        card_box.set_margin_bottom(8)
        card_box.set_margin_start(12)
        card_box.set_margin_end(12)
        
        # Header
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        # Icon
        icon_label = Gtk.Label(label="🎨")
        header_box.append(icon_label)
        
        # Title
        title_label = Gtk.Label()
        title_label.set_markup("<b>Generated Image</b>")
        title_label.set_halign(Gtk.Align.START)
        title_label.set_hexpand(True)
        header_box.append(title_label)
        
        card_box.append(header_box)
        
        # Prompt
        prompt = self.image_result.get("prompt", "")
        if prompt:
            prompt_label = Gtk.Label()
            prompt_label.set_markup(f'<i>"{prompt}"</i>')
            prompt_label.set_wrap(True)
            prompt_label.set_xalign(0.0)
            prompt_label.set_margin_top(4)
            card_box.append(prompt_label)
        
        # Image preview
        image_path = self.image_result.get("image_path", "")
        if image_path:
            try:
                from gi.repository import GdkPixbuf, Gdk
                
                # Load image
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(image_path)
                
                # Scale to fit (max 400px height)
                orig_width = pixbuf.get_width()
                orig_height = pixbuf.get_height()
                
                max_height = 400
                if orig_height > max_height:
                    scale = max_height / orig_height
                    new_width = int(orig_width * scale)
                    new_height = max_height
                    pixbuf = pixbuf.scale_simple(
                        new_width, new_height, GdkPixbuf.InterpType.BILINEAR
                    )
                
                # Convert to texture
                texture = Gdk.Texture.new_for_pixbuf(pixbuf)
                
                # Create picture widget
                picture = Gtk.Picture()
                picture.set_paintable(texture)
                picture.set_size_request(pixbuf.get_width(), pixbuf.get_height())
                picture.set_halign(Gtk.Align.CENTER)
                picture.set_valign(Gtk.Align.CENTER)
                picture.set_can_shrink(False)
                picture.set_margin_top(8)
                picture.set_margin_bottom(8)
                card_box.append(picture)
                
                # Store texture for clipboard
                self._texture = texture
                
            except Exception as e:
                logger.error(f"Failed to load image: {e}")
                error_label = Gtk.Label(label=f"Image loaded but display failed: {e}")
                error_label.set_wrap(True)
                error_label.set_margin_top(8)
                card_box.append(error_label)
                self._texture = None
        
        # Settings info row
        settings_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        settings_box.set_margin_top(6)
        
        # Model
        model = self.image_result.get("model", "")
        if model:
            model_label = Gtk.Label(label=f"Model: {model}")
            model_label.set_opacity(0.6)
            settings_box.append(model_label)
        
        # Size
        width = self.image_result.get("width", 0)
        height = self.image_result.get("height", 0)
        if width and height:
            size_label = Gtk.Label(label=f"Size: {width}x{height}")
            size_label.set_opacity(0.6)
            settings_box.append(size_label)
        
        # Generation time
        gen_time = self.image_result.get("generation_time", 0)
        if gen_time > 0:
            time_label = Gtk.Label(label=f"Time: {gen_time:.1f}s")
            time_label.set_opacity(0.6)
            settings_box.append(time_label)
        
        card_box.append(settings_box)
        
        # Button row
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_box.set_margin_top(8)
        btn_box.set_halign(Gtk.Align.CENTER)
        
        # Save button
        save_btn = Gtk.Button(label="💾 Save")
        save_btn.set_tooltip_text("Save image to file")
        save_btn.connect("clicked", lambda _: self._save_image(image_path))
        btn_box.append(save_btn)
        
        # Copy button
        copy_btn = Gtk.Button(label="📋 Copy")
        copy_btn.set_tooltip_text("Copy image to clipboard")
        copy_btn.connect("clicked", lambda _: self._copy_image())
        btn_box.append(copy_btn)
        
        card_box.append(btn_box)
        
        self.append(card_box)
    
    def _save_image(self, image_path: str):
        """Save image with file dialog."""
        try:
            from gi.repository import Gtk as _Gtk
            import re
            from datetime import datetime
            
            dialog = _Gtk.FileDialog()
            dialog.set_title("Save Generated Image")
            
            # Generate filename
            prompt = self.image_result.get("prompt", "image")
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
                        # Copy file
                        import shutil
                        shutil.copy2(image_path, path)
                        logger.info(f"Image saved to {path}")
                except Exception as e:
                    if "dismiss" not in str(e).lower():
                        logger.error(f"Save failed: {e}")
            
            # Get root window
            root = self.get_root()
            dialog.save(root, None, _on_save_finish)
            
        except Exception as e:
            logger.error(f"Failed to save image: {e}")
    
    def _copy_image(self):
        """Copy image to clipboard."""
        try:
            from gi.repository import Gdk
            
            if hasattr(self, '_texture') and self._texture:
                display = Gdk.Display.get_default()
                clipboard = display.get_clipboard()
                clipboard.set_texture(self._texture)
                logger.info("Image copied to clipboard")
            else:
                logger.warning("No texture available to copy")
                
        except Exception as e:
            logger.error(f"Failed to copy image: {e}")

