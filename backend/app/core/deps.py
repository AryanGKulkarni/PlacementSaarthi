"""FastAPI dependency wiring: session -> repositories -> services, plus auth guards."""

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.db.models import Role, User
from app.db.session import get_db
from app.messaging.ingest_queue import IngestQueue
from app.repositories.department_repository import DepartmentRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.document_service import DocumentService

# Shows an "Authorize" button in Swagger (/docs) where you paste the access token.
bearer_scheme = HTTPBearer(auto_error=False)


# ---- services -----------------------------------------------------------------

def get_document_service(db: Session = Depends(get_db)) -> DocumentService:
    return DocumentService(DocumentRepository(db), DepartmentRepository(db), IngestQueue())


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(UserRepository(db), DepartmentRepository(db))


# ---- auth guards --------------------------------------------------------------

def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    auth: AuthService = Depends(get_auth_service),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError("Not authenticated")
    return auth.user_from_token(credentials.credentials)


def require_roles(*roles: Role):
    """Usage: user: User = Depends(require_roles(Role.faculty, Role.admin))"""

    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise ForbiddenError("You don't have permission to do this")
        return user

    return checker
