"""
src/api/health.py
FastAPI health endpoint — returns system status for Railway/Render health checks.
"""
import time
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()
START_TIME = time.time()
VERSION = "9.0"


@router.get("/health")
async def health_check():
    status = {}

    # ChromaDB check
    try:
        from src.knowledge.chroma_client import get_collection
        col = get_collection("founders_mindsets")
        chunk_count = col.count()
        # Count all collections
        for col_name in ["campaign_case_studies", "cmo_profiles", "market_data_reports",
                          "consumer_psychology", "books_annotations", "social_intelligence"]:
            try:
                chunk_count += get_collection(col_name).count()
            except Exception:
                pass
        status["chromadb_status"] = "ok"
        status["knowledge_chunks_count"] = chunk_count
    except Exception as e:
        status["chromadb_status"] = f"error: {str(e)[:80]}"
        status["knowledge_chunks_count"] = 0

    # SQLite check
    try:
        from src.memory.database import SessionLocal
        from sqlalchemy import text
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        status["sqlite_status"] = "ok"
    except Exception as e:
        status["sqlite_status"] = f"error: {str(e)[:80]}"


    # Overall
    is_healthy = (
        status["chromadb_status"] == "ok" and
        status["sqlite_status"] == "ok"
    )

    return JSONResponse(
        status_code=200 if is_healthy else 503,
        content={
            "status": "ok" if is_healthy else "degraded",
            "chromadb_status": status["chromadb_status"],
            "sqlite_status": status["sqlite_status"],
            "knowledge_chunks_count": status["knowledge_chunks_count"],
            "uptime_seconds": int(time.time() - START_TIME),
            "version": VERSION,
        }
    )


@router.get("/")
async def root():
    return {"message": "Shesheer CMO Agent — API running. Hit /health for status."}
