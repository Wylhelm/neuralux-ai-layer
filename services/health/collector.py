"""Metrics collection using psutil."""

import os
import psutil
from datetime import datetime
from typing import List
import structlog

from models import (
    SystemMetrics,
    CPUMetrics,
    MemoryMetrics,
    DiskMetrics,
    NetworkMetrics,
    ProcessInfo,
    GPUMetrics,
)

logger = structlog.get_logger(__name__)


class MetricsCollector:
    """Collects system metrics using psutil."""
    
    def __init__(self):
        """Initialize the metrics collector."""
        # Store previous network counters for delta calculation
        self._last_net_io = psutil.net_io_counters()
        
    def collect_cpu_metrics(self) -> CPUMetrics:
        """Collect CPU metrics."""
        try:
            # Collect per-core first (includes overall) - more efficient than two separate calls
            per_core = psutil.cpu_percent(interval=0.1, percpu=True)
            # Calculate overall from per-core average instead of separate blocking call
            cpu_percent = sum(per_core) / len(per_core) if per_core else 0.0
            load_avg = os.getloadavg() if hasattr(os, 'getloadavg') else [0.0, 0.0, 0.0]
            
            cpu_stats = psutil.cpu_stats()
            
            return CPUMetrics(
                usage_percent=cpu_percent,
                per_core=per_core,
                load_average=list(load_avg),
                context_switches=cpu_stats.ctx_switches,
                interrupts=cpu_stats.interrupts,
            )
        except Exception as e:
            logger.error("Error collecting CPU metrics", error=str(e))
            return CPUMetrics(
                usage_percent=0.0,
                per_core=[],
                load_average=[0.0, 0.0, 0.0],
                context_switches=0,
                interrupts=0,
            )
    
    def collect_memory_metrics(self) -> MemoryMetrics:
        """Collect memory metrics."""
        try:
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            return MemoryMetrics(
                total=mem.total,
                available=mem.available,
                used=mem.used,
                percent=mem.percent,
                swap_total=swap.total,
                swap_used=swap.used,
                swap_percent=swap.percent,
            )
        except Exception as e:
            logger.error("Error collecting memory metrics", error=str(e))
            return MemoryMetrics(
                total=0,
                available=0,
                used=0,
                percent=0.0,
                swap_total=0,
                swap_used=0,
                swap_percent=0.0,
            )
    
    def collect_disk_metrics(self) -> List[DiskMetrics]:
        """Collect disk metrics for all partitions."""
        disks = []
        try:
            partitions = psutil.disk_partitions(all=False)
            
            for partition in partitions:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    
                    disks.append(DiskMetrics(
                        device=partition.device,
                        mountpoint=partition.mountpoint,
                        total=usage.total,
                        used=usage.used,
                        free=usage.free,
                        percent=usage.percent,
                    ))
                except (PermissionError, OSError) as e:
                    logger.debug("Cannot access partition", partition=partition.mountpoint, error=str(e))
                    continue
                    
        except Exception as e:
            logger.error("Error collecting disk metrics", error=str(e))
            
        return disks
    
    def collect_network_metrics(self) -> NetworkMetrics:
        """Collect network metrics."""
        try:
            net_io = psutil.net_io_counters()
            connections = len(psutil.net_connections())
            
            return NetworkMetrics(
                bytes_sent=net_io.bytes_sent,
                bytes_recv=net_io.bytes_recv,
                packets_sent=net_io.packets_sent,
                packets_recv=net_io.packets_recv,
                connections=connections,
            )
        except Exception as e:
            logger.error("Error collecting network metrics", error=str(e))
            return NetworkMetrics(
                bytes_sent=0,
                bytes_recv=0,
                packets_sent=0,
                packets_recv=0,
                connections=0,
            )
    
    def collect_top_processes(self, count: int = 10) -> List[ProcessInfo]:
        """Collect information about top processes by CPU usage."""
        processes = []
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'memory_info']):
                try:
                    info = proc.info
                    memory_mb = info['memory_info'].rss / (1024 * 1024) if info.get('memory_info') else 0.0
                    
                    processes.append(ProcessInfo(
                        pid=info['pid'],
                        name=info['name'],
                        cpu_percent=info['cpu_percent'] or 0.0,
                        memory_percent=info['memory_percent'] or 0.0,
                        memory_mb=memory_mb,
                    ))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Sort by CPU usage and take top N
            processes.sort(key=lambda p: p.cpu_percent, reverse=True)
            return processes[:count]
            
        except Exception as e:
            logger.error("Error collecting process info", error=str(e))
            return []
    
    def collect_all(self, top_process_count: int = 10) -> SystemMetrics:
        """Collect all system metrics."""
        try:
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = (datetime.now() - boot_time).total_seconds()
            # Try to collect GPU metrics via pynvml (NVIDIA)
            gpus = []
            try:
                import pynvml  # type: ignore
                pynvml.nvmlInit()
                count = pynvml.nvmlDeviceGetCount()
                for i in range(count):
                    h = pynvml.nvmlDeviceGetHandleByIndex(i)
                    name = pynvml.nvmlDeviceGetName(h).decode("utf-8") if hasattr(pynvml.nvmlDeviceGetName(h), 'decode') else str(pynvml.nvmlDeviceGetName(h))
                    util = pynvml.nvmlDeviceGetUtilizationRates(h)
                    mem = pynvml.nvmlDeviceGetMemoryInfo(h)
                    temp = None
                    power = None
                    limit = None
                    try:
                        temp = float(pynvml.nvmlDeviceGetTemperature(h, pynvml.NVML_TEMPERATURE_GPU))
                    except Exception:
                        pass
                    try:
                        power = float(pynvml.nvmlDeviceGetPowerUsage(h)) / 1000.0
                        limit = float(pynvml.nvmlDeviceGetEnforcedPowerLimit(h)) / 1000.0
                    except Exception:
                        pass
                    mem_used_mb = mem.used / (1024 * 1024)
                    mem_total_mb = mem.total / (1024 * 1024)
                    mem_util = (mem_used_mb / mem_total_mb * 100.0) if mem_total_mb > 0 else 0.0
                    gpus.append(GPUMetrics(
                        index=i,
                        name=name,
                        utilization_percent=float(util.gpu),
                        memory_used_mb=mem_used_mb,
                        memory_total_mb=mem_total_mb,
                        memory_util_percent=mem_util,
                        temperature_c=temp,
                        power_watts=power,
                        power_limit_watts=limit,
                    ))
                try:
                    pynvml.nvmlShutdown()
                except Exception:
                    pass
            except Exception:
                gpus = []
            
            return SystemMetrics(
                timestamp=datetime.now(),
                cpu=self.collect_cpu_metrics(),
                memory=self.collect_memory_metrics(),
                disks=self.collect_disk_metrics(),
                network=self.collect_network_metrics(),
                top_processes=self.collect_top_processes(top_process_count),
                gpus=gpus,
                uptime_seconds=uptime,
                boot_time=boot_time,
            )
        except Exception as e:
            logger.error("Error collecting system metrics", error=str(e))
            raise

