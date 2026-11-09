import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api import auth, chat, dashboard, documents, students
from app.core.config import settings
from app.core.exceptions import AppError
from app.core.security import DEV_SECRET
from app.db.session import SessionLocal, get_db, init_db
from app.repositories.department_repository import DepartmentRepository
from app.repositories.health_repository import HealthRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.department_service import DepartmentService

log = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.jwt_secret == DEV_SECRET:
        log.warning("JWT_SECRET is the insecure development default - set it in .env")
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.resume_dir.mkdir(parents=True, exist_ok=True)
    init_db()  # creates the `placement` schema + tables on startup
    with SessionLocal() as db:
        DepartmentService(DepartmentRepository(db)).seed_defaults()
        AuthService(UserRepository(db), DepartmentRepository(db)).ensure_default_admin(
            settings.admin_email, settings.admin_password
        )
    yield


app = FastAPI(title="Placement Assistant API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code, content={"detail": exc.detail}, headers=exc.headers
    )


app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(dashboard.router)
app.include_router(documents.router)
app.include_router(students.router)


@app.get("/api/health")
def health(db: Session = Depends(get_db)):
    HealthRepository(db).ping()
    return {"status": "ok", "db": "ok", "model": settings.model}
