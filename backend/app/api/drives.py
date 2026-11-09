from fastapi import APIRouter, Depends, Query, status

from app.core.deps import get_current_user, get_drive_service, require_roles
from app.db.models import DriveStatus, Role, User
from app.schemas.drive import DriveCreate, DriveListPage, DriveOut
from app.services.drive_service import DriveService

router = APIRouter(prefix="/api/drives", tags=["drives"])


@router.post("", response_model=DriveOut, status_code=status.HTTP_201_CREATED)
def create_drive(
    data: DriveCreate,
    user: User = Depends(require_roles(Role.faculty, Role.admin)),
    service: DriveService = Depends(get_drive_service),
):
    """Faculty: drive is for their own department. Admin: any departments, empty = all."""
    return service.create(user, data)


@router.get("", response_model=DriveListPage)
def list_drives(
    department_id: int | None = Query(
        None, gt=0, description="Admin: filter by department. Others always see only their own."
    ),
    status_filter: DriveStatus | None = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    service: DriveService = Depends(get_drive_service),
):
    """Drives sorted by date. Faculty/students: their department's drives + drives open to all."""
    return service.list_drives(
        user, department_id=department_id, status=status_filter, limit=limit, offset=offset
    )
