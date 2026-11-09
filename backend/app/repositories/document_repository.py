import uuid
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

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

    def list_page(
        self,
        *,
        department_id: int | None,
        include_global: bool,
        offset: int,
        limit: int,
    ) -> tuple[list[Document], int]:
        """Newest first. department_id=None -> every document.
        include_global also returns documents with no department (visible to all)."""
        filters = []
        if department_id is not None:
            cond = Document.department_id == department_id
            filters.append(or_(cond, Document.department_id.is_(None)) if include_global else cond)

        total = self.db.scalar(select(func.count()).select_from(Document).where(*filters)) or 0
        stmt = (
            select(Document)
            .options(selectinload(Document.department))
            .where(*filters)
            .order_by(Document.uploaded_at.desc(), Document.id)
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.scalars(stmt)), total
