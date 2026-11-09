import uuid

from sqlalchemy import exists, select

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
