import uuid

from sqlalchemy import exists, func, select
from sqlalchemy.orm import contains_eager

from app.db.models import StudentProfile
from app.repositories.base import BaseRepository


class StudentRepository(BaseRepository):
    def get_profile(self, user_id: uuid.UUID) -> StudentProfile | None:
        return self.db.get(StudentProfile, user_id)

    def roll_no_taken(self, roll_no: str, exclude_user_id: uuid.UUID) -> bool:
        return bool(
            self.db.scalar(
                select(
                    exists().where(
                        StudentProfile.roll_no == roll_no,
                        StudentProfile.user_id != exclude_user_id,
                    )
                )
            )
        )

    def flush(self) -> None:
        self.db.flush()

    def refresh(self, profile: StudentProfile) -> StudentProfile:
        self.db.refresh(profile)
        return profile

    def list_profiles(
        self,
        *,
        department_id: int | None,
        search: str | None,
        offset: int,
        limit: int,
    ) -> tuple[list[StudentProfile], int]:
        """Student profiles (with user + department loaded), sorted by name. Returns (page, total)."""
        filters = []
        if department_id is not None:
            filters.append(StudentProfile.department_id == department_id)
        if search:
            filters.append(StudentProfile.full_name.ilike(f"%{_escape_like(search)}%", escape="!"))

        total = self.db.scalar(select(func.count()).select_from(StudentProfile).where(*filters)) or 0
        stmt = (
            select(StudentProfile)
            .join(StudentProfile.user)
            .join(StudentProfile.department)
            .options(contains_eager(StudentProfile.user), contains_eager(StudentProfile.department))
            .where(*filters)
            .order_by(func.lower(StudentProfile.full_name), StudentProfile.user_id)
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.scalars(stmt)), total


def _escape_like(text: str) -> str:
    """Make %, _ and the escape char itself match literally in LIKE (escape char is '!')."""
    return text.replace("!", "!!").replace("%", "!%").replace("_", "!_")
