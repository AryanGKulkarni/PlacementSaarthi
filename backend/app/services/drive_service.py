import uuid

from app.core.exceptions import BadRequestError, ForbiddenError
from app.db.models import Drive, DriveStatus, Role, User
from app.repositories.department_repository import DepartmentRepository
from app.repositories.drive_repository import DriveRepository
from app.schemas.drive import DriveCreate, DriveListPage, DriveOut


class DriveService:
    def __init__(self, drives: DriveRepository, departments: DepartmentRepository):
        self.drives = drives
        self.departments = departments

    def create(self, creator: User, data: DriveCreate) -> DriveOut:
        department_ids = self._allowed_departments(creator, data.department_ids)
        departments = self.departments.get_many(department_ids) if department_ids else []
        if len(departments) != len(department_ids):
            unknown = set(department_ids) - {d.id for d in departments}
            raise BadRequestError(f"Unknown department id(s): {sorted(unknown)}")

        drive = Drive(
            id=uuid.uuid4(),
            **data.model_dump(exclude={"department_ids"}),
            status=DriveStatus.upcoming,
            created_by=creator.id,
            departments=departments,
        )
        try:
            self.drives.add(drive)
            self.drives.commit()
        except BaseException:
            self.drives.rollback()
            raise
        return to_drive_out(self.drives.refresh(drive))

    def list_drives(
        self,
        viewer: User,
        *,
        department_id: int | None,
        status: DriveStatus | None,
        limit: int,
        offset: int,
    ) -> DriveListPage:
        """Admin: every drive (optional department filter).
        Faculty / students: drives open to their department, including drives open to all."""
        if viewer.role is not Role.admin:
            own = _own_department(viewer)
            if department_id is not None and department_id != own:
                raise ForbiddenError("You can only view drives of your own department")
            department_id = own

        drives, total = self.drives.list_page(
            department_id=department_id, status=status, offset=offset, limit=limit
        )
        return DriveListPage(
            items=[to_drive_out(d) for d in drives], total=total, limit=limit, offset=offset
        )

    @staticmethod
    def _allowed_departments(creator: User, requested: list[int]) -> list[int]:
        if creator.role is Role.admin:
            return requested  # empty = open to all departments
        own = _own_department(creator)
        if requested and requested != [own]:
            raise ForbiddenError("Faculty can only create drives for their own department")
        return [own]


def _own_department(user: User) -> int:
    profile = user.faculty_profile if user.role is Role.faculty else user.student_profile
    if profile is None:
        raise ForbiddenError("Your profile has no department")
    return profile.department_id


def to_drive_out(d: Drive) -> DriveOut:
    return DriveOut(
        id=d.id,
        company=d.company,
        job_role=d.job_role,
        description=d.description,
        location=d.location,
        package_lpa=float(d.package_lpa) if d.package_lpa is not None else None,
        min_cgpa=float(d.min_cgpa),
        max_backlogs=d.max_backlogs,
        passing_year=d.passing_year,
        required_skills=d.required_skills or [],
        drive_date=d.drive_date,
        registration_deadline=d.registration_deadline,
        status=d.status,
        departments=sorted(dep.code for dep in d.departments),
        created_at=d.created_at,
    )
