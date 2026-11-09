from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse

from app.core.deps import get_student_service, require_roles
from app.db.models import Role, User
from app.schemas.student import StudentProfileOut, StudentProfileUpdate
from app.services.student_service import StudentService

router = APIRouter(prefix="/api/students/me", tags=["students"])

student_only = require_roles(Role.student)


@router.get("/profile", response_model=StudentProfileOut)
def get_profile(
    user: User = Depends(student_only),
    service: StudentService = Depends(get_student_service),
):
    """The logged-in student's profile, with completeness for the progress card."""
    return service.get_profile(user)


@router.patch("/profile", response_model=StudentProfileOut)
def update_profile(
    data: StudentProfileUpdate,
    user: User = Depends(student_only),
    service: StudentService = Depends(get_student_service),
):
    """Partial update: only the fields sent are changed. Email and branch can't be changed."""
    return service.update_profile(user, data)


@router.put("/resume", response_model=StudentProfileOut)
async def upload_resume(
    file: UploadFile = File(..., description="PDF, max 5 MB. Replaces any existing resume."),
    user: User = Depends(student_only),
    service: StudentService = Depends(get_student_service),
):
    return await service.upload_resume(user, file, file.filename or "")


@router.get("/resume", response_class=FileResponse)
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


@router.delete("/resume", response_model=StudentProfileOut)
def delete_resume(
    user: User = Depends(student_only),
    service: StudentService = Depends(get_student_service),
):
    return service.delete_resume(user)
