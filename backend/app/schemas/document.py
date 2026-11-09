import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.db.models import DocumentStatus, FileType


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_filename: str
    stored_filename: str
    file_type: FileType
    size_bytes: int
    sha256: str
    title: str | None
    description: str | None
    department_id: int | None
    status: DocumentStatus
    uploaded_at: datetime


class DocumentListItem(BaseModel):
    id: uuid.UUID
    filename: str
    status: DocumentStatus
    chunks: int
    uploaded_at: datetime
    size_bytes: int
    department_code: str | None  # None = visible to all departments
    error: str | None            # set when status is "failed"


class DocumentListPage(BaseModel):
    items: list[DocumentListItem]
    total: int   # all matches, ignoring limit/offset
    limit: int
    offset: int
