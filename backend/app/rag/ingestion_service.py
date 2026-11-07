import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.db.models import Document, DocumentStatus
from app.rag.chunker import chunk_pages
from app.rag.embedder import Embedder
from app.rag.loader import LoaderError, load_pages
from app.rag.vector_store import VectorStore
from app.repositories.document_repository import DocumentRepository

log = logging.getLogger(__name__)


class IngestionService:
    """Runs inside the ingestion worker: uploaded -> processing -> indexed | failed."""

    def __init__(self, documents: DocumentRepository, embedder: Embedder, vector_store: VectorStore):
        self.documents = documents
        self.embedder = embedder
        self.vector_store = vector_store

    def process(self, document_id: uuid.UUID) -> None:
        doc = self.documents.get(document_id)
        if doc is None:
            log.warning("Document %s not found (deleted?), skipping", document_id)
            return
        if doc.status is DocumentStatus.indexed:
            log.info("Document %s already indexed, skipping", document_id)
            return

        self.documents.update_status(doc, DocumentStatus.processing)
        self.documents.commit()
        log.info("Processing %s (%s)", doc.id, doc.original_filename)

        try:
            path = settings.upload_dir / doc.stored_filename
            if not path.exists():
                raise FileNotFoundError(f"Stored file missing: {doc.stored_filename}")

            chunk_count = self._run_pipeline(doc, path)

            self.documents.update_status(
                doc,
                DocumentStatus.indexed,
                chunk_count=chunk_count,
                indexed_at=datetime.now(timezone.utc),
            )
            self.documents.commit()
            log.info("Indexed %s: %d chunks", doc.id, chunk_count)
        except Exception as exc:
            self.documents.rollback()
            self._discard_partial_chunks(doc.id)
            self.documents.update_status(doc, DocumentStatus.failed, chunk_count=0, error=str(exc)[:1000])
            self.documents.commit()
            if isinstance(exc, LoaderError):
                log.warning("Ingestion failed for %s: %s", doc.id, exc)  # expected (bad file), no traceback
            else:
                log.exception("Ingestion failed for %s", doc.id)

    def _run_pipeline(self, doc: Document, path: Path) -> int:
        """Extract text -> chunk -> embed -> store in ChromaDB. Returns the chunk count."""
        started = time.perf_counter()

        pages = load_pages(path, doc.file_type)
        chunks = chunk_pages(pages)
        if not chunks:
            raise LoaderError("Text was extracted but produced no usable chunks")
        log.info("%s: %d pages -> %d chunks", doc.id, len(pages), len(chunks))

        embeddings = self.embedder.embed_documents([c.text for c in chunks])
        log.info("%s: embedded %d chunks in %.1fs", doc.id, len(embeddings), time.perf_counter() - started)

        # Replace, don't append: clears chunks from any earlier run (e.g. a reindex
        # where the document now produces fewer chunks).
        self.vector_store.delete_document(doc.id)
        stored = self.vector_store.add_document_chunks(doc, chunks, embeddings)

        log.info("%s: stored %d chunks, total %.1fs", doc.id, stored, time.perf_counter() - started)
        return stored

    def _discard_partial_chunks(self, document_id: uuid.UUID) -> None:
        """A failed document must not leave searchable chunks behind."""
        try:
            self.vector_store.delete_document(document_id)
        except Exception:
            log.warning("Could not clean up chunks for failed document %s", document_id, exc_info=True)
