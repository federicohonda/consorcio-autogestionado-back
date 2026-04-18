from fastapi import APIRouter
from src.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name, "environment": settings.environment}


@router.get("/health/db")
def health_db():
    # TODO: implement real DB connectivity check once DB layer is set up
    return {"status": "ok", "db": "not_checked"}
