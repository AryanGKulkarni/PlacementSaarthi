import asyncio
import logging
import uuid
from pathlib import Path

from app.core.exceptions import BadRequestError, ConflictError, UnsupportedFileTypeError
from app.db.models import Document, FileType
from app.messaging.ingest_queue import IngestQueue
from app.repositories.department_repository import DepartmentRepository
from app.repositories.document_repository import DocumentRepository
from app.services import file_storage
from app.services.file_storage import AsyncReadable

log = logging.getLogger(__name__)


class DocumentService:
    def __init__(
        self,
        documents: DocumentRepository,
        departments: DepartmentRepository,
        ingest_queue: IngestQueue,
    ):
        self.documents = documents
        self.departments = departments
        self.ingest_queue = ingest_queue

    async def upload(
        self,
        source: AsyncReadable,
        filename: str,
        title: str | None = None,
        description: str | None = None,
        department_id: int | None = None,
    ) -> Document:
        file_type = self._file_type(filename)

        if department_id is not None and not self.departments.exists(department_id):
            raise BadRequestError(f"Department {department_id} does not exist")

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

    @staticmethod
    def _file_type(filename: str) -> FileType:
        ext = Path(filename).suffix.lower().lstrip(".")
        try:
            return FileType(ext)
        except ValueError:
            raise UnsupportedFileTypeError("Only .pdf and .txt files are allowed") from None
