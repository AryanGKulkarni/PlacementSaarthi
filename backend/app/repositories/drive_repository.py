from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.db.models import Department, Drive, DriveStatus
from app.repositories.base import BaseRepository


class DriveRepository(BaseRepository):
    def upcoming_for_department(
        self, department_id: int, passing_year: int | None, today: date
    ) -> list[Drive]:
        """Upcoming drives open to this department (a drive with no departments is open to all),
        for the student's batch if both sides have one. Soonest first."""
        stmt = (
            select(Drive)
            .options(selectinload(Drive.departments))
            .where(
                Drive.status == DriveStatus.upcoming,
                Drive.drive_date >= today,
                or_(
                    Drive.departments.any(Department.id == department_id),
                    ~Drive.departments.any(),
                ),
            )
            .order_by(Drive.drive_date, Drive.company)
        )
        if passing_year is not None:
            stmt = stmt.where(
                or_(Drive.passing_year.is_(None), Drive.passing_year == passing_year)
            )
        return list(self.db.scalars(stmt))

    def add(self, drive: Drive) -> Drive:
        self.db.add(drive)
        self.db.flush()
        return drive

    def refresh(self, drive: Drive) -> Drive:
        self.db.refresh(drive)
        return drive

    def list_page(
        self,
        *,
        department_id: int | None,
        status: DriveStatus | None,
        offset: int,
        limit: int,
    ) -> tuple[list[Drive], int]:
        """Soonest drive first. department_id: drives open to that department, including
        drives open to all. None -> every drive."""
        filters = []
        if department_id is not None:
            filters.append(
                or_(Drive.departments.any(Department.id == department_id), ~Drive.departments.any())
            )
        if status is not None:
            filters.append(Drive.status == status)

        total = self.db.scalar(select(func.count()).select_from(Drive).where(*filters)) or 0
        stmt = (
            select(Drive)
            .options(selectinload(Drive.departments))
            .where(*filters)
            .order_by(Drive.drive_date, Drive.company, Drive.id)
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.scalars(stmt)), total
