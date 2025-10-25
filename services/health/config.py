"""Configuration for health monitoring service."""

from pathlib import Path
from pydantic_settings import BaseSettings


class HealthServiceConfig(BaseSettings):
    """Configuration for health monitoring service."""
    
    # Service
    service_name: str = "health_service"
    service_port: int = 8004
    host: str = "0.0.0.0"
    
    # Collection intervals (seconds)
    collection_interval: int = 5  # Collect metrics every 5 seconds
    
    # Storage
    db_path: Path = Path(__file__).parent.parent.parent / "data" / "health.duckdb"
    
    # Retention policy
    detailed_retention_days: int = 7  # Keep detailed metrics for 7 days
    aggregated_retention_days: int = 30  # Keep hourly aggregates for 30 days
    summary_retention_days: int = 365  # Keep daily summaries for 1 year
    
    # Alert thresholds
    cpu_warning_threshold: float = 80.0  # % CPU usage
    cpu_critical_threshold: float = 95.0
    
    memory_warning_threshold: float = 85.0  # % Memory usage
    memory_critical_threshold: float = 95.0
    
    disk_warning_threshold: float = 80.0  # % Disk usage
    disk_critical_threshold: float = 90.0
    
    # Top processes
    top_processes_count: int = 10
    
    class Config:
        env_prefix = "HEALTH_"
        case_sensitive = False

