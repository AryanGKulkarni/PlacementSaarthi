import uuid
from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.db.models import Designation, Role


def _strip(value: str) -> str:
    return " ".join(value.split())


class _RegisterBase(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    full_name: str = Field(min_length=2, max_length=120)
    department_id: int = Field(gt=0)

    @field_validator("email")
    @classmethod
    def lower_email(cls, v: str) -> str:
        return v.lower()

    @field_validator("password")
    @classmethod
    def password_bytes(cls, v: str) -> str:
        if len(v.encode()) > 72:  # bcrypt only uses the first 72 bytes
            raise ValueError("Password is too long (max 72 bytes)")
        return v

    @field_validator("full_name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        return _strip(v)


class StudentRegister(_RegisterBase):
    """Students only need basic details + department; the rest of the profile is completed later."""

    role: Literal["student"]


class FacultyRegister(_RegisterBase):
    """Faculty must provide their full profile at registration."""

    role: Literal["faculty"]
    employee_id: str = Field(min_length=1, max_length=30)
    designation: Designation
    phone: str = Field(pattern=r"^\+?[0-9]{10,13}$", examples=["9876543210"])
    joined_on: date

    @field_validator("employee_id")
    @classmethod
    def clean_employee_id(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("joined_on")
    @classmethod
    def not_in_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("joined_on cannot be in the future")
        return v


RegisterRequest = Annotated[StudentRegister | FacultyRegister, Field(discriminator="role")]


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=1024)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    role: Role
    is_active: bool
    full_name: str | None = None
    department_id: int | None = None


class TokenOut(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int  # seconds
    user: UserOut
