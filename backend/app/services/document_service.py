import asyncio
import logging
import uuid
from pathlib import Path

from app.core.exceptions import ConflictError, ForbiddenError, UnsupportedFileTypeError
from app.db.models import Document, FileType, Role, User
from app.messaging.ingest_queue import IngestQueue
from app.repositories.document_repository import DocumentRepository
from app.services import file_storage
from app.schemas.document import DocumentListItem, DocumentListPage
from app.services.file_storage import AsyncReadable

log = logging.getLogger(__name__)


class DocumentService:
    def __init__(
        self,
        documents: DocumentRepository,
        ingest_queue: IngestQueue,
    ):
        self.documents = documents
        self.ingest_queue = ingest_queue

    async def upload(
        self,
        source: AsyncReadable,
        filename: str,
        uploader: User,
        title: str | None = None,
        description: str | None = None,
    ) -> Document:
        file_type = self._file_type(filename)
        department_id = self._department_for(uploader)

        temp = await file_storage.save_to_temp(source, file_type)

        try:
            existing = self.documents.get_by_sha256(temp.sha256)
            if existing:
                raise ConflictError(
                    f"This file was already uploaded as '{existing.original_filename}' "
                    f"(id {existing.id})"
                )

            doc = self.documents.add(
                Document(
                    id=uuid.uuid4(),
                    original_filename=Path(filename).name[:255],
                    file_type=file_type,
                    size_bytes=temp.size_bytes,
                    sha256=temp.sha256,
                    title=title,
                    description=description,
                    department_id=department_id,
                    uploaded_by=uploader.id,
                )
            )

            final_path = file_storage.promote(temp, doc.stored_filename)
            try:
                self.documents.commit()
            except BaseException:
                final_path.unlink(missing_ok=True)
                raise
        except BaseException:
            self.documents.rollback()
            temp.discard()
            raise

        # The upload is saved either way; if the queue is down the document just stays
        # 'uploaded' and can be re-queued later.
        try:
            await asyncio.to_thread(self.ingest_queue.enqueue, doc.id)
        except Exception:
            log.exception("Could not enqueue document %s for ingestion", doc.id)

        return self.documents.refresh(doc)

    def list_documents(
        self, viewer: User, *, department_id: int | None, limit: int, offset: int
    ) -> DocumentListPage:
        """Admin: all documents (optional department filter, exact match).
        Faculty: their department's documents + the ones visible to all departments."""
        if viewer.role is Role.admin:
            include_global = False
        else:
            own = self._department_for(viewer)
            if department_id is not None and department_id != own:
                raise ForbiddenError("You can only view documents of your own department")
            department_id, include_global = own, True

        docs, total = self.documents.list_page(
            department_id=department_id, include_global=include_global, offset=offset, limit=limit
        )
        return DocumentListPage(
            items=[_list_item(d) for d in docs], total=total, limit=limit, offset=offset
        )

    @staticmethod
    def _department_for(uploader: User) -> int | None:
        """Faculty uploads are scoped to their department; admin uploads are visible to all."""
        if uploader.role is Role.admin:
            return None
        if uploader.role is Role.faculty and uploader.faculty_profile is not None:
            return uploader.faculty_profile.department_id
        raise ForbiddenError("Only faculty and admins can upload documents")

    @staticmethod
    def _file_type(filename: str) -> FileType:
        ext = Path(filename).suffix.lower().lstrip(".")
        try:
            return FileType(ext)
        except ValueError:
            raise UnsupportedFileTypeError("Only .pdf and .txt files are allowed") from None


def _list_item(doc: Document) -> DocumentListItem:
    return DocumentListItem(
        id=doc.id,
        filename=doc.original_filename,
        status=doc.status,
        chunks=doc.chunk_count,
        uploaded_at=doc.uploaded_at,
        size_bytes=doc.size_bytes,
        department_code=doc.department.code if doc.department else None,
        error=doc.error,
    )
