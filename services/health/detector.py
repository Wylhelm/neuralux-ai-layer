"""Anomaly detection and alerting."""

from datetime import datetime
from typing import List
import structlog

from models import SystemMetrics, HealthAlert
from config import HealthServiceConfig

logger = structlog.get_logger(__name__)


class AnomalyDetector:
    """Detects anomalies in system metrics and generates alerts."""
    
    def __init__(self, config: HealthServiceConfig):
        """Initialize the anomaly detector."""
        self.config = config
    
    def detect_anomalies(self, metrics: SystemMetrics) -> List[HealthAlert]:
        """Detect anomalies in metrics and return alerts."""
        alerts = []
        
        # Check CPU usage
        alerts.extend(self._check_cpu(metrics))
        
        # Check memory usage
        alerts.extend(self._check_memory(metrics))
        
        # Check disk usage
        alerts.extend(self._check_disks(metrics))
        
        return alerts
    
    def _check_cpu(self, metrics: SystemMetrics) -> List[HealthAlert]:
        """Check CPU metrics for anomalies."""
        alerts = []
        cpu_usage = metrics.cpu.usage_percent
        
        if cpu_usage >= self.config.cpu_critical_threshold:
            alerts.append(HealthAlert(
                timestamp=datetime.now(),
                level="critical",
                category="cpu",
                message=f"CPU usage is critically high: {cpu_usage:.1f}%",
                value=cpu_usage,
                threshold=self.config.cpu_critical_threshold,
            ))
        elif cpu_usage >= self.config.cpu_warning_threshold:
            alerts.append(HealthAlert(
                timestamp=datetime.now(),
                level="warning",
                category="cpu",
                message=f"CPU usage is high: {cpu_usage:.1f}%",
                value=cpu_usage,
                threshold=self.config.cpu_warning_threshold,
            ))
        
        return alerts
    
    def _check_memory(self, metrics: SystemMetrics) -> List[HealthAlert]:
        """Check memory metrics for anomalies."""
        alerts = []
        mem_usage = metrics.memory.percent
        
        if mem_usage >= self.config.memory_critical_threshold:
            alerts.append(HealthAlert(
                timestamp=datetime.now(),
                level="critical",
                category="memory",
                message=f"Memory usage is critically high: {mem_usage:.1f}%",
                value=mem_usage,
                threshold=self.config.memory_critical_threshold,
            ))
        elif mem_usage >= self.config.memory_warning_threshold:
            alerts.append(HealthAlert(
                timestamp=datetime.now(),
                level="warning",
                category="memory",
                message=f"Memory usage is high: {mem_usage:.1f}%",
                value=mem_usage,
                threshold=self.config.memory_warning_threshold,
            ))
        
        # Check swap usage
        swap_usage = metrics.memory.swap_percent
        if swap_usage > 50.0:
            alerts.append(HealthAlert(
                timestamp=datetime.now(),
                level="warning",
                category="memory",
                message=f"Swap usage is high: {swap_usage:.1f}%",
                value=swap_usage,
                threshold=50.0,
            ))
        
        return alerts
    
    def _check_disks(self, metrics: SystemMetrics) -> List[HealthAlert]:
        """Check disk metrics for anomalies."""
        alerts = []
        
        for disk in metrics.disks:
            # Skip snap mounts and loop devices (they're always 100% and read-only)
            if disk.mountpoint.startswith('/snap/') or '/loop' in disk.device:
                continue
            
            # Skip other special mounts
            if disk.mountpoint.startswith('/run/') or disk.mountpoint.startswith('/sys/'):
                continue
            
            disk_usage = disk.percent
            
            if disk_usage >= self.config.disk_critical_threshold:
                alerts.append(HealthAlert(
                    timestamp=datetime.now(),
                    level="critical",
                    category="disk",
                    message=f"Disk {disk.mountpoint} is critically full: {disk_usage:.1f}%",
                    value=disk_usage,
                    threshold=self.config.disk_critical_threshold,
                ))
            elif disk_usage >= self.config.disk_warning_threshold:
                alerts.append(HealthAlert(
                    timestamp=datetime.now(),
                    level="warning",
                    category="disk",
                    message=f"Disk {disk.mountpoint} is filling up: {disk_usage:.1f}%",
                    value=disk_usage,
                    threshold=self.config.disk_warning_threshold,
                ))
        
        return alerts
    
    def get_overall_status(self, alerts: List[HealthAlert]) -> str:
        """Determine overall system health status."""
        if not alerts:
            return "healthy"
        
        for alert in alerts:
            if alert.level == "critical":
                return "critical"
        
        return "warning"

