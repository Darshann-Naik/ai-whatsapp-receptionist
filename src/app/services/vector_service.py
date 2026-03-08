import chromadb
import asyncio
import uuid
from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.core.logging import logger

class VectorService:
    def __init__(self):
        # Persistent local storage
        self.client = chromadb.PersistentClient(path="./chroma_data")
        
        # We use a single collection. Multi-tenancy is enforced via metadata filtering.
        self.collection = self.client.get_or_create_collection(
            name="business_knowledge"
        )
        
        # Optimal chunking for semantic search
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            is_separator_regex=False,
        )

    def _sync_upsert(self, tenant_id: int, text_content: str):
        chunks = self.text_splitter.split_text(text_content)
        
        if not chunks:
            return

        documents = []
        metadatas = []
        ids = []

        for chunk in chunks:
            documents.append(chunk)
            # CRITICAL: This is your multi-tenant isolation lock
            metadatas.append({"tenant_id": tenant_id})
            ids.append(str(uuid.uuid4()))

        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        logger.info(f"Upserted {len(chunks)} chunks for tenant {tenant_id}")

    def _sync_query(self, tenant_id: int, query_text: str) -> List[str]:
        results = self.collection.query(
            query_texts=[query_text],
            n_results=3,
            # CRITICAL: This guarantees no data leakage between clients
            where={"tenant_id": tenant_id} 
        )
        
        if not results["documents"] or not results["documents"][0]:
            return []
            
        return results["documents"][0]

    async def upsert_business_info(self, tenant_id: int, text_content: str):
        """Offloads CPU/Disk bound chunking and database writing to a thread."""
        await asyncio.to_thread(self._sync_upsert, tenant_id, text_content)

    async def query_business_info(self, tenant_id: int, query_text: str) -> str:
        """Offloads CPU/Disk bound embedding and similarity search to a thread."""
        docs = await asyncio.to_thread(self._sync_query, tenant_id, query_text)
        # Join the retrieved chunks into a single context string
        return "\n---\n".join(docs) if docs else ""
    
    def _sync_delete(self, tenant_id: int):
        """Synchronous deletion of all chunks for a specific tenant."""
        try:
            self.collection.delete(where={"tenant_id": tenant_id})
            logger.info(f"Cleared all vector data for tenant {tenant_id}")
        except Exception as e:
            logger.error(f"Failed to delete vectors for tenant {tenant_id}: {str(e)}")

    async def clear_business_info(self, tenant_id: int):
        """Async wrapper to offload disk-bound deletion to a thread."""
        await asyncio.to_thread(self._sync_delete, tenant_id)

vector_service = VectorService()