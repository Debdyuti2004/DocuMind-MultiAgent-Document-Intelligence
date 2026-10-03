"""Vector Store manager powered by ChromaDB."""

from pathlib import Path
from typing import Any, Dict, List, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings

from app.models.schemas import DocumentChunk
from app.rag.embeddings import embedding_service
from app.utils.config import settings
from app.utils.logging import logger


class VectorStore:
    """Manages persistent document embedding indexing and vector retrieval via ChromaDB."""

    def __init__(self, chroma_path: Path = settings.CHROMA_PATH, collection_name: str = settings.CHROMA_COLLECTION_NAME):
        self.chroma_path = chroma_path
        self.collection_name = collection_name
        self.chroma_path.mkdir(parents=True, exist_ok=True)
        
        self.client = chromadb.PersistentClient(
            path=str(self.chroma_path),
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    def add_chunks(self, chunks: List[DocumentChunk]) -> int:
        """Embeds and indexes document chunks into ChromaDB."""
        if not chunks:
            return 0

        ids = [c.chunk_id for c in chunks]
        texts = [c.text for c in chunks]
        metadatas = [
            {
                "document_id": c.document_id,
                "filename": c.filename,
                "page": c.page,
                "section": c.section,
                "chunk_index": c.chunk_index,
                "token_count": c.token_count
            }
            for c in chunks
        ]

        logger.info(f"Generating embeddings for {len(chunks)} chunks...")
        embeddings = embedding_service.embed_texts(texts)

        # Batch insert into ChromaDB
        batch_size = 200
        for i in range(0, len(chunks), batch_size):
            end = i + batch_size
            self.collection.upsert(
                ids=ids[i:end],
                documents=texts[i:end],
                metadatas=metadatas[i:end],
                embeddings=embeddings[i:end]
            )

        logger.info(f"Successfully indexed {len(chunks)} chunks in vector store.")
        return len(chunks)

    def search(
        self,
        query: str,
        top_k: int = settings.TOP_K,
        document_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Performs vector similarity search against ChromaDB."""
        if self.collection.count() == 0:
            return []

        query_embedding = embedding_service.embed_query(query)
        where_filter: Optional[Dict[str, Any]] = None
        
        if document_ids and len(document_ids) == 1:
            where_filter = {"document_id": document_ids[0]}
        elif document_ids and len(document_ids) > 1:
            where_filter = {"document_id": {"$in": document_ids}}

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, self.collection.count()),
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )

        formatted_results: List[Dict[str, Any]] = []
        if not results or not results["ids"] or not results["ids"][0]:
            return formatted_results

        for idx in range(len(results["ids"][0])):
            chunk_id = results["ids"][0][idx]
            text = results["documents"][0][idx]
            meta = results["metadatas"][0][idx]
            distance = results["distances"][0][idx]
            # Convert cosine distance to similarity score: similarity = 1 - distance
            similarity = max(0.0, min(1.0, 1.0 - distance))

            formatted_results.append({
                "chunk_id": chunk_id,
                "text": text,
                "document_id": meta.get("document_id"),
                "filename": meta.get("filename"),
                "page": int(meta.get("page", 1)),
                "section": meta.get("section", "General"),
                "chunk_index": int(meta.get("chunk_index", 0)),
                "similarity_score": similarity
            })

        return formatted_results

    def delete_document(self, document_id: str) -> None:
        """Deletes all chunks belonging to a document ID."""
        try:
            self.collection.delete(where={"document_id": document_id})
            logger.info(f"Deleted vector chunks for document_id: {document_id}")
        except Exception as e:
            logger.error(f"Error deleting chunks for {document_id}: {e}")

    def count(self) -> int:
        """Returns total indexed chunks."""
        return self.collection.count()

    def get_document_chunks(self, document_id: str) -> List[Dict[str, Any]]:
        """Fetches all chunks for a document ordered by page and index."""
        results = self.collection.get(
            where={"document_id": document_id},
            include=["documents", "metadatas"]
        )
        chunks = []
        if results and results["ids"]:
            for idx in range(len(results["ids"])):
                chunks.append({
                    "chunk_id": results["ids"][idx],
                    "text": results["documents"][idx],
                    **results["metadatas"][idx]
                })
            chunks.sort(key=lambda x: (x.get("page", 1), x.get("chunk_index", 0)))
        return chunks


vector_store = VectorStore()
