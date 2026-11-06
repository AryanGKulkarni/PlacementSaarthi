from sqlalchemy import select

from app.db.models import Department
from app.repositories.base import BaseRepository


class DepartmentRepository(BaseRepository):
    def get(self, department_id: int) -> Department | None:
        return self.db.get(Department, department_id)

    def exists(self, department_id: int) -> bool:
        return self.get(department_id) is not None

    def is_empty(self) -> bool:
        return self.db.scalar(select(Department.id).limit(1)) is None

    def add_many(self, departments: list[Department]) -> None:
        self.db.add_all(departments)
