"""
vector_store.py — Long-term memory using LlamaIndex and ChromaDB.
"""
import os
from typing import List, Optional
from loguru import logger

from llama_index.core import VectorStoreIndex, StorageContext, Document
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb

class ProjectMemory:
    """
    Manages semantic search and RAG for project context.
    """
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.persist_dir = f"./memory_store/{project_id}"
        os.makedirs(self.persist_dir, exist_ok=True)
        
        # Initialize ChromaDB
        self.db = chromadb.PersistentClient(path=os.path.join(self.persist_dir, "chroma"))
        self.chroma_collection = self.db.get_or_create_collection("project_context")
        
        # Setup LlamaIndex
        self.vector_store = ChromaVectorStore(chroma_collection=self.chroma_collection)
        self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
        
        # Note: Index is created/loaded lazily
        self._index = None

    async def add_context(self, text: str, metadata: Optional[dict] = None):
        """
        Adds a snippet of text to the project's long-term memory.
        """
        doc = Document(text=text, extra_info=metadata or {})
        if not self._index:
            self._index = VectorStoreIndex.from_documents(
                [doc], storage_context=self.storage_context
            )
        else:
            self._index.insert(doc)
        logger.info(f"Added context to project memory: {metadata.get('source') if metadata else 'Raw Text'}")

    async def query_context(self, query: str, top_k: int = 3) -> str:
        """
        Retrieves relevant snippets from memory based on a query.
        """
        if not self._index:
            return ""
        
        query_engine = self._index.as_query_engine(similarity_top_k=top_k)
        response = query_engine.query(query)
        return str(response)
