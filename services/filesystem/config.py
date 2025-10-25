"""Configuration for filesystem service."""

from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class FileSystemServiceConfig(BaseSettings):
    """Configuration for the filesystem service."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Service
    service_name: str = "filesystem_service"
    service_port: int = 8003
    host: str = "0.0.0.0"
    
    # Indexing
    watch_directories: List[Path] = [Path.home()]
    exclude_patterns: List[str] = [
        "*/node_modules/*",
        "*/.git/*",
        "*/.venv/*",
        "*/venv/*",
        "*/__pycache__/*",
        "*.pyc",
        "*/.cache/*",
        "*/Cache/*",
        "*/.npm/*",
        "*/dist/*",
        "*/build/*",
    ]
    
    # File types to index
    text_extensions: List[str] = [
        ".txt", ".md", ".rst", ".log",
        ".py", ".js", ".ts", ".jsx", ".tsx",
        ".java", ".c", ".cpp", ".h", ".hpp",
        ".go", ".rs", ".sh", ".bash",
        ".json", ".yaml", ".yml", ".toml", ".xml",
        ".html", ".css", ".scss",
        ".sql", ".r", ".m", ".mat",
    ]
    
    document_extensions: List[str] = [
        ".pdf", ".docx", ".doc", ".odt",
        ".pptx", ".ppt", ".odp",
        ".xlsx", ".xls", ".ods",
    ]
    
    # Limits
    max_file_size_mb: int = 10
    chunk_size: int = 1000  # Characters per chunk
    chunk_overlap: int = 200  # Overlap between chunks
    
    # Qdrant collection
    collection_name: str = "neuralux_files"
    
    # Message bus subjects
    fs_search_subject: str = "system.file.search"
    fs_index_subject: str = "system.file.index"

