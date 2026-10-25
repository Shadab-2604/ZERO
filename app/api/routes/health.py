"""
Health route returning real subsystem status.
"""

from fastapi import APIRouter
from app.system.health_monitor import HealthMonitor

router = APIRouter(tags=["Health"])


@router.get("/health")
def get_health():
    """Retrieve comprehensive subsystem health status."""
    return HealthMonitor.get_full_health_report()
