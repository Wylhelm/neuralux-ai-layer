"""Data models for health monitoring service."""

from datetime import datetime
from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class CPUMetrics(BaseModel):
    """CPU metrics."""
    usage_percent: float
    per_core: List[float]
    load_average: List[float]  # 1, 5, 15 minute averages
    context_switches: int
    interrupts: int


class MemoryMetrics(BaseModel):
    """Memory metrics."""
    total: int  # bytes
    available: int
    used: int
    percent: float
    swap_total: int
    swap_used: int
    swap_percent: float


class DiskMetrics(BaseModel):
    """Disk metrics for a single partition."""
    device: str
    mountpoint: str
    total: int  # bytes
    used: int
    free: int
    percent: float


class NetworkMetrics(BaseModel):
    """Network metrics."""
    bytes_sent: int
    bytes_recv: int
    packets_sent: int
    packets_recv: int
    connections: int


class ProcessInfo(BaseModel):
    """Information about a single process."""
    pid: int
    name: str
    cpu_percent: float
    memory_percent: float
    memory_mb: float


class SystemMetrics(BaseModel):
    """Complete system metrics snapshot."""
    timestamp: datetime
    cpu: CPUMetrics
    memory: MemoryMetrics
    disks: List[DiskMetrics]
    network: NetworkMetrics
    top_processes: List[ProcessInfo]
    uptime_seconds: float
    boot_time: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class HealthAlert(BaseModel):
    """Health alert/warning."""
    timestamp: datetime
    level: str  # "warning" or "critical"
    category: str  # "cpu", "memory", "disk", "process"
    message: str
    value: float
    threshold: float
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class HealthSummary(BaseModel):
    """Summary of system health."""
    current_metrics: SystemMetrics
    alerts: List[HealthAlert]
    status: str  # "healthy", "warning", "critical"


class HealthHistoryRequest(BaseModel):
    """Request for historical health data."""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    metric_type: Optional[str] = None  # "cpu", "memory", "disk", "network"
    limit: int = 100


class HealthHistoryResponse(BaseModel):
    """Response with historical health data."""
    metrics: List[SystemMetrics]
    count: int

