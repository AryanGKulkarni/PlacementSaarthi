from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status

from app.core.deps import get_document_service, require_roles
from app.db.models import Role, User
from app.schemas.document import DocumentListPage, DocumentOut
from app.services.document_service import DocumentService

router = APIRouter(prefix="/api/documents", tags=["documents"])

staff_only = require_roles(Role.faculty, Role.admin)


@router.get("", response_model=DocumentListPage)
def list_documents(
    department_id: int | None = Query(
        None, gt=0, description="Admin: filter by department. Faculty always see only their own."
    ),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(staff_only),
    service: DocumentService = Depends(get_document_service),
):
    """Uploaded documents, newest first. Faculty: own department + documents shared with all."""
    return service.list_documents(user, department_id=department_id, limit=limit, offset=offset)


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    title: str | None = Form(None, max_length=200),
    description: str | None = Form(None),
    user: User = Depends(staff_only),
    service: DocumentService = Depends(get_document_service),
):
    """Faculty: document is visible to their department only. Admin: visible to all departments."""
    return await service.upload(
        source=file,
        filename=file.filename or "",
        uploader=user,
        title=title,
        description=description,
    )
