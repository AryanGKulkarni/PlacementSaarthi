"""Rule-based placement readiness score.

Each parameter gets a 0-100 percent (one progress bar each); the overall score is
the weighted sum. Pure functions: no DB access, easy to unit test.
"""

from collections import Counter
from dataclasses import dataclass

from app.db.models import Drive, StudentProfile
from app.schemas.dashboard import Readiness, ReadinessParam, Status

WEIGHTS = {"cgpa": 40, "skills": 30, "backlogs": 20, "profile": 10}  # must add up to 100

TOP_DEMAND_SKILLS = 8   # skills score = share of the N most-requested skills you have
TARGET_SKILL_COUNT = 6  # fallback when no drive lists skills: N skills = 100%
BACKLOG_PENALTY = 40    # each active backlog removes 40% (0 -> 100, 1 -> 60, 2 -> 20, 3+ -> 0)

# Fields counted for profile completeness. internships/projects/certifications are
# left out: they default to 0, so "not filled" and "none" look the same.
PROFILE_FIELDS: list[tuple[str, str]] = [
    ("roll_no", "Roll number"),
    ("year", "Current year"),
    ("passing_year", "Passing year"),
    ("cgpa", "CGPA"),
    ("tenth_percent", "10th %"),
    ("twelfth_percent", "12th %"),
    ("skills", "Skills"),
    ("interests", "Career interests"),
    ("resume_path", "Resume"),
]


# ---- skill helpers (shared with tips and drive cards) ---------------------------

def norm(skill: str) -> str:
    return " ".join(skill.split()).lower()


@dataclass
class SkillDemand:
    name: str   # display name, as first written in a drive
    drives: int  # how many drives ask for it


def skill_demand(drives: list[Drive]) -> list[SkillDemand]:
    """Skills requested by these drives, most requested first."""
    counts: Counter[str] = Counter()
    display: dict[str, str] = {}
    for drive in drives:
        # dict dedupes a skill listed twice in the same drive
        for key, name in {norm(s): s for s in drive.required_skills or []}.items():
            counts[key] += 1
            display.setdefault(key, name.strip())
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [SkillDemand(display[key], n) for key, n in ranked]


def student_skill_set(profile: StudentProfile) -> set[str]:
    return {norm(s) for s in profile.skills or []}


def missing_profile_fields(profile: StudentProfile) -> list[str]:
    return [label for attr, label in PROFILE_FIELDS if _is_empty(getattr(profile, attr))]


# ---- score ----------------------------------------------------------------------

def compute_readiness(profile: StudentProfile, dept_drives: list[Drive]) -> Readiness:
    """dept_drives: upcoming drives open to the student's department (any eligibility)."""
    params = [
        _cgpa(profile, dept_drives),
        _skills(profile, dept_drives),
        _backlogs(profile, dept_drives),
        _profile(profile),
    ]
    overall = round(sum(p.points for p in params))
    level = "Ready" if overall >= 75 else "Almost ready" if overall >= 50 else "Needs work"
    return Readiness(overall=overall, level=level, params=params)


def _cgpa(profile: StudentProfile, drives: list[Drive]) -> ReadinessParam:
    if profile.cgpa is None:
        return _param("cgpa", "CGPA", 0, "missing", "Add your CGPA to get a score",
                      {"value": None, "max": 10})
    cgpa = float(profile.cgpa)
    meets = sum(1 for d in drives if cgpa >= float(d.min_cgpa))
    detail = f"{cgpa:.2f} / 10"
    if drives:
        detail += f" - meets the cutoff for {meets} of {len(drives)} upcoming drives"
    return _param("cgpa", "CGPA", round(cgpa * 10), None, detail,
                  {"value": cgpa, "max": 10, "meets_cutoff": meets, "upcoming_drives": len(drives)})


def _skills(profile: StudentProfile, drives: list[Drive]) -> ReadinessParam:
    have = student_skill_set(profile)
    demand = skill_demand(drives)[:TOP_DEMAND_SKILLS]

    if demand:  # compare against what upcoming drives actually ask for
        matched = [d.name for d in demand if norm(d.name) in have]
        missing = [d.name for d in demand if norm(d.name) not in have]
        percent = round(100 * len(matched) / len(demand))
        detail = f"You have {len(matched)} of the {len(demand)} most requested skills"
        meta = {"basis": "drive_demand", "count": len(have), "matched": matched, "missing": missing}
    else:  # no drive lists skills yet -> reward having a reasonable number of them
        percent = round(100 * min(len(have), TARGET_SKILL_COUNT) / TARGET_SKILL_COUNT)
        detail = f"{len(have)} skills listed (aim for {TARGET_SKILL_COUNT}+)"
        meta = {"basis": "skill_count", "count": len(have), "target": TARGET_SKILL_COUNT,
                "matched": [], "missing": []}

    status = "missing" if not have else None
    if not have:
        detail = "Add your skills to get a score"
    return _param("skills", "Skills", percent, status, detail, meta)


def _backlogs(profile: StudentProfile, drives: list[Drive]) -> ReadinessParam:
    n = profile.active_backlogs or 0
    allowed = sum(1 for d in drives if n <= d.max_backlogs)
    detail = "No active backlogs" if n == 0 else f"{n} active backlog{'s' if n > 1 else ''}"
    if drives and n > 0:
        detail += f" - {allowed} of {len(drives)} upcoming drives allow this"
    return _param("backlogs", "Backlogs", max(0, 100 - BACKLOG_PENALTY * n), None, detail,
                  {"value": n, "drives_allowing": allowed, "upcoming_drives": len(drives)})


def _profile(profile: StudentProfile) -> ReadinessParam:
    missing = missing_profile_fields(profile)
    total = len(PROFILE_FIELDS)
    filled = total - len(missing)
    detail = "Profile complete" if not missing else f"{filled} of {total} fields filled"
    return _param("profile", "Profile completeness", round(100 * filled / total), None, detail,
                  {"filled": filled, "total": total, "missing_fields": missing})


def _param(key: str, label: str, percent: int, status: Status | None, detail: str,
           meta: dict) -> ReadinessParam:
    weight = WEIGHTS[key]
    return ReadinessParam(
        key=key,
        label=label,
        percent=percent,
        weight=weight,
        points=round(percent * weight / 100, 1),
        status=status or _status(percent),
        detail=detail,
        meta=meta,
    )


def _status(percent: int) -> Status:
    return "good" if percent >= 75 else "average" if percent >= 50 else "low"


def _is_empty(value) -> bool:
    return value is None or value == "" or value == [] or value == ()
