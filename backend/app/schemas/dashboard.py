import uuid
from datetime import date
from typing import Any, Literal

from pydantic import BaseModel

Status = Literal["good", "average", "low", "missing"]


class ReadinessParam(BaseModel):
    key: Literal["cgpa", "skills", "backlogs", "profile"]
    label: str
    percent: int          # 0-100, drives the progress bar
    weight: int           # share of the overall score, weights add up to 100
    points: float         # percent * weight / 100 -> contribution to the overall score
    status: Status
    detail: str           # one-line explanation shown under the bar
    meta: dict[str, Any]  # raw numbers for the UI (value, matched skills, missing fields...)


class Readiness(BaseModel):
    overall: int          # 0-100
    level: Literal["Ready", "Almost ready", "Needs work"]
    params: list[ReadinessParam]


class Tip(BaseModel):
    type: Literal["profile", "skill_gap", "eligibility_gap", "deadline", "general"]
    text: str
    action: str | None = None  # frontend route the tip links to


class DriveCard(BaseModel):
    id: uuid.UUID
    company: str
    job_role: str
    location: str | None
    package_lpa: float | None
    min_cgpa: float
    max_backlogs: int
    drive_date: date
    registration_deadline: date | None
    days_to_deadline: int | None
    required_skills: list[str]
    matched_skills: list[str]
    missing_skills: list[str]
    skill_match_percent: int | None  # None when the drive lists no skills


class StudentInfo(BaseModel):
    full_name: str
    department_code: str
    passing_year: int | None


class StudentDashboard(BaseModel):
    student: StudentInfo
    readiness: Readiness
    tips: list[Tip]
    eligible_drives: list[DriveCard]
