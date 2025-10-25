"""Semantic file searcher."""

from typing import List
import structlog
from qdrant_client import QdrantClient

from config import FileSystemServiceConfig
from models import SearchQuery, SearchResult, SearchResponse, FileMetadata

logger = structlog.get_logger(__name__)


class FileSearcher:
    """Searches indexed files semantically."""
    
    def __init__(
        self,
        config: FileSystemServiceConfig,
        qdrant_client: QdrantClient,
        embedder
    ):
        """Initialize the file searcher."""
        self.config = config
        self.qdrant = qdrant_client
        self.embedder = embedder
    
    def search(self, query: SearchQuery) -> SearchResponse:
        """Search for files matching the query."""
        logger.info("Searching files", query=query.query, limit=query.limit)
        
        # Generate embedding for query
        query_embedding = self.embedder.encode(query.query).tolist()
        
        # Build filter if file types specified
        search_filter = None
        if query.file_types:
            search_filter = {
                "should": [
                    {"key": "extension", "match": {"value": ext}}
                    for ext in query.file_types
                ]
            }
        
        # Search in Qdrant
        search_results = self.qdrant.search(
            collection_name=self.config.collection_name,
            query_vector=query_embedding,
            limit=query.limit,
            score_threshold=query.min_score,
            query_filter=search_filter if search_filter else None
        )
        
        # Convert to SearchResult objects
        results = []
        for hit in search_results:
            payload = hit.payload
            
            # Create metadata
            metadata = FileMetadata(
                path=payload["file_path"],
                filename=payload["filename"],
                extension=payload["extension"],
                size_bytes=payload["size_bytes"],
                modified_time=payload["modified_time"],
                mime_type=payload.get("mime_type"),
            )
            
            # Extract snippet (first 200 chars of content)
            content = payload["content"]
            snippet = content[:200] + "..." if len(content) > 200 else content
            
            result = SearchResult(
                file_path=payload["file_path"],
                filename=payload["filename"],
                score=hit.score,
                snippet=snippet,
                metadata=metadata,
                chunk_index=payload["chunk_index"]
            )
            results.append(result)
        
        response = SearchResponse(
            query=query.query,
            results=results,
            total_found=len(results)
        )
        
        logger.info("Search complete", results=len(results))
        return response
    
    def search_similar(self, file_path: str, limit: int = 10) -> SearchResponse:
        """Find files similar to the given file."""
        logger.info("Finding similar files", file_path=file_path)
        
        # Get the file's chunks from Qdrant
        scroll_result = self.qdrant.scroll(
            collection_name=self.config.collection_name,
            scroll_filter={
                "must": [
                    {"key": "file_path", "match": {"value": file_path}}
                ]
            },
            limit=1
        )
        
        if not scroll_result[0]:
            return SearchResponse(
                query=f"similar to {file_path}",
                results=[],
                total_found=0
            )
        
        # Use first chunk's embedding to find similar
        first_chunk = scroll_result[0][0]
        query_vector = first_chunk.vector
        
        # Search for similar vectors
        search_results = self.qdrant.search(
            collection_name=self.config.collection_name,
            query_vector=query_vector,
            limit=limit + 10,  # Get extra to filter out the source file
        )
        
        # Filter out the source file and convert to results
        results = []
        seen_files = set()
        
        for hit in search_results:
            payload = hit.payload
            hit_file_path = payload["file_path"]
            
            # Skip the source file and duplicates
            if hit_file_path == file_path or hit_file_path in seen_files:
                continue
            
            seen_files.add(hit_file_path)
            
            metadata = FileMetadata(
                path=hit_file_path,
                filename=payload["filename"],
                extension=payload["extension"],
                size_bytes=payload["size_bytes"],
                modified_time=payload["modified_time"],
                mime_type=payload.get("mime_type"),
            )
            
            content = payload["content"]
            snippet = content[:200] + "..." if len(content) > 200 else content
            
            result = SearchResult(
                file_path=hit_file_path,
                filename=payload["filename"],
                score=hit.score,
                snippet=snippet,
                metadata=metadata,
                chunk_index=payload["chunk_index"]
            )
            results.append(result)
            
            if len(results) >= limit:
                break
        
        return SearchResponse(
            query=f"similar to {file_path}",
            results=results,
            total_found=len(results)
        )

