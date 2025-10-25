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
from models import SearchQuery, IndexRequest, IndexResponse, SearchResponse

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

