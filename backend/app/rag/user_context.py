"""Describe the person asking, so the LLM can frame and personalise its answer.

Only details useful for placement advice are included. Contact/identity data
(email, phone, roll number, resume path) is deliberately left out of the prompt.
"""

from dataclasses import dataclass

from app.db.models import FacultyProfile, Role, StudentProfile, User

NOT_PROVIDED = "not provided"


@dataclass
class AskerContext:
    role: Role | None
    persona: str              # instruction: how to address / frame the answer
    profile_text: str | None  # data: the asker's profile, or None


def build_asker_context(user: User | None) -> AskerContext:
    if user is None:
        return AskerContext(
            role=None,
            persona="The person asking is not identified. Give general, factual guidance.",
            profile_text=None,
        )

    if user.role is Role.admin:
        return AskerContext(
            role=Role.admin,
            persona=(
                "The person asking is a placement administrator. Give complete, factual answers; "
                "do not address them as a job candidate."
            ),
            profile_text="Role: Placement administrator (all departments)",
        )

    if user.role is Role.faculty:
        profile = user.faculty_profile
        return AskerContext(
            role=Role.faculty,
            persona=(
                "The person asking is a faculty member who mentors students for placements. "
                "Frame answers as guidance they can pass on to their students, state eligibility "
                "criteria explicitly, and do not address them as a job candidate."
            ),
            profile_text=_faculty_text(profile) if profile else "Role: Faculty",
        )

    profile = user.student_profile
    return AskerContext(
        role=Role.student,
        persona=(
            "The person asking is a student preparing for placements. Address them as 'you'. "
            "Where it helps, personalise the advice using their profile: compare their CGPA, "
            "backlogs and branch with the eligibility criteria in the context, and point out "
            "required skills missing from their skill list. If a profile detail needed to answer "
            "is 'not provided', say so and suggest completing their profile."
        ),
        profile_text=_student_text(profile) if profile else "Role: Student (profile not filled in yet)",
    )


def _student_text(p: StudentProfile) -> str:
    lines = [
        "Role: Student",
        f"Name: {p.full_name}",
        f"Branch/Department: {_department(p)}",
        f"Year of study: {_val(p.year)}",
        f"Passing year (batch): {_val(p.passing_year)}",
        f"CGPA (out of 10): {_val(p.cgpa)}",
        f"Active backlogs: {_val(p.active_backlogs)}",
        f"10th percentage: {_val(p.tenth_percent)}",
        f"12th percentage: {_val(p.twelfth_percent)}",
        f"Skills: {', '.join(p.skills) if p.skills else NOT_PROVIDED}",
        f"Career interests: {', '.join(p.interests) if p.interests else NOT_PROVIDED}",
        f"Internships: {_val(p.internships)}",
        f"Projects: {_val(p.projects)}",
        f"Certifications: {_val(p.certifications)}",
    ]
    return "\n".join(lines)


def _faculty_text(p: FacultyProfile) -> str:
    lines = [
        "Role: Faculty",
        f"Name: {p.full_name}",
        f"Department: {_department(p)}",
        f"Designation: {p.designation.value.replace('_', ' ').title()}",
        f"Placement coordinator: {'yes' if p.is_placement_coordinator else 'no'}",
    ]
    return "\n".join(lines)


def _department(p: StudentProfile | FacultyProfile) -> str:
    d = p.department
    return f"{d.code} ({d.name})" if d else NOT_PROVIDED


def _val(value) -> str:
    return NOT_PROVIDED if value is None else str(value)
