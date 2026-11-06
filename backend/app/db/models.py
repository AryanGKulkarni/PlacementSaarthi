import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Table,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Role(str, enum.Enum):
    student = "student"
    faculty = "faculty"
    admin = "admin"


class Designation(str, enum.Enum):
    assistant_professor = "assistant_professor"
    associate_professor = "associate_professor"
    professor = "professor"
    hod = "hod"
    tpo = "tpo"  # Training & Placement Officer


class DriveStatus(str, enum.Enum):
    upcoming = "upcoming"
    ongoing = "ongoing"
    completed = "completed"
    cancelled = "cancelled"


class FileType(str, enum.Enum):
    pdf = "pdf"
    txt = "txt"


class DocumentStatus(str, enum.Enum):
    uploaded = "uploaded"      # file saved, not yet ingested
    processing = "processing"  # chunking/embedding in progress
    indexed = "indexed"        # chunks stored in ChromaDB
    failed = "failed"          # see Document.error


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(10), unique=True)
    name: Mapped[str] = mapped_column(String(100))


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(
        Enum(Role, name="user_role"), default=Role.student
    )
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    student_profile: Mapped["StudentProfile | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    faculty_profile: Mapped["FacultyProfile | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class StudentProfile(Base):
    __tablename__ = "student_profiles"
    __table_args__ = (
        CheckConstraint("cgpa BETWEEN 0 AND 10", name="cgpa_range"),
        CheckConstraint("year BETWEEN 1 AND 4", name="year_range"),
        CheckConstraint("active_backlogs >= 0", name="backlogs_nonneg"),
        CheckConstraint("tenth_percent BETWEEN 0 AND 100", name="tenth_range"),
        CheckConstraint("twelfth_percent BETWEEN 0 AND 100", name="twelfth_range"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), index=True)

    full_name: Mapped[str] = mapped_column(String(120))
    roll_no: Mapped[str | None] = mapped_column(String(30), unique=True)
    year: Mapped[int] = mapped_column(SmallInteger)
    passing_year: Mapped[int | None] = mapped_column(SmallInteger)

    cgpa: Mapped[Decimal] = mapped_column(Numeric(4, 2))
    active_backlogs: Mapped[int] = mapped_column(SmallInteger, default=0)
    tenth_percent: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    twelfth_percent: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))

    skills: Mapped[list[str]] = mapped_column(ARRAY(String(50)), default=list)
    interests: Mapped[list[str]] = mapped_column(ARRAY(String(50)), default=list)

    internships: Mapped[int] = mapped_column(SmallInteger, default=0)
    projects: Mapped[int] = mapped_column(SmallInteger, default=0)
    certifications: Mapped[int] = mapped_column(SmallInteger, default=0)
    resume_path: Mapped[str | None] = mapped_column(String(500))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(back_populates="student_profile")
    department: Mapped[Department] = relationship()


class FacultyProfile(Base):
    __tablename__ = "faculty_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), index=True)

    employee_id: Mapped[str] = mapped_column(String(30), unique=True)
    full_name: Mapped[str] = mapped_column(String(120))
    designation: Mapped[Designation] = mapped_column(
        Enum(Designation, name="designation")
    )
    is_placement_coordinator: Mapped[bool] = mapped_column(default=False)
    phone: Mapped[str | None] = mapped_column(String(15))
    joined_on: Mapped[date | None]

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(back_populates="faculty_profile")
    department: Mapped[Department] = relationship()


# Many-to-many: which departments are eligible for a drive.
drive_departments = Table(
    "drive_departments",
    Base.metadata,
    Column("drive_id", ForeignKey("drives.id", ondelete="CASCADE"), primary_key=True),
    Column("department_id", ForeignKey("departments.id", ondelete="CASCADE"), primary_key=True),
)


class Drive(Base):
    __tablename__ = "drives"
    __table_args__ = (
        CheckConstraint("min_cgpa BETWEEN 0 AND 10", name="min_cgpa_range"),
        CheckConstraint("max_backlogs >= 0", name="max_backlogs_nonneg"),
        CheckConstraint("package_lpa IS NULL OR package_lpa >= 0", name="package_nonneg"),
        CheckConstraint(
            "registration_deadline IS NULL OR registration_deadline <= drive_date",
            name="deadline_before_drive",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    company: Mapped[str] = mapped_column(String(120), index=True)
    job_role: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(120))
    package_lpa: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))  # CTC in lakhs per annum

    # Eligibility criteria
    min_cgpa: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=0)
    max_backlogs: Mapped[int] = mapped_column(SmallInteger, default=0)
    passing_year: Mapped[int | None] = mapped_column(SmallInteger)  # batch, e.g. 2027
    required_skills: Mapped[list[str]] = mapped_column(ARRAY(String(50)), default=list)

    drive_date: Mapped[date] = mapped_column(index=True)
    registration_deadline: Mapped[date | None]
    status: Mapped[DriveStatus] = mapped_column(
        Enum(DriveStatus, name="drive_status"), default=DriveStatus.upcoming
    )

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    departments: Mapped[list[Department]] = relationship(secondary=drive_departments)
    creator: Mapped[User | None] = relationship()


class Document(Base):
    """Metadata for a knowledge-base file.

    The file itself is stored on disk as  {DATA_DIR}/uploads/{id}.{file_type}
    and its chunks live in ChromaDB with metadata {"doc_id": str(id)}.
    """

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    original_filename: Mapped[str] = mapped_column(String(255))
    file_type: Mapped[FileType] = mapped_column(Enum(FileType, name="file_type"))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    sha256: Mapped[str] = mapped_column(String(64), unique=True)  # blocks duplicate uploads

    title: Mapped[str | None] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    # NULL = visible to all departments; otherwise scoped to one department
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"), index=True
    )

    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status"),
        default=DocumentStatus.uploaded,
    )
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)

    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    department: Mapped[Department | None] = relationship()
    uploader: Mapped[User | None] = relationship()

    @property
    def stored_filename(self) -> str:
        """Name of the file on disk, e.g. '3f2a...c9.pdf'."""
        return f"{self.id}.{self.file_type.value}"
