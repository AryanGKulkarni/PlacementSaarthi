from datetime import date

from app.db.models import Drive, StudentProfile

# Reasons a student can't apply to a drive (department and batch are already
# filtered in the query, see DriveRepository.upcoming_for_department).
CGPA = "cgpa"                  # below min_cgpa
CGPA_MISSING = "cgpa_missing"  # profile has no CGPA but the drive has a cutoff
BACKLOGS = "backlogs"          # more active backlogs than allowed
CLOSED = "closed"              # registration deadline has passed


def blockers(profile: StudentProfile, drive: Drive, today: date) -> list[str]:
    """Empty list = eligible."""
    reasons = []
    min_cgpa = float(drive.min_cgpa or 0)
    if profile.cgpa is None:
        if min_cgpa > 0:
            reasons.append(CGPA_MISSING)
    elif float(profile.cgpa) < min_cgpa:
        reasons.append(CGPA)
    if (profile.active_backlogs or 0) > drive.max_backlogs:
        reasons.append(BACKLOGS)
    if drive.registration_deadline is not None and drive.registration_deadline < today:
        reasons.append(CLOSED)
    return reasons
