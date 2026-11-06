import uuid

from sqlalchemy import select

from app.db.models import Document
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
