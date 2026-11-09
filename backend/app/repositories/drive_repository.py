from datetime import date

from sqlalchemy import or_, select
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
