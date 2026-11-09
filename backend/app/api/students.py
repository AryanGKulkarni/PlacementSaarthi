import uuid

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import FileResponse

from app.core.deps import get_student_service, require_roles
from app.db.models import Role, User
from app.schemas.student import StudentDetail, StudentListPage, StudentProfileOut, StudentProfileUpdate
from app.services.student_service import StudentService

router = APIRouter(prefix="/api/students", tags=["students"])

student_only = require_roles(Role.student)
staff_only = require_roles(Role.faculty, Role.admin)

# The /me/... routes are declared before /{student_id} so "me" is never parsed as an id.


@router.get("/me/profile", response_model=StudentProfileOut)
def get_profile(
    user: User = Depends(student_only),
    service: StudentService = Depends(get_student_service),
):
    """The logged-in student's profile, with completeness for the progress card."""
    return service.get_profile(user)


@router.patch("/me/profile", response_model=StudentProfileOut)
def update_profile(
    data: StudentProfileUpdate,
    user: User = Depends(student_only),
    service: StudentService = Depends(get_student_service),
):
    """Partial update: only the fields sent are changed. Email and branch can't be changed."""
    return service.update_profile(user, data)


@router.put("/me/resume", response_model=StudentProfileOut)
async def upload_resume(
    file: UploadFile = File(..., description="PDF, max 5 MB. Replaces any existing resume."),
    user: User = Depends(student_only),
    service: StudentService = Depends(get_student_service),
):
    return await service.upload_resume(user, file, file.filename or "")


@router.get("/me/resume", response_class=FileResponse)
def download_resume(
    user: User = Depends(student_only),
    service: StudentService = Depends(get_student_service),
):
    path = service.resume_file(user)
    return FileResponse(
        path,
        media_type="application/pdf",
        filename="resume.pdf",
        content_disposition_type="inline",  # open in the browser's PDF viewer
    )


@router.delete("/me/resume", response_model=StudentProfileOut)
def delete_resume(
    user: User = Depends(student_only),
    service: StudentService = Depends(get_student_service),
):
    return service.delete_resume(user)


# ---- faculty / admin ----------------------------------------------------------------

@router.get("", response_model=StudentListPage)
def list_students(
    search: str | None = Query(None, max_length=100, description="Part of the student's name"),
    department_id: int | None = Query(
        None, gt=0, description="Admin: filter by department. Faculty always see only their own."
    ),
    limit: int = Query(20, ge=1, le=100, description="Max students to return"),
    offset: int = Query(0, ge=0, description="Number of students to skip"),
    user: User = Depends(staff_only),
    service: StudentService = Depends(get_student_service),
):
    """Students list, sorted by name. Faculty: own department only. Admin: all departments."""
    return service.list_students(
        user, search=search, department_id=department_id, limit=limit, offset=offset
    )


@router.get("/{student_id}", response_model=StudentDetail)
def student_detail(
    student_id: uuid.UUID,
    user: User = Depends(staff_only),
    service: StudentService = Depends(get_student_service),
):
    """'View details': full profile + placement readiness score."""
    return service.student_detail(user, student_id)
