"""Document query result card."""

import gi
gi.require_version('Gtk', '4.0')

from gi.repository import Gtk
from typing import Dict, Any, List

import structlog

logger = structlog.get_logger(__name__)


class DocumentQueryCard(Gtk.Box):
    """
    Display card for document query results.
    
    Shows:
    - Query string
    - Number of results found
    - List of documents with relevance scores
    - Preview/snippet for each
    - Open/copy path buttons
    """
    
    def __init__(self, query_result: Dict[str, Any]):
        """
        Initialize document query card.
        
        Args:
            query_result: Dictionary with query results
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        
        self.query_result = query_result
        
        # Add CSS class
        self.add_css_class("action-card")
        self.add_css_class("document-card")
        self.add_css_class("action-success")
        
        # Set margins
        self.set_margin_start(12)
        self.set_margin_end(12)
        self.set_margin_top(4)
        self.set_margin_bottom(4)
        
        # Build UI
        self._build_ui()
    
    def _build_ui(self):
        """Build the document card UI."""
        # Card container
        card_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card_box.set_margin_top(8)
        card_box.set_margin_bottom(8)
        card_box.set_margin_start(12)
        card_box.set_margin_end(12)
        
        # Header
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        # Icon
        icon_label = Gtk.Label(label="📚")
        header_box.append(icon_label)
        
        # Title
        title_label = Gtk.Label()
        query = self.query_result.get("query", "")
        title_label.set_markup(f"<b>Document Query Results</b>")
        title_label.set_halign(Gtk.Align.START)
        title_label.set_hexpand(True)
        header_box.append(title_label)
        
        # Result count badge
        documents = self.query_result.get("documents", [])
        count_label = Gtk.Label(label=f"Found: {len(documents)}")
        count_label.add_css_class("result-count-badge")
        header_box.append(count_label)
        
        card_box.append(header_box)
        
        # Query string
        if query:
            query_label = Gtk.Label()
            query_label.set_markup(f'<i>Query: "{query}"</i>')
            query_label.set_wrap(True)
            query_label.set_xalign(0.0)
            query_label.set_opacity(0.7)
            query_label.set_margin_top(4)
            card_box.append(query_label)
        
        # Documents list (scrollable)
        if documents:
            scrolled = Gtk.ScrolledWindow()
            scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            scrolled.set_max_content_height(250)
            scrolled.set_propagate_natural_height(True)
            scrolled.set_margin_top(8)
            
            docs_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            
            for i, doc in enumerate(documents[:10], 1):  # Limit to top 10
                doc_widget = self._create_document_item(i, doc)
                docs_box.append(doc_widget)
            
            scrolled.set_child(docs_box)
            card_box.append(scrolled)
            
            # Tip
            if len(documents) > 0:
                tip_label = Gtk.Label()
                tip_label.set_markup(
                    '<span alpha="60%">💡 Click a document to open it</span>'
                )
                tip_label.set_margin_top(6)
                card_box.append(tip_label)
        else:
            # No results
            no_results_label = Gtk.Label(label="No documents found")
            no_results_label.set_opacity(0.6)
            no_results_label.set_margin_top(12)
            no_results_label.set_margin_bottom(12)
            card_box.append(no_results_label)
        
        self.append(card_box)
    
    def _create_document_item(self, index: int, doc: Dict[str, Any]) -> Gtk.Box:
        """Create a widget for a single document result."""
        doc_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        doc_box.add_css_class("document-item")
        doc_box.set_margin_start(8)
        doc_box.set_margin_end(8)
        doc_box.set_margin_top(4)
        doc_box.set_margin_bottom(4)
        
        # Header row
        header_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        # Index
        index_label = Gtk.Label(label=f"{index}.")
        index_label.add_css_class("doc-index")
        header_row.append(index_label)
        
        # Path/name
        path = doc.get("path", "")
        name_label = Gtk.Label()
        name_label.set_markup(f"<b>{path}</b>")
        name_label.set_halign(Gtk.Align.START)
        name_label.set_hexpand(True)
        name_label.set_ellipsize(True)
        header_row.append(name_label)
        
        # Relevance score (if available)
        relevance = doc.get("relevance", 0)
        if relevance > 0:
            score_label = Gtk.Label(label=f"{relevance:.2f}")
            score_label.set_opacity(0.6)
            score_label.set_tooltip_text("Relevance score")
            header_row.append(score_label)
        
        # Open button
        open_btn = Gtk.Button(label="Open")
        open_btn.add_css_class("doc-open-btn")
        open_btn.connect("clicked", lambda _: self._open_document(path))
        header_row.append(open_btn)
        
        doc_box.append(header_row)
        
        # Preview/snippet (if available)
        preview = doc.get("preview", "") or doc.get("snippet", "")
        if preview:
            preview_label = Gtk.Label(label=preview[:150] + ("..." if len(preview) > 150 else ""))
            preview_label.set_wrap(True)
            preview_label.set_xalign(0.0)
            preview_label.set_opacity(0.7)
            preview_label.set_margin_start(20)  # Indent
            preview_label.add_css_class("doc-preview")
            doc_box.append(preview_label)
        
        return doc_box
    
    def _open_document(self, path: str):
        """Open a document."""
        try:
            import subprocess
            subprocess.Popen(["xdg-open", path])
            logger.info(f"Opening document: {path}")
        except Exception as e:
            logger.error(f"Failed to open document: {e}")

