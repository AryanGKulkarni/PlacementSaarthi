"""Rule-based dashboard tips.

Rules run in a fixed priority order and each rule adds at most one tip, so the
student never sees three tips of the same kind. Gaps are filled with general tips.
"""

import uuid
from datetime import date
from urllib.parse import quote

from app.db.models import Drive, StudentProfile
from app.schemas.dashboard import Tip
from app.services import eligibility as el
from app.services.readiness import missing_profile_fields, norm, skill_demand, student_skill_set

MAX_TIPS = 3
DEADLINE_WINDOW_DAYS = 7

GENERAL_TIPS = [
    Tip(type="general", text="Practise aptitude and reasoning daily - most drives start with an online test."),
    Tip(type="general", text="Do a mock interview and prepare a one-minute introduction about yourself."),
    Tip(type="general", text="Keep your resume to one page and add your latest projects to it."),
    Tip(type="general", text="Ask the assistant about a company's selection process before its drive.",
        action="/chat"),
]


def build_tips(
    profile: StudentProfile,
    dept_drives: list[Drive],
    blockers: dict[uuid.UUID, list[str]],
    eligible: list[Drive],
    today: date,
) -> list[Tip]:
    open_drives = [d for d in dept_drives if el.CLOSED not in blockers[d.id]]
    rules = [  # priority order
        lambda: _profile_tip(profile),
        lambda: _skill_gap_tip(profile, open_drives),
        lambda: _eligibility_gap_tip(profile, open_drives, blockers),
        lambda: _deadline_tip(eligible, today),
    ]

    tips: list[Tip] = []
    for rule in rules:
        tip = rule()
        if tip is not None:
            tips.append(tip)
        if len(tips) == MAX_TIPS:
            return tips
    return tips + GENERAL_TIPS[: MAX_TIPS - len(tips)]


def _profile_tip(profile: StudentProfile) -> Tip | None:
    if profile.cgpa is None:
        return Tip(type="profile", action="/profile",
                   text="Add your CGPA - it decides which drives you are eligible for.")
    if not profile.skills:
        return Tip(type="profile", action="/profile",
                   text="Add your technical skills so we can match you with drives.")
    missing = missing_profile_fields(profile)
    if not missing:
        return None
    listed = ", ".join(missing[:2])
    more = f" and {len(missing) - 2} more" if len(missing) > 2 else ""
    return Tip(type="profile", action="/profile",
               text=f"Complete your profile: add {listed}{more}.")


def _skill_gap_tip(profile: StudentProfile, drives: list[Drive]) -> Tip | None:
    have = student_skill_set(profile)
    gap = next((d for d in skill_demand(drives) if norm(d.name) not in have), None)
    if gap is None:
        return None
    drives_text = f"{gap.drives} upcoming drives" if gap.drives > 1 else "an upcoming drive"
    return Tip(
        type="skill_gap",
        text=f"Learn {gap.name} - it is asked for by {drives_text} for your branch.",
        action=f"/chat?q={quote(f'How should I learn {gap.name} for placements?')}",
    )


def _eligibility_gap_tip(
    profile: StudentProfile, drives: list[Drive], blockers: dict[uuid.UUID, list[str]]
) -> Tip | None:
    """Drives blocked by exactly one thing the student can improve."""
    if profile.cgpa is None:
        return None  # the profile tip already asks for CGPA
    backlog_only = [d for d in drives if blockers[d.id] == [el.BACKLOGS]]
    cgpa_only = [d for d in drives if blockers[d.id] == [el.CGPA]]

    if backlog_only and len(backlog_only) >= len(cgpa_only):
        n = profile.active_backlogs
        k = len(backlog_only)
        return Tip(
            type="eligibility_gap", action="/drives",
            text=f"Clearing your {n} active backlog{'s' if n > 1 else ''} would make you "
                 f"eligible for {k} more drive{'s' if k > 1 else ''}.",
        )
    if cgpa_only:
        nearest = min(cgpa_only, key=lambda d: d.min_cgpa)
        target = float(nearest.min_cgpa)
        gap = target - float(profile.cgpa)
        unlocks = sum(1 for d in cgpa_only if float(d.min_cgpa) <= target)
        extra = f" and {unlocks - 1} other drive{'s' if unlocks > 2 else ''}" if unlocks > 1 else ""
        return Tip(
            type="eligibility_gap", action=f"/drives/{nearest.id}",
            text=f"You are {gap:.2f} CGPA short of {nearest.company} (needs {target:g}). "
                 f"Reaching {target:g} unlocks it{extra}.",
        )
    return None


def _deadline_tip(eligible: list[Drive], today: date) -> Tip | None:
    closing = [
        d for d in eligible
        if d.registration_deadline is not None
        and 0 <= (d.registration_deadline - today).days <= DEADLINE_WINDOW_DAYS
    ]
    if not closing:
        return None
    drive = min(closing, key=lambda d: d.registration_deadline)
    days = (drive.registration_deadline - today).days
    when = "today" if days == 0 else "tomorrow" if days == 1 else f"in {days} days"
    return Tip(type="deadline", action=f"/drives/{drive.id}",
               text=f"Register for {drive.company} ({drive.job_role}) - registration closes {when}.")
