from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api import documents
from app.core.config import settings
from app.core.exceptions import AppError
from app.db.session import SessionLocal, get_db, init_db
from app.repositories.department_repository import DepartmentRepository
from app.repositories.health_repository import HealthRepository
from app.services.department_service import DepartmentService


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    init_db()  # creates the `placement` schema + tables on startup
    with SessionLocal() as db:
        DepartmentService(DepartmentRepository(db)).seed_defaults()
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
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


app.include_router(documents.router)


@app.get("/api/health")
def health(db: Session = Depends(get_db)):
    HealthRepository(db).ping()
    return {"status": "ok", "db": "ok", "model": settings.model}
