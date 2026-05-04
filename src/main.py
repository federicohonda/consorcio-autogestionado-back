import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.core.config import settings
from src.core.logger import logger
from src.routers import health, auth, users, groups, payments
from src.routers import pozo

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(groups.router)
app.include_router(payments.router)
app.include_router(pozo.router)

# Serve uploaded receipts as static files
uploads_dir = settings.uploads_dir
os.makedirs(os.path.join(uploads_dir, "receipts"), exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")


@app.on_event("startup")
async def on_startup():
    logger.info(f"{settings.app_name} started — environment={settings.environment}")
