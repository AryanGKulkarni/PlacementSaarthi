from fastapi import APIRouter, Body, Depends, status

from app.core.deps import get_auth_service, get_current_user
from app.db.models import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenOut, UserOut
from app.services.auth_service import AuthService, to_user_out

router = APIRouter(prefix="/api/auth", tags=["auth"])

STUDENT_EXAMPLE = {
    "role": "student",
    "email": "aryan@college.edu",
    "password": "Str0ngPass!",
    "full_name": "Aryan Kulkarni",
    "department_id": 1,
}
FACULTY_EXAMPLE = {
    "role": "faculty",
    "email": "prof.sharma@college.edu",
    "password": "Str0ngPass!",
    "full_name": "Priya Sharma",
    "department_id": 1,
    "employee_id": "EMP1042",
    "designation": "assistant_professor",
    "phone": "9876543210",
    "joined_on": "2019-07-15",
}


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(
    data: RegisterRequest = Body(
        openapi_examples={
            "student": {"summary": "Student (basic details only)", "value": STUDENT_EXAMPLE},
            "faculty": {"summary": "Faculty (full profile)", "value": FACULTY_EXAMPLE},
        }
    ),
    auth: AuthService = Depends(get_auth_service),
):
    """Register as a student or faculty member. Returns an access token (auto-login)."""
    return auth.register(data)


@router.post("/login", response_model=TokenOut)
def login(data: LoginRequest, auth: AuthService = Depends(get_auth_service)):
    return auth.login(data.email, data.password)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return to_user_out(user)
