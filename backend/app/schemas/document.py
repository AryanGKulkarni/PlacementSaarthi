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
