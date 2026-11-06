from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from app.core.deps import get_document_service
from app.schemas.document import DocumentOut
from app.services.document_service import DocumentService

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    title: str | None = Form(None, max_length=200),
    description: str | None = Form(None),
    department_id: int | None = Form(None, description="Omit for a document visible to all departments"),
    service: DocumentService = Depends(get_document_service),
):
    return await service.upload(
        source=file,
        filename=file.filename or "",
        title=title,
        description=description,
        department_id=department_id,
    )
