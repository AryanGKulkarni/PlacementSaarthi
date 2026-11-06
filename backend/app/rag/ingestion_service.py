import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.db.models import Document, DocumentStatus
from app.repositories.document_repository import DocumentRepository

log = logging.getLogger(__name__)


class IngestionService:
    """Runs inside the ingestion worker: uploaded -> processing -> indexed | failed."""

    def __init__(self, documents: DocumentRepository):
        self.documents = documents

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
            self.documents.update_status(doc, DocumentStatus.failed, error=str(exc)[:1000])
            self.documents.commit()
            log.exception("Ingestion failed for %s", doc.id)

    def _run_pipeline(self, doc: Document, path: Path) -> int:
        """Extract text -> chunk -> embed -> store in ChromaDB. Returns the chunk count.

        TODO: RAG pipeline not implemented yet; this placeholder stores no chunks.
        """
        log.warning("RAG pipeline not implemented yet: %s marked indexed with 0 chunks", doc.id)
        return 0
