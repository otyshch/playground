"""
Health check endpoints for monitoring and service discovery.
"""
import logging
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from ...shared.database import get_db
from ...shared.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", summary="Basic health check")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "State Fiscal Data Feed API",
        "version": "1.0.0"
    }


@router.get("/detailed", summary="Detailed health check")
async def detailed_health_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Detailed health check with database connectivity."""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "State Fiscal Data Feed API",
        "version": "1.0.0",
        "checks": {}
    }
    
    # Database connectivity check
    try:
        db.execute(text("SELECT 1"))
        health_status["checks"]["database"] = {
            "status": "healthy",
            "message": "Database connection successful"
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}"
        }
    
    # Configuration check
    try:
        settings = get_settings()
        health_status["checks"]["configuration"] = {
            "status": "healthy",
            "message": "Configuration loaded successfully",
            "database_configured": bool(settings.database_url),
            "external_apis_configured": bool(
                settings.trading_economics_api_key and 
                settings.fred_api_key
            )
        }
    except Exception as e:
        logger.error(f"Configuration health check failed: {e}")
        health_status["status"] = "unhealthy"
        health_status["checks"]["configuration"] = {
            "status": "unhealthy",
            "message": f"Configuration error: {str(e)}"
        }
    
    return health_status


@router.get("/readiness", summary="Readiness probe")
async def readiness_check(db: Session = Depends(get_db)):
    """Kubernetes readiness probe endpoint."""
    try:
        # Check database connectivity
        db.execute(text("SELECT 1"))
        
        return {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {
            "status": "not_ready",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


@router.get("/liveness", summary="Liveness probe")
async def liveness_check():
    """Kubernetes liveness probe endpoint."""
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }