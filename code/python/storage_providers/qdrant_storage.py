# Copyright (c) 2025 Microsoft Corporation.
# Licensed under the MIT License

"""
Qdrant storage provider for conversation history.
"""

import os
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models

from core.storage import StorageProvider, ConversationEntry
from core.embedding import get_embedding
from misc.logger.logging_config_helper import get_configured_logger

logger = get_configured_logger("qdrant_storage")


def _normalize_qdrant_url(u: Optional[str]) -> Optional[str]:
    if not u:
        return u
    if u.startswith("http://") or u.startswith("https://"):
        host = u.split("://", 1)[1]
        if ":" not in host:
            return u.rstrip("/") + ":6333"
    return u


class QdrantStorageProvider(StorageProvider):
    """Qdrant-based storage for conversation history."""

    def __init__(self, config):
        self.config = config
        self.collection_name = (
            getattr(config, "collection_name", None)
            or os.getenv("QDRANT_COLLECTION")
            or "nlweb_conversations"
        )
        self.vector_size = (
            getattr(config, "vector_size", None)
            or int(os.getenv("EMBEDDING_DIM", "1536"))
        )

        url_cfg = getattr(config, "url", None) if hasattr(config, "url") else None
        api_key_cfg = getattr(config, "api_key", None) if hasattr(config, "api_key") else None
        path_cfg = getattr(config, "database_path", None) if hasattr(config, "database_path") else None

        self.url = _normalize_qdrant_url(url_cfg or os.getenv("QDRANT_URL"))
        self.api_key = api_key_cfg or os.getenv("QDRANT_API_KEY")
        self.path = path_cfg or os.getenv("QDRANT_LOCAL_PATH")

        self.client: Optional[AsyncQdrantClient] = None

    async def initialize(self):
        try:
            if self.url:
                logger.info(f"Connecting to Qdrant at {self.url}")
                self.client = AsyncQdrantClient(url=self.url, api_key=self.api_key)
            else:
                logger.info(f"Using local Qdrant storage at {self.path}")
                self.client = AsyncQdrantClient(path=self.path)

            collections = await self.client.get_collections()
            names = [c.name for c in collections.collections]

            if self.collection_name not in names:
                logger.info(f"Creating collection '{self.collection_name}'")
                await self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=self.vector_size,
                        distance=models.Distance.COSINE,
                    ),
                )
                try:
                    import warnings
                    with warnings.catch_warnings():
                        warnings.filterwarnings("ignore", message="Payload indexes have no effect in the local Qdrant")
                        await self.client.create_payload_index(
                            collection_name=self.collection_name,
                            field_name="user_id",
                            field_schema=models.PayloadSchemaType.KEYWORD,
                        )
                        await self.client.create_payload_index(
                            collection_name=self.collection_name,
                            field_name="thread_id",
                            field_schema=models.PayloadSchemaType.KEYWORD,
                        )
                        await self.client.create_payload_index(
                            collection_name=self.collection_name,
                            field_name="site",
                            field_schema=models.PayloadSchemaType.KEYWORD,
                        )
                        await self.client.create_payload_index(
                            collection_name=self.collection_name,
                            field_name="time_of_creation",
                            field_schema=models.PayloadSchemaType.DATETIME,
                        )
                except Exception:
                    pass

            logger.info("Qdrant storage provider initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Qdrant storage: {e}")
            raise

    async def add_conversation(self, user_id: str, site: str, thread_id: Optional[str],
                               user_prompt: str, response: str) -> ConversationEntry:
        try:
            if thread_id is None:
                thread_id = str(uuid.uuid4())
                logger.info(f"Created new thread_id: {thread_id}")

            conversation_id = str(uuid.uuid4())
            conversation_text = f"User: {user_prompt}\nAssistant: {response}"
            embedding = await get_embedding(conversation_text)

            entry = ConversationEntry(
                user_id=user_id,
                site=site,
                thread_id=thread_id,
                user_prompt=user_prompt,
                response=response,
                time_of_creation=datetime.utcnow(),
                conversation_id=conversation_id,
                embedding=embedding,
            )

            point = models.PointStruct(
                id=str(uuid.uuid4()),
                vector=entry.embedding,
                payload={
                    "conversation_id": entry.conversation_id,
                    "user_id": entry.user_id,
                    "site": entry.site,
                    "thread_id": entry.thread_id,
                    "user_prompt": entry.user_prompt,
                    "response": entry.response,
                    "time_of_creation": entry.time_of_creation.isoformat(),
                },
            )

            await self.client.upsert(
                collection_name=self.collection_name,
                points=[point],
            )

            logger.debug(f"Stored conversation {entry.conversation_id} in thread {entry.thread_id}")
            return entry

        except Exception as e:
            logger.error(f"Failed to add conversation: {e}")
            raise

    async def get_conversation_thread(self, thread_id: str, user_id: Optional[str] = None) -> List[ConversationEntry]:
        try:
            must = [
                models.FieldCondition(
                    key="thread_id",
                    match=models.MatchValue(value=thread_id),
                )
            ]
            if user_id:
                must.append(
                    models.FieldCondition(
                        key="user_id",
                        match=models.MatchValue(value=user_id),
                    )
                )

            results = await self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=models.Filter(must=must),
                limit=1000,
                with_payload=True,
                with_vectors=True,
            )

            conversations: List[ConversationEntry] = []
            for point in results[0]:
                payload = point.payload
                conversations.append(
                    ConversationEntry(
                        conversation_id=payload["conversation_id"],
                        user_id=payload["user_id"],
                        site=payload["site"],
                        thread_id=payload["thread_id"],
                        user_prompt=payload["user_prompt"],
                        response=payload["response"],
                        time_of_creation=datetime.fromisoformat(payload["time_of_creation"]),
                        embedding=point.vector,
                    )
                )

            conversations.sort(key=lambda x: x.time_of_creation)
            return conversations

        except Exception as e:
            logger.error(f"Failed to get conversation thread: {e}")
            return []

    async def get_recent_conversations(self, user_id: str, site: str, limit: int = 50) -> List[Dict[str, Any]]:
        try:
            must = [
                models.FieldCondition(
                    key="user_id",
                    match=models.MatchValue(value=user_id),
                )
            ]
            if site != "all":
                must.append(
                    models.FieldCondition(
                        key="site",
                        match=models.MatchValue(value=site),
                    )
                )

            filter_condition = models.Filter(must=must)

            results = await self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=filter_condition,
                limit=limit,
                with_payload=True,
                with_vectors=False,
            )

            threads_dict: Dict[str, Dict[str, Any]] = {}
            for point in results[0]:
                payload = point.payload
                thread_id = payload["thread_id"]
                if thread_id not in threads_dict:
                    threads_dict[thread_id] = {
                        "id": thread_id,
                        "site": payload["site"],
                        "conversations": [],
                    }
                threads_dict[thread_id]["conversations"].append(
                    {
                        "id": payload["conversation_id"],
                        "user_prompt": payload["user_prompt"],
                        "response": payload["response"],
                        "time": payload["time_of_creation"],
                    }
                )

            for thread in threads_dict.values():
                thread["conversations"].sort(key=lambda x: x["time"])

            threads_list = list(threads_dict.values())
            threads_list.sort(
                key=lambda t: t["conversations"][-1]["time"] if t["conversations"] else "",
                reverse=True,
            )

            return threads_list

        except Exception as e:
            logger.error(f"Failed to get recent conversations: {e}")
            return []

    async def delete_conversation(self, conversation_id: str, user_id: Optional[str] = None) -> bool:
        try:
            must = [
                models.FieldCondition(
                    key="conversation_id",
                    match=models.MatchValue(value=conversation_id),
                )
            ]
            if user_id:
                must.append(
                    models.FieldCondition(
                        key="user_id",
                        match=models.MatchValue(value=user_id),
                    )
                )

            await self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(must=must)
                ),
            )
            logger.debug(f"Deleted conversation {conversation_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete conversation: {e}")
            return False
