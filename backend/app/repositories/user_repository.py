import uuid

from sqlalchemy import exists, select

from app.db.models import FacultyProfile, Role, User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    def get(self, user_id: uuid.UUID) -> User | None:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email.lower()))

    def email_exists(self, email: str) -> bool:
        return bool(self.db.scalar(select(exists().where(User.email == email.lower()))))

    def admin_exists(self) -> bool:
        return bool(self.db.scalar(select(exists().where(User.role == Role.admin))))

    def employee_id_exists(self, employee_id: str) -> bool:
        return bool(
            self.db.scalar(select(exists().where(FacultyProfile.employee_id == employee_id)))
        )

    def add(self, user: User) -> User:
        """Stage a user (with its profile, via cascade) and flush to surface constraint errors."""
        self.db.add(user)
        self.db.flush()
        return user
