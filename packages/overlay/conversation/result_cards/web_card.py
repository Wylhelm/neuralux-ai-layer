"""Web search result card."""

import gi
gi.require_version('Gtk', '4.0')

from gi.repository import Gtk
from typing import Dict, Any, List

import structlog

logger = structlog.get_logger(__name__)


class WebSearchCard(Gtk.Box):
    """
    Display card for web search results.
    
    Shows:
    - Search query
    - Number of results found
    - List of links with titles and snippets
    - Open in browser buttons
    - Copy URL buttons
    """
    
    def __init__(self, search_result: Dict[str, Any]):
        """
        Initialize web search card.
        
        Args:
            search_result: Dictionary with search results
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        
        self.search_result = search_result
        
        # Add CSS class
        self.add_css_class("action-card")
        self.add_css_class("web-card")
        self.add_css_class("action-success")
        
        # Set margins
        self.set_margin_start(12)
        self.set_margin_end(12)
        self.set_margin_top(4)
        self.set_margin_bottom(4)
        
        # Build UI
        self._build_ui()
    
    def _build_ui(self):
        """Build the web search card UI."""
        # Card container
        card_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card_box.set_margin_top(8)
        card_box.set_margin_bottom(8)
        card_box.set_margin_start(12)
        card_box.set_margin_end(12)
        
        # Header
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        # Icon
        icon_label = Gtk.Label(label="🌐")
        header_box.append(icon_label)
        
        # Title
        title_label = Gtk.Label()
        title_label.set_markup("<b>Web Search Results</b>")
        title_label.set_halign(Gtk.Align.START)
        title_label.set_hexpand(True)
        header_box.append(title_label)
        
        # Result count badge
        results = self.search_result.get("results", [])
        count_label = Gtk.Label(label=f"Found: {len(results)}")
        count_label.add_css_class("result-count-badge")
        header_box.append(count_label)
        
        card_box.append(header_box)
        
        # Query string
        query = self.search_result.get("query", "")
        if query:
            query_label = Gtk.Label()
            query_label.set_markup(f'<i>Query: "{query}"</i>')
            query_label.set_wrap(True)
            query_label.set_xalign(0.0)
            query_label.set_opacity(0.7)
            query_label.set_margin_top(4)
            card_box.append(query_label)
        
        # Results list (scrollable)
        if results:
            scrolled = Gtk.ScrolledWindow()
            scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            scrolled.set_max_content_height(300)
            scrolled.set_propagate_natural_height(True)
            scrolled.set_margin_top(8)
            
            results_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            
            for i, result in enumerate(results[:5], 1):  # Limit to top 5
                result_widget = self._create_result_item(i, result)
                results_box.append(result_widget)
            
            scrolled.set_child(results_box)
            card_box.append(scrolled)
            
            # Tip
            if len(results) > 0:
                tip_label = Gtk.Label()
                tip_label.set_markup(
                    '<span alpha="60%">💡 Say "open link 1" or click to open in browser</span>'
                )
                tip_label.set_margin_top(6)
                card_box.append(tip_label)
        else:
            # No results
            no_results_label = Gtk.Label(label="No results found")
            no_results_label.set_opacity(0.6)
            no_results_label.set_margin_top(12)
            no_results_label.set_margin_bottom(12)
            card_box.append(no_results_label)
        
        self.append(card_box)
    
    def _create_result_item(self, index: int, result: Dict[str, Any]) -> Gtk.Box:
        """Create a widget for a single search result."""
        result_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        result_box.add_css_class("web-result-item")
        result_box.set_margin_start(8)
        result_box.set_margin_end(8)
        result_box.set_margin_top(4)
        result_box.set_margin_bottom(4)
        
        # Header row
        header_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        # Index
        index_label = Gtk.Label(label=f"{index}.")
        index_label.add_css_class("result-index")
        header_row.append(index_label)
        
        # Title
        title = result.get("title", "No title")
        title_label = Gtk.Label()
        title_label.set_markup(f"<b>{title}</b>")
        title_label.set_halign(Gtk.Align.START)
        title_label.set_hexpand(True)
        title_label.set_ellipsize(True)
        title_label.set_wrap(True)
        title_label.set_max_width_chars(50)
        header_row.append(title_label)
        
        result_box.append(header_row)
        
        # URL
        url = result.get("url", "")
        if url:
            url_label = Gtk.Label()
            url_label.set_markup(f'<span font_family="monospace" size="small">{url}</span>')
            url_label.set_halign(Gtk.Align.START)
            url_label.set_ellipsize(True)
            url_label.set_opacity(0.7)
            url_label.set_margin_start(20)  # Indent
            result_box.append(url_label)
        
        # Snippet
        snippet = result.get("snippet", "") or result.get("description", "")
        if snippet:
            snippet_label = Gtk.Label(label=snippet[:200] + ("..." if len(snippet) > 200 else ""))
            snippet_label.set_wrap(True)
            snippet_label.set_xalign(0.0)
            snippet_label.set_opacity(0.8)
            snippet_label.set_margin_start(20)  # Indent
            snippet_label.set_margin_top(4)
            snippet_label.add_css_class("web-snippet")
            result_box.append(snippet_label)
        
        # Button row
        btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_row.set_margin_start(20)
        btn_row.set_margin_top(6)
        
        # Open button
        open_btn = Gtk.Button(label="🌐 Open")
        open_btn.add_css_class("web-open-btn")
        open_btn.connect("clicked", lambda _: self._open_url(url))
        btn_row.append(open_btn)
        
        # Copy URL button
        copy_btn = Gtk.Button(label="📋 Copy URL")
        copy_btn.connect("clicked", lambda _: self._copy_url(url))
        btn_row.append(copy_btn)
        
        result_box.append(btn_row)
        
        return result_box
    
    def _open_url(self, url: str):
        """Open URL in browser."""
        try:
            import webbrowser
            webbrowser.open(url)
            logger.info(f"Opening URL: {url}")
        except Exception as e:
            logger.error(f"Failed to open URL: {e}")
    
    def _copy_url(self, url: str):
        """Copy URL to clipboard."""
        try:
            from gi.repository import Gdk
            
            display = Gdk.Display.get_default()
            clipboard = display.get_clipboard()
            clipboard.set(url)
            
            logger.info(f"URL copied to clipboard: {url}")
        except Exception as e:
            logger.error(f"Failed to copy URL: {e}")

