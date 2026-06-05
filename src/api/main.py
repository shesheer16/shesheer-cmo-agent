"""
src/api/main.py
FastAPI application — mounts the health router.
Used by uvicorn when running in --bot mode.
"""
from fastapi import FastAPI
from src.api.health import router as health_router

app = FastAPI(
    title="Shesheer CMO Agent API",
    description="Internal health and status API for the CMO Agent.",
    version="9.0",
    docs_url=None,   # Disable Swagger UI in production
    redoc_url=None,
)

app.include_router(health_router)
