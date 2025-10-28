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


class FileWriteRequest(BaseModel):
    """Request to write to a file."""
    file_path: str
    content: str
    mode: str = "w"  # 'w' for write, 'a' for append
    create_dirs: bool = True


class FileWriteResponse(BaseModel):
    """Response from file write operation."""
    success: bool
    file_path: str
    bytes_written: int
    error: Optional[str] = None


class FileReadRequest(BaseModel):
    """Request to read a file."""
    file_path: str
    max_size: int = 10 * 1024 * 1024  # 10MB default


class FileReadResponse(BaseModel):
    """Response from file read operation."""
    success: bool
    file_path: str
    content: Optional[str] = None
    size_bytes: int = 0
    error: Optional[str] = None


class FileMoveRequest(BaseModel):
    """Request to move/rename a file."""
    src_path: str
    dst_path: str
    overwrite: bool = False


class FileMoveResponse(BaseModel):
    """Response from file move operation."""
    success: bool
    src_path: str
    dst_path: str
    error: Optional[str] = None


class FileDeleteRequest(BaseModel):
    """Request to delete a file."""
    file_path: str


class FileDeleteResponse(BaseModel):
    """Response from file delete operation."""
    success: bool
    file_path: str
    error: Optional[str] = None

