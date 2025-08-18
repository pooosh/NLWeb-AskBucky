#!/usr/bin/env python3
"""
Qdrant search functionality for AskBucky
"""

import os
from typing import List, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models
from core.embedding import get_embedding
from misc.logger.logging_config_helper import get_configured_logger

logger = get_configured_logger("qdrant_store")

def search(query: str, top_k: int = 8, sitetag: Optional[str] = None) -> List[models.ScoredPoint]:
    """
    Search for documents in Qdrant
    
    Args:
        query: Search query string
        top_k: Number of results to return
        sitetag: Optional site tag to filter results
        
    Returns:
        List of ScoredPoint objects with search results
    """
    try:
        # Get Qdrant connection details from environment
        qdrant_url = os.environ.get("QDRANT_URL")
        qdrant_api_key = os.environ.get("QDRANT_API_KEY")
        
        if not qdrant_url:
            logger.error("QDRANT_URL not found in environment")
            return []
        
        # Create client
        client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key, timeout=30.0)
        
        # Get embedding for the query
        embedding = get_embedding(query)
        
        # Build search filter
        search_filter = None
        if sitetag:
            search_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="site",
                        match=models.MatchValue(value=sitetag)
                    )
                ]
            )
        
        # Perform search
        search_result = client.search(
            collection_name="nlweb_documents",  # Default collection name
            query_vector=embedding,
            limit=top_k,
            query_filter=search_filter,
            with_payload=True,
            with_vectors=False
        )
        
        logger.info(f"Search returned {len(search_result)} results for query: {query}")
        return search_result
        
    except Exception as e:
        logger.error(f"Error in Qdrant search: {e}")
        return [] 