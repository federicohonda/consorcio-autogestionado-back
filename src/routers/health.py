from fastapi import APIRouter
from src.core.config import settings
from src.database.db import check_connection

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name, "environment": settings.environment}


@router.get("/health/db")
def health_db():
    connected = check_connection()
    if not connected:
        return {"status": "error", "db": "unreachable"}
    return {"status": "ok", "db": "connected"}
