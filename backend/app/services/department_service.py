from app.db.models import Department
from app.repositories.department_repository import DepartmentRepository

DEFAULT_DEPARTMENTS = [
    ("CSE", "Computer Science & Engineering"),
    ("IT", "Information Technology"),
    ("ENTC", "Electronics & Telecommunication"),
    ("MECH", "Mechanical Engineering"),
    ("CIVIL", "Civil Engineering"),
]


class DepartmentService:
    def __init__(self, departments: DepartmentRepository):
        self.departments = departments

    def seed_defaults(self) -> None:
        """Insert the default departments on first startup."""
        if self.departments.is_empty():
            self.departments.add_many([Department(code=c, name=n) for c, n in DEFAULT_DEPARTMENTS])
            self.departments.commit()
