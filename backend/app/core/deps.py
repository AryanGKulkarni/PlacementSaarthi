"""FastAPI dependency wiring: session -> repositories -> services."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.messaging.ingest_queue import IngestQueue
from app.repositories.department_repository import DepartmentRepository
from app.repositories.document_repository import DocumentRepository
from app.services.document_service import DocumentService


def get_document_service(db: Session = Depends(get_db)) -> DocumentService:
    return DocumentService(DocumentRepository(db), DepartmentRepository(db), IngestQueue())
