import logging
from pathlib import Path

from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError, UnsupportedFileTypeError
from app.db.models import FileType, StudentProfile, User
from app.repositories.student_repository import StudentRepository
from app.schemas.student import Completeness, StudentProfileOut, StudentProfileUpdate
from app.services import file_storage
from app.services.auth_service import is_unique_violation
from app.services.file_storage import AsyncReadable
from app.services.readiness import PROFILE_FIELDS, missing_profile_fields

log = logging.getLogger(__name__)


class StudentService:
    def __init__(self, students: StudentRepository):
        self.students = students

    # ---- profile ----------------------------------------------------------------

    def get_profile(self, user: User) -> StudentProfileOut:
        return to_profile_out(user, self._profile(user))

    def update_profile(self, user: User, data: StudentProfileUpdate) -> StudentProfileOut:
        profile = self._profile(user)
        changes = data.model_dump(exclude_unset=True)  # only fields the client sent

        roll_no = changes.get("roll_no")
        if roll_no and self.students.roll_no_taken(roll_no, exclude_user_id=user.id):
            raise ConflictError("This roll number is already used by another student")

        for field, value in changes.items():
            setattr(profile, field, value)

        try:
            self.students.commit()
        except IntegrityError as exc:  # race on roll_no between the check and the commit
            self.students.rollback()
            if is_unique_violation(exc):
                raise ConflictError("This roll number is already used by another student") from exc
            raise
        self.students.refresh(profile)  # pick up updated_at from the DB
        return to_profile_out(user, profile)

    # ---- resume -----------------------------------------------------------------

    async def upload_resume(self, user: User, source: AsyncReadable, filename: str) -> StudentProfileOut:
        profile = self._profile(user)
        if Path(filename).suffix.lower() != ".pdf":
            raise UnsupportedFileTypeError("Resume must be a PDF")

        # Checks %PDF- header and size while streaming; one file per student, replaced on re-upload.
        temp = await file_storage.save_to_temp(
            source, FileType.pdf, max_mb=settings.max_resume_mb, directory=settings.resume_dir
        )
        try:
            file_storage.promote(temp, f"{user.id}.pdf", directory=settings.resume_dir)
        except BaseException:
            temp.discard()
            raise

        profile.resume_path = f"resumes/{user.id}.pdf"  # relative to DATA_DIR
        self.students.commit()
        self.students.refresh(profile)
        return to_profile_out(user, profile)

    def resume_file(self, user: User) -> Path:
        path = _resume_path(self._profile(user))
        if path is None or not path.is_file():
            raise NotFoundError("No resume uploaded")
        return path

    def delete_resume(self, user: User) -> StudentProfileOut:
        profile = self._profile(user)
        path = _resume_path(profile)
        profile.resume_path = None
        self.students.commit()
        if path is not None:
            path.unlink(missing_ok=True)  # after commit: never point the DB at a missing file
        self.students.refresh(profile)
        return to_profile_out(user, profile)

    # ---- helpers ----------------------------------------------------------------

    def _profile(self, user: User) -> StudentProfile:
        profile = self.students.get_profile(user.id)
        if profile is None:
            raise NotFoundError("Student profile not found")
        return profile


def _resume_path(profile: StudentProfile) -> Path | None:
    return settings.data_dir / profile.resume_path if profile.resume_path else None


def to_profile_out(user: User, p: StudentProfile) -> StudentProfileOut:
    missing = missing_profile_fields(p)
    total = len(PROFILE_FIELDS)
    filled = total - len(missing)
    return StudentProfileOut(
        user_id=str(user.id),
        email=user.email,
        department_id=p.department_id,
        department_code=p.department.code,
        department_name=p.department.name,
        full_name=p.full_name,
        roll_no=p.roll_no,
        year=p.year,
        passing_year=p.passing_year,
        cgpa=float(p.cgpa) if p.cgpa is not None else None,
        active_backlogs=p.active_backlogs or 0,
        tenth_percent=float(p.tenth_percent) if p.tenth_percent is not None else None,
        twelfth_percent=float(p.twelfth_percent) if p.twelfth_percent is not None else None,
        skills=p.skills or [],
        interests=p.interests or [],
        internships=p.internships or 0,
        projects=p.projects or 0,
        certifications=p.certifications or 0,
        has_resume=p.resume_path is not None,
        completeness=Completeness(
            percent=round(100 * filled / total), filled=filled, total=total, missing_fields=missing
        ),
        updated_at=p.updated_at,
    )
