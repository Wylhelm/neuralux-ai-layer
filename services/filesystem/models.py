"""Data models for filesystem service."""

from datetime import datetime
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field


class FileMetadata(BaseModel):
    """Metadata for an indexed file."""
    path: str
    filename: str
    extension: str
    size_bytes: int
    modified_time: datetime
    created_time: Optional[datetime] = None
    mime_type: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class FileChunk(BaseModel):
    """A chunk of file content with metadata."""
    file_path: str
    chunk_index: int
    content: str
    char_start: int
    char_end: int
    metadata: FileMetadata


class SearchQuery(BaseModel):
    """Search query for files."""
    query: str
    limit: int = 10
    file_types: Optional[List[str]] = None
    min_score: float = 0.1  # Lower threshold for better semantic search recall


class SearchResult(BaseModel):
    """A search result."""
    file_path: str
    filename: str
    score: float
    snippet: str
    metadata: FileMetadata
    chunk_index: int = 0


class SearchResponse(BaseModel):
    """Response from file search."""
    query: str
    results: List[SearchResult]
    total_found: int


class IndexRequest(BaseModel):
    """Request to index a directory."""
    directory: str
    recursive: bool = True
    force_reindex: bool = False


class IndexResponse(BaseModel):
    """Response from indexing operation."""
    files_indexed: int
    chunks_created: int
    errors: List[str] = []
    duration_seconds: float

