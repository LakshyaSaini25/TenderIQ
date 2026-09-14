from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
from app.core.database import db_instance, get_database
from app.core.config import settings
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("", response_model=Dict[str, str])
async def health_check():
    """
    Basic health check endpoint to verify the API is running.
    """
    return {"status": "ok"}

@router.get("/db", response_model=Dict[str, str])
async def database_health_check():
    """
    Database health check endpoint to verify MongoDB connectivity.
    """
    if db_instance.client is None:
        raise HTTPException(status_code=503, detail="Database client not initialized")
    
    try:
        # Ping the database
        await db_instance.client.admin.command('ping')
        return {
            "status": "ok",
            "database": settings.DATABASE_NAME
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        raise HTTPException(status_code=503, detail="Database connection failed")

