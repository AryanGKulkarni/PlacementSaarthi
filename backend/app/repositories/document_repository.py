import uuid
from datetime import datetime

from sqlalchemy import select

from app.db.models import Document, DocumentStatus
from app.repositories.base import BaseRepository


class DocumentRepository(BaseRepository):
    def get(self, document_id: uuid.UUID) -> Document | None:
        return self.db.get(Document, document_id)

    def get_by_sha256(self, sha256: str) -> Document | None:
        return self.db.scalar(select(Document).where(Document.sha256 == sha256))

    def add(self, document: Document) -> Document:
        """Stage a new document and flush so DB constraint errors surface immediately."""
        self.db.add(document)
        self.db.flush()
        return document

    def refresh(self, document: Document) -> Document:
        self.db.refresh(document)
        return document

    def update_status(
        self,
        document: Document,
        status: DocumentStatus,
        *,
        chunk_count: int | None = None,
        error: str | None = None,
        indexed_at: datetime | None = None,
    ) -> Document:
        document.status = status
        document.error = error
        if chunk_count is not None:
            document.chunk_count = chunk_count
        if indexed_at is not None:
            document.indexed_at = indexed_at
        self.db.flush()
        return document
