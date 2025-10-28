"""Filesystem service - semantic file search and indexing."""

import asyncio
import sys
import time
from pathlib import Path

import structlog
from fastapi import FastAPI, HTTPException
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "packages" / "common"))

from neuralux.config import NeuraluxConfig
from neuralux.logger import setup_logging
from neuralux.messaging import MessageBusClient

from config import FileSystemServiceConfig
from indexer import FileIndexer
from searcher import FileSearcher
from models import (
    SearchQuery, IndexRequest, IndexResponse, SearchResponse,
    FileWriteRequest, FileWriteResponse,
    FileReadRequest, FileReadResponse,
    FileMoveRequest, FileMoveResponse,
    FileDeleteRequest, FileDeleteResponse,
)

logger = structlog.get_logger(__name__)


class FileSystemService:
    """Filesystem service for semantic file operations."""
    
    def __init__(self):
        """Initialize the filesystem service."""
        self.config = FileSystemServiceConfig()
        self.neuralux_config = NeuraluxConfig()
        self.message_bus = MessageBusClient(self.neuralux_config)
        self.app = FastAPI(title="Neuralux Filesystem Service")
        
        # Initialize Qdrant client
        self.qdrant = QdrantClient(url=self.neuralux_config.qdrant_url)
        
        # Initialize embedder (lightweight model)
        logger.info("Loading embedding model...")
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("Embedding model loaded")
        
        # Initialize indexer and searcher
        self.indexer = FileIndexer(self.config, self.qdrant, self.embedder)
        self.searcher = FileSearcher(self.config, self.qdrant, self.embedder)
        
        # Setup routes
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup FastAPI routes."""
        
        @self.app.get("/")
        async def root():
            return {
                "service": "neuralux-filesystem",
                "version": "0.1.0",
                "status": "running"
            }
        
        @self.app.post("/search", response_model=SearchResponse)
        async def search(query: SearchQuery):
            """Search for files by content."""
            try:
                return self.searcher.search(query)
            except Exception as e:
                logger.error("Search failed", error=str(e))
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/index", response_model=IndexResponse)
        async def index(request: IndexRequest):
            """Index a directory."""
            try:
                directory = Path(request.directory).expanduser()
                
                if not directory.exists():
                    raise HTTPException(status_code=404, detail="Directory not found")
                
                start_time = time.time()
                files, chunks, errors = self.indexer.index_directory(
                    directory,
                    recursive=request.recursive
                )
                duration = time.time() - start_time
                
                return IndexResponse(
                    files_indexed=files,
                    chunks_created=chunks,
                    errors=errors,
                    duration_seconds=duration
                )
            except HTTPException:
                raise
            except Exception as e:
                logger.error("Indexing failed", error=str(e))
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/similar/{file_path:path}")
        async def find_similar(file_path: str, limit: int = 10):
            """Find files similar to the given file."""
            try:
                return self.searcher.search_similar(file_path, limit)
            except Exception as e:
                logger.error("Similar search failed", error=str(e))
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/file/write", response_model=FileWriteResponse)
        async def write_file(request: FileWriteRequest):
            """Write content to a file."""
            try:
                return await self._write_file(request)
            except Exception as e:
                logger.error("File write failed", error=str(e))
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/file/read", response_model=FileReadResponse)
        async def read_file(request: FileReadRequest):
            """Read content from a file."""
            try:
                return await self._read_file(request)
            except Exception as e:
                logger.error("File read failed", error=str(e))
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/file/move", response_model=FileMoveResponse)
        async def move_file(request: FileMoveRequest):
            """Move or rename a file."""
            try:
                return await self._move_file(request)
            except Exception as e:
                logger.error("File move failed", error=str(e))
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/file/delete", response_model=FileDeleteResponse)
        async def delete_file(request: FileDeleteRequest):
            """Delete a file."""
            try:
                return await self._delete_file(request)
            except Exception as e:
                logger.error("File delete failed", error=str(e))
                raise HTTPException(status_code=500, detail=str(e))
    
    async def _handle_search_request(self, request_data: dict) -> dict:
        """Handle search request from message bus."""
        try:
            query = SearchQuery(**request_data)
            response = self.searcher.search(query)
            return response.model_dump(mode='json')
        except Exception as e:
            logger.error("Message bus search failed", error=str(e))
            return {"error": str(e)}
    
    async def _handle_index_request(self, request_data: dict) -> dict:
        """Handle index request from message bus."""
        try:
            request = IndexRequest(**request_data)
            directory = Path(request.directory).expanduser()
            
            start_time = time.time()
            files, chunks, errors = self.indexer.index_directory(
                directory,
                recursive=request.recursive
            )
            duration = time.time() - start_time
            
            response = IndexResponse(
                files_indexed=files,
                chunks_created=chunks,
                errors=errors,
                duration_seconds=duration
            )
            return response.model_dump()
        except Exception as e:
            logger.error("Message bus indexing failed", error=str(e))
            return {"error": str(e)}
    
    async def _write_file(self, request: FileWriteRequest) -> FileWriteResponse:
        """Write content to a file."""
        try:
            file_path = Path(request.file_path).expanduser()
            
            # Create parent directories if needed
            if request.create_dirs:
                file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            if request.mode == "a":
                with file_path.open("a", encoding="utf-8") as f:
                    bytes_written = f.write(request.content)
            else:
                bytes_written = len(request.content)
                file_path.write_text(request.content, encoding="utf-8")
            
            logger.info("File written", path=str(file_path), bytes=bytes_written)
            
            return FileWriteResponse(
                success=True,
                file_path=str(file_path),
                bytes_written=bytes_written,
            )
        except Exception as e:
            logger.error("File write failed", error=str(e))
            return FileWriteResponse(
                success=False,
                file_path=request.file_path,
                bytes_written=0,
                error=str(e),
            )
    
    async def _read_file(self, request: FileReadRequest) -> FileReadResponse:
        """Read content from a file."""
        try:
            file_path = Path(request.file_path).expanduser()
            
            if not file_path.exists():
                return FileReadResponse(
                    success=False,
                    file_path=str(file_path),
                    error="File does not exist",
                )
            
            # Check file size
            size = file_path.stat().st_size
            if size > request.max_size:
                return FileReadResponse(
                    success=False,
                    file_path=str(file_path),
                    size_bytes=size,
                    error=f"File too large: {size} bytes (max {request.max_size})",
                )
            
            # Read file
            content = file_path.read_text(encoding="utf-8")
            
            logger.info("File read", path=str(file_path), bytes=size)
            
            return FileReadResponse(
                success=True,
                file_path=str(file_path),
                content=content,
                size_bytes=size,
            )
        except Exception as e:
            logger.error("File read failed", error=str(e))
            return FileReadResponse(
                success=False,
                file_path=request.file_path,
                error=str(e),
            )
    
    async def _move_file(self, request: FileMoveRequest) -> FileMoveResponse:
        """Move or rename a file."""
        try:
            import shutil
            
            src_path = Path(request.src_path).expanduser()
            dst_path = Path(request.dst_path).expanduser()
            
            if not src_path.exists():
                return FileMoveResponse(
                    success=False,
                    src_path=str(src_path),
                    dst_path=str(dst_path),
                    error="Source file does not exist",
                )
            
            if dst_path.exists() and not request.overwrite:
                return FileMoveResponse(
                    success=False,
                    src_path=str(src_path),
                    dst_path=str(dst_path),
                    error="Destination file already exists",
                )
            
            # Create parent directories
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Move file
            shutil.move(str(src_path), str(dst_path))
            
            logger.info("File moved", src=str(src_path), dst=str(dst_path))
            
            return FileMoveResponse(
                success=True,
                src_path=str(src_path),
                dst_path=str(dst_path),
            )
        except Exception as e:
            logger.error("File move failed", error=str(e))
            return FileMoveResponse(
                success=False,
                src_path=request.src_path,
                dst_path=request.dst_path,
                error=str(e),
            )
    
    async def _delete_file(self, request: FileDeleteRequest) -> FileDeleteResponse:
        """Delete a file."""
        try:
            file_path = Path(request.file_path).expanduser()
            
            if not file_path.exists():
                return FileDeleteResponse(
                    success=False,
                    file_path=str(file_path),
                    error="File does not exist",
                )
            
            # Delete file
            file_path.unlink()
            
            logger.info("File deleted", path=str(file_path))
            
            return FileDeleteResponse(
                success=True,
                file_path=str(file_path),
            )
        except Exception as e:
            logger.error("File delete failed", error=str(e))
            return FileDeleteResponse(
                success=False,
                file_path=request.file_path,
                error=str(e),
            )
    
    async def _handle_file_write_request(self, request_data: dict) -> dict:
        """Handle file write request from message bus."""
        try:
            request = FileWriteRequest(**request_data)
            response = await self._write_file(request)
            return response.model_dump()
        except Exception as e:
            logger.error("Message bus file write failed", error=str(e))
            return {"success": False, "error": str(e)}
    
    async def _handle_file_read_request(self, request_data: dict) -> dict:
        """Handle file read request from message bus."""
        try:
            request = FileReadRequest(**request_data)
            response = await self._read_file(request)
            return response.model_dump()
        except Exception as e:
            logger.error("Message bus file read failed", error=str(e))
            return {"success": False, "error": str(e)}
    
    async def _handle_file_move_request(self, request_data: dict) -> dict:
        """Handle file move request from message bus."""
        try:
            request = FileMoveRequest(**request_data)
            response = await self._move_file(request)
            return response.model_dump()
        except Exception as e:
            logger.error("Message bus file move failed", error=str(e))
            return {"success": False, "error": str(e)}
    
    async def _handle_file_delete_request(self, request_data: dict) -> dict:
        """Handle file delete request from message bus."""
        try:
            request = FileDeleteRequest(**request_data)
            response = await self._delete_file(request)
            return response.model_dump()
        except Exception as e:
            logger.error("Message bus file delete failed", error=str(e))
            return {"success": False, "error": str(e)}
    
    async def start(self):
        """Start the filesystem service."""
        setup_logging(self.config.service_name, self.neuralux_config.log_level)
        logger.info("Starting filesystem service")
        
        # Connect to message bus
        try:
            await self.message_bus.connect()
            
            # Register message handlers
            await self.message_bus.reply_handler(
                self.config.fs_search_subject,
                self._handle_search_request
            )
            await self.message_bus.reply_handler(
                self.config.fs_index_subject,
                self._handle_index_request
            )
            
            # Register file operation handlers
            await self.message_bus.reply_handler(
                "system.file.write",
                self._handle_file_write_request
            )
            await self.message_bus.reply_handler(
                "system.file.read",
                self._handle_file_read_request
            )
            await self.message_bus.reply_handler(
                "system.file.move",
                self._handle_file_move_request
            )
            await self.message_bus.reply_handler(
                "system.file.delete",
                self._handle_file_delete_request
            )
            
            logger.info("Message bus handlers registered")
        except Exception as e:
            logger.error("Failed to connect to message bus", error=str(e))
            logger.warning("Service will run in REST-only mode")
    
    async def stop(self):
        """Stop the filesystem service."""
        logger.info("Stopping filesystem service")
        await self.message_bus.disconnect()


# Create service instance
service = FileSystemService()


if __name__ == "__main__":
    import uvicorn
    
    async def startup():
        await service.start()
    
    async def shutdown():
        await service.stop()
    
    # Add startup/shutdown handlers
    service.app.add_event_handler("startup", startup)
    service.app.add_event_handler("shutdown", shutdown)
    
    # Run the service
    uvicorn.run(
        service.app,
        host=service.config.host,
        port=service.config.service_port,
        log_level=service.neuralux_config.log_level.lower(),
    )

