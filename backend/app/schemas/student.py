from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field, field_validator, model_validator

MAX_TAGS = 30

Tag = Annotated[str, Field(min_length=1, max_length=50)]


def _clean_tags(values: list[str] | None) -> list[str] | None:
    """Trim, collapse spaces, drop blanks and case-insensitive duplicates (keeps first spelling)."""
    if values is None:
        return None
    seen: dict[str, str] = {}
    for v in values:
        v = " ".join(v.split())
        if v and v.lower() not in seen:
            seen[v.lower()] = v
    if len(seen) > MAX_TAGS:
        raise ValueError(f"At most {MAX_TAGS} items allowed")
    return list(seen.values())


class StudentProfileUpdate(BaseModel):
    """PATCH body: send only the fields you want to change. Send null to clear an optional field.

    Email and branch (department) are set at registration and can't be changed here.
    """

    full_name: str | None = Field(None, min_length=2, max_length=120)
    roll_no: str | None = Field(None, min_length=1, max_length=30)
    year: int | None = Field(None, ge=1, le=4)
    passing_year: int | None = Field(None, ge=2000, le=2100)

    cgpa: Decimal | None = Field(None, ge=0, le=10, max_digits=4, decimal_places=2)
    active_backlogs: int | None = Field(None, ge=0, le=50)
    tenth_percent: Decimal | None = Field(None, ge=0, le=100, max_digits=5, decimal_places=2)
    twelfth_percent: Decimal | None = Field(None, ge=0, le=100, max_digits=5, decimal_places=2)

    skills: list[Tag] | None = None
    interests: list[Tag] | None = None

    internships: int | None = Field(None, ge=0, le=50)
    projects: int | None = Field(None, ge=0, le=100)
    certifications: int | None = Field(None, ge=0, le=100)

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "roll_no": "CS21B045",
                "year": 4,
                "passing_year": 2027,
                "cgpa": 7.85,
                "active_backlogs": 0,
                "tenth_percent": 91.2,
                "twelfth_percent": 84.6,
                "skills": ["Java", "SQL", "DSA", "React"],
                "interests": ["Backend development"],
                "internships": 1,
                "projects": 3,
                "certifications": 2,
            }]
        }
    }

    @field_validator("full_name")
    @classmethod
    def clean_name(cls, v: str | None) -> str | None:
        return " ".join(v.split()) if v is not None else None

    @field_validator("roll_no")
    @classmethod
    def clean_roll_no(cls, v: str | None) -> str | None:
        return v.strip().upper() if v is not None else None

    @field_validator("skills", "interests")
    @classmethod
    def clean_tags(cls, v: list[str] | None) -> list[str] | None:
        return _clean_tags(v)

    @model_validator(mode="after")
    def required_fields_not_null(self):
        # These columns are NOT NULL: they may be omitted, but not explicitly set to null.
        for name in ("full_name", "active_backlogs", "skills", "interests",
                     "internships", "projects", "certifications"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self


class Completeness(BaseModel):
    percent: int
    filled: int
    total: int
    missing_fields: list[str]


class StudentProfileOut(BaseModel):
    user_id: str
    email: str
    department_id: int
    department_code: str
    department_name: str

    full_name: str
    roll_no: str | None
    year: int | None
    passing_year: int | None

    cgpa: float | None
    active_backlogs: int
    tenth_percent: float | None
    twelfth_percent: float | None

    skills: list[str]
    interests: list[str]

    internships: int
    projects: int
    certifications: int

    has_resume: bool
    completeness: Completeness
    updated_at: datetime
