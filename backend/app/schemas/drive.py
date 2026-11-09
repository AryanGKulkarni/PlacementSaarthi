import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field, field_validator, model_validator

from app.db.models import DriveStatus

Skill = Annotated[str, Field(min_length=1, max_length=50)]


class DriveCreate(BaseModel):
    company: str = Field(min_length=1, max_length=120)
    job_role: str = Field(min_length=1, max_length=120)
    description: str | None = Field(None, max_length=5000)
    location: str | None = Field(None, max_length=120)
    package_lpa: Decimal | None = Field(None, ge=0, max_digits=6, decimal_places=2)

    min_cgpa: Decimal = Field(Decimal("0"), ge=0, le=10, max_digits=4, decimal_places=2)
    max_backlogs: int = Field(0, ge=0, le=50)
    passing_year: int | None = Field(None, ge=2000, le=2100, description="Batch, e.g. 2027. Omit for any.")
    required_skills: list[Skill] = Field(default_factory=list, max_length=30)

    drive_date: date
    registration_deadline: date | None = None

    department_ids: list[Annotated[int, Field(gt=0)]] = Field(
        default_factory=list,
        description="Eligible departments. Empty = all departments (admin only). "
                    "Faculty: omit, or send only their own department.",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "company": "NovaByte Technologies",
                "job_role": "Associate Software Engineer",
                "location": "Pune",
                "package_lpa": 7.5,
                "min_cgpa": 7.0,
                "max_backlogs": 0,
                "passing_year": 2027,
                "required_skills": ["Java", "SQL", "DSA", "Git"],
                "drive_date": "2026-12-01",
                "registration_deadline": "2026-11-20",
                "department_ids": [1, 2, 3],
            }]
        }
    }

    @field_validator("company", "job_role", "location")
    @classmethod
    def clean_text(cls, v: str | None) -> str | None:
        return " ".join(v.split()) if v is not None else None

    @field_validator("required_skills")
    @classmethod
    def clean_skills(cls, v: list[str]) -> list[str]:
        """Trim and drop case-insensitive duplicates, keeping the first spelling."""
        seen: dict[str, str] = {}
        for s in v:
            s = " ".join(s.split())
            if s and s.lower() not in seen:
                seen[s.lower()] = s
        return list(seen.values())

    @field_validator("department_ids")
    @classmethod
    def unique_departments(cls, v: list[int]) -> list[int]:
        return sorted(set(v))

    @model_validator(mode="after")
    def check_dates(self):
        if self.drive_date < date.today():
            raise ValueError("drive_date cannot be in the past")
        if self.registration_deadline and self.registration_deadline > self.drive_date:
            raise ValueError("registration_deadline must be on or before drive_date")
        return self


class DriveOut(BaseModel):
    id: uuid.UUID
    company: str
    job_role: str
    description: str | None
    location: str | None
    package_lpa: float | None
    min_cgpa: float
    max_backlogs: int
    passing_year: int | None
    required_skills: list[str]
    drive_date: date
    registration_deadline: date | None
    status: DriveStatus
    departments: list[str]  # department codes; empty = open to all departments
    created_at: datetime


class DriveListPage(BaseModel):
    items: list[DriveOut]
    total: int   # all matches, ignoring limit/offset
    limit: int
    offset: int
