from datetime import date

from app.core.exceptions import NotFoundError
from app.db.models import Drive, StudentProfile, User
from app.repositories.drive_repository import DriveRepository
from app.schemas.dashboard import DriveCard, StudentDashboard, StudentInfo
from app.services.eligibility import blockers
from app.services.readiness import compute_readiness, norm, student_skill_set
from app.services.tips import build_tips


class DashboardService:
    def __init__(self, drives: DriveRepository):
        self.drives = drives

    def student_dashboard(self, user: User, today: date | None = None) -> StudentDashboard:
        profile = user.student_profile
        if profile is None:
            raise NotFoundError("Student profile not found")
        today = today or date.today()

        # One query; everything below is computed in memory from these drives.
        dept_drives = self.drives.upcoming_for_department(
            profile.department_id, profile.passing_year, today
        )
        reasons = {d.id: blockers(profile, d, today) for d in dept_drives}
        eligible = [d for d in dept_drives if not reasons[d.id]]

        return StudentDashboard(
            student=StudentInfo(
                full_name=profile.full_name,
                department_code=profile.department.code,
                passing_year=profile.passing_year,
            ),
            readiness=compute_readiness(profile, dept_drives),
            tips=build_tips(profile, dept_drives, reasons, eligible, today),
            eligible_drives=[_drive_card(d, profile, today) for d in eligible],
        )


def _drive_card(drive: Drive, profile: StudentProfile, today: date) -> DriveCard:
    have = student_skill_set(profile)
    required = drive.required_skills or []
    matched = [s for s in required if norm(s) in have]
    missing = [s for s in required if norm(s) not in have]
    return DriveCard(
        id=drive.id,
        company=drive.company,
        job_role=drive.job_role,
        location=drive.location,
        package_lpa=float(drive.package_lpa) if drive.package_lpa is not None else None,
        min_cgpa=float(drive.min_cgpa),
        max_backlogs=drive.max_backlogs,
        drive_date=drive.drive_date,
        registration_deadline=drive.registration_deadline,
        days_to_deadline=(
            (drive.registration_deadline - today).days if drive.registration_deadline else None
        ),
        required_skills=required,
        matched_skills=matched,
        missing_skills=missing,
        skill_match_percent=round(100 * len(matched) / len(required)) if required else None,
    )
