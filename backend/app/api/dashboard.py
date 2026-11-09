from fastapi import APIRouter, Depends

from app.core.deps import get_dashboard_service, require_roles
from app.db.models import Role, User
from app.schemas.dashboard import StudentDashboard
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/student", response_model=StudentDashboard)
def student_dashboard(
    user: User = Depends(require_roles(Role.student)),
    service: DashboardService = Depends(get_dashboard_service),
):
    """Readiness score (4 progress bars), up to 3 tips and the drives the student can apply to."""
    return service.student_dashboard(user)
