"""
Zero AI — Subsystem Health Monitoring & System Telemetry.

Responsibilities:
- Subsystem health checks (database, audio, AI provider, knowledge store).
- Memory, CPU, and disk metrics collection.
"""

from app.system.health_monitor import HealthMonitor

__all__ = ["HealthMonitor"]
