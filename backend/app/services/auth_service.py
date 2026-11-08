import logging
import uuid

from sqlalchemy.exc import IntegrityError

from app.core import security
from app.core.exceptions import BadRequestError, ConflictError, UnauthorizedError
from app.db.models import FacultyProfile, Role, StudentProfile, User
from app.repositories.department_repository import DepartmentRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import FacultyRegister, StudentRegister, TokenOut, UserOut

INVALID_CREDENTIALS = "Invalid email or password"

log = logging.getLogger("uvicorn.error")


class AuthService:
    def __init__(self, users: UserRepository, departments: DepartmentRepository):
        self.users = users
        self.departments = departments

    # ---- register ---------------------------------------------------------

    def register(self, data: StudentRegister | FacultyRegister) -> TokenOut:
        if self.users.email_exists(data.email):
            raise ConflictError("An account with this email already exists")
        if not self.departments.exists(data.department_id):
            raise BadRequestError(f"Department {data.department_id} does not exist")

        if isinstance(data, FacultyRegister):
            if self.users.employee_id_exists(data.employee_id):
                raise ConflictError("A faculty account with this employee ID already exists")
            user = self._new_user(data, Role.faculty)
            user.faculty_profile = FacultyProfile(
                department_id=data.department_id,
                employee_id=data.employee_id,
                full_name=data.full_name,
                designation=data.designation,
                phone=data.phone,
                joined_on=data.joined_on,
            )
        else:
            user = self._new_user(data, Role.student)
            user.student_profile = StudentProfile(
                department_id=data.department_id,
                full_name=data.full_name,
            )

        try:
            self.users.add(user)
            self.users.commit()
        except IntegrityError as exc:
            self.users.rollback()
            if is_unique_violation(exc):
                # Lost a race with a concurrent registration using the same email / employee ID.
                raise ConflictError("An account with these details already exists") from None
            raise  # NOT NULL / FK / CHECK violations are bugs or schema drift: surface them as 500s

        return self._token_for(user)

    @staticmethod
    def _new_user(data: StudentRegister | FacultyRegister, role: Role) -> User:
        return User(
            id=uuid.uuid4(),
            email=data.email,
            password_hash=security.hash_password(data.password),
            role=role,
            is_active=True,
        )

    # ---- default admin ----------------------------------------------------

    def ensure_default_admin(self, email: str, password: str) -> None:
        """Create the default admin on startup if there is no admin yet.

        Never overwrites an existing user: changing ADMIN_PASSWORD later does not
        reset the password of an admin that already exists.
        """
        if self.users.admin_exists():
            return
        email = email.strip().lower()
        if not email or not password:
            log.warning("No admin exists and ADMIN_EMAIL/ADMIN_PASSWORD are not set; skipping")
            return
        if self.users.email_exists(email):
            log.warning("No admin exists, but %s is already used by a non-admin account; skipping", email)
            return

        self.users.add(
            User(
                id=uuid.uuid4(),
                email=email,
                password_hash=security.hash_password(password),
                role=Role.admin,
                is_active=True,
            )
        )
        try:
            self.users.commit()
        except IntegrityError as exc:
            self.users.rollback()
            if is_unique_violation(exc):  # another process created it at the same moment
                return
            raise
        log.info("Created default admin user %s", email)
        if len(password) < 8:
            log.warning("Default admin password is weak - change ADMIN_PASSWORD before deploying")

    # ---- login ------------------------------------------------------------

    def login(self, email: str, password: str) -> TokenOut:
        user = self.users.get_by_email(email)
        if user is None:
            security.burn_password_check(password)  # same timing as a wrong password
            raise UnauthorizedError(INVALID_CREDENTIALS)
        if not security.verify_password(password, user.password_hash):
            raise UnauthorizedError(INVALID_CREDENTIALS)
        if not user.is_active:
            raise UnauthorizedError("Account is deactivated")
        return self._token_for(user)

    # ---- tokens -----------------------------------------------------------

    def user_from_token(self, token: str) -> User:
        user = self.users.get(security.decode_access_token(token))
        if user is None or not user.is_active:
            raise UnauthorizedError("User not found or deactivated")
        return user

    def _token_for(self, user: User) -> TokenOut:
        token, expires_in = security.create_access_token(user.id, user.role.value)
        return TokenOut(access_token=token, expires_in=expires_in, user=to_user_out(user))


UNIQUE_VIOLATION = "23505"  # Postgres SQLSTATE


def is_unique_violation(exc: IntegrityError) -> bool:
    return getattr(exc.orig, "sqlstate", None) == UNIQUE_VIOLATION


def to_user_out(user: User) -> UserOut:
    profile = user.student_profile or user.faculty_profile
    return UserOut(
        id=user.id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        full_name=profile.full_name if profile else None,
        department_id=profile.department_id if profile else None,
    )
