"""ChromaDB (server) access for the knowledge base.

One collection (settings.chroma_collection), cosine distance. Each record is one chunk:

    id         "{doc_id}:{chunk_no}"
    embedding  vector of the chunk text (computed by our Embedder, not by Chroma)
    document   the plain chunk text (no embedding prefix) - what the LLM will see
    metadata   {source_type, doc_id, filename, page?, chunk_no, department_id}

department_id = 0 means "visible to all departments" (Chroma metadata can't hold None).
"""

import logging
import uuid
from dataclasses import dataclass
from typing import Any

import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection

from app.core.config import settings
from app.db.models import Document
from app.rag.chunker import Chunk

log = logging.getLogger(__name__)

ALL_DEPARTMENTS = 0
SOURCE_DOCUMENT = "document"


class VectorStoreError(Exception):
    """ChromaDB unreachable or rejected an operation."""


@dataclass
class SearchHit:
    id: str
    text: str
    metadata: dict[str, Any]
    distance: float  # cosine distance: 0 = identical, larger = less similar


class VectorStore:
    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        collection_name: str | None = None,
    ):
        self.host = host or settings.chroma_host
        self.port = port or settings.chroma_port
        self.collection_name = collection_name or settings.chroma_collection
        self._client: ClientAPI | None = None
        self._collection: Collection | None = None

    # ---- connection -------------------------------------------------------

    @property
    def client(self) -> ClientAPI:
        if self._client is None:
            try:
                self._client = chromadb.HttpClient(host=self.host, port=self.port)
            except Exception as exc:
                raise VectorStoreError(f"ChromaDB not reachable at {self.host}:{self.port}: {exc}") from exc
        return self._client

    @property
    def collection(self) -> Collection:
        if self._collection is None:
            try:
                self._collection = self.client.get_or_create_collection(
                    name=self.collection_name,
                    configuration={"hnsw": {"space": "cosine"}},
                    embedding_function=None,  # we always pass our own embeddings
                )
            except Exception as exc:
                raise VectorStoreError(f"Could not open collection '{self.collection_name}': {exc}") from exc
        return self._collection

    def heartbeat(self) -> int:
        return self.client.heartbeat()

    # ---- write ------------------------------------------------------------

    def add_document_chunks(
        self, document: Document, chunks: list[Chunk], embeddings: list[list[float]]
    ) -> int:
        """Store all chunks of a document. Upsert, so re-running is safe. Returns count stored."""
        if len(chunks) != len(embeddings):
            raise VectorStoreError(f"{len(chunks)} chunks but {len(embeddings)} embeddings")
        if not chunks:
            return 0

        doc_id = str(document.id)
        ids = [chunk_id(doc_id, c.chunk_no) for c in chunks]
        texts = [c.text for c in chunks]
        metadatas = [self._chunk_metadata(document, c) for c in chunks]

        batch = self._max_batch_size()
        try:
            for start in range(0, len(ids), batch):
                end = start + batch
                self.collection.upsert(
                    ids=ids[start:end],
                    embeddings=embeddings[start:end],
                    documents=texts[start:end],
                    metadatas=metadatas[start:end],
                )
        except VectorStoreError:
            raise
        except Exception as exc:
            raise VectorStoreError(f"Failed to store chunks for {doc_id}: {exc}") from exc
        return len(ids)

    def delete_document(self, document_id: uuid.UUID | str) -> None:
        """Remove every chunk belonging to a document (no-op if it has none)."""
        try:
            self.collection.delete(where={"doc_id": str(document_id)})
        except Exception as exc:
            raise VectorStoreError(f"Failed to delete chunks for {document_id}: {exc}") from exc

    # ---- read -------------------------------------------------------------

    def query(
        self,
        embedding: list[float],
        k: int = 4,
        where: dict[str, Any] | None = None,
    ) -> list[SearchHit]:
        """Top-k nearest chunks to a query vector, optionally pre-filtered by metadata."""
        try:
            result = self.collection.query(
                query_embeddings=[embedding],
                n_results=k,
                where=where or None,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            raise VectorStoreError(f"Query failed: {exc}") from exc

        return [
            SearchHit(id=i, text=t, metadata=m or {}, distance=d)
            for i, t, m, d in zip(
                result["ids"][0],
                result["documents"][0],
                result["metadatas"][0],
                result["distances"][0],
            )
        ]

    def count_document_chunks(self, document_id: uuid.UUID | str) -> int:
        try:
            return len(self.collection.get(where={"doc_id": str(document_id)}, include=[])["ids"])
        except Exception as exc:
            raise VectorStoreError(f"Count failed for {document_id}: {exc}") from exc

    def count(self) -> int:
        return self.collection.count()

    # ---- helpers ----------------------------------------------------------

    @staticmethod
    def _chunk_metadata(document: Document, chunk: Chunk) -> dict[str, Any]:
        metadata: dict[str, Any] = {
            "source_type": SOURCE_DOCUMENT,
            "doc_id": str(document.id),
            "filename": document.original_filename,
            "chunk_no": chunk.chunk_no,
            "department_id": document.department_id or ALL_DEPARTMENTS,
        }
        if chunk.page is not None:  # TXT files have no pages; omit rather than store None
            metadata["page"] = chunk.page
        return metadata

    def _max_batch_size(self) -> int:
        try:
            return min(self.client.get_max_batch_size(), 1000)
        except Exception:
            return 500


def chunk_id(doc_id: str, chunk_no: int) -> str:
    return f"{doc_id}:{chunk_no}"
