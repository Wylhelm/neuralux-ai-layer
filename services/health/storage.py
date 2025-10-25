"""Time-series storage for health metrics using DuckDB."""

import duckdb
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional
import structlog
import json

from models import SystemMetrics, HealthAlert
from config import HealthServiceConfig

logger = structlog.get_logger(__name__)


class HealthStorage:
    """Manages time-series storage of health metrics in DuckDB."""
    
    def __init__(self, config: HealthServiceConfig):
        """Initialize the storage."""
        self.config = config
        self.db_path = config.db_path
        
        # Ensure directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
        
    def _init_database(self):
        """Initialize database schema."""
        try:
            conn = duckdb.connect(str(self.db_path))
            
            # Create metrics table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    timestamp TIMESTAMP,
                    cpu_usage FLOAT,
                    cpu_per_core VARCHAR,
                    load_average VARCHAR,
                    memory_total BIGINT,
                    memory_used BIGINT,
                    memory_percent FLOAT,
                    swap_used BIGINT,
                    swap_percent FLOAT,
                    disks VARCHAR,
                    network_bytes_sent BIGINT,
                    network_bytes_recv BIGINT,
                    network_connections INTEGER,
                    top_processes VARCHAR,
                    uptime_seconds FLOAT,
                    boot_time TIMESTAMP
                )
            """)
            
            # Create index on timestamp for faster queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_metrics_timestamp 
                ON metrics(timestamp)
            """)
            
            # Create alerts table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    timestamp TIMESTAMP,
                    level VARCHAR,
                    category VARCHAR,
                    message VARCHAR,
                    value FLOAT,
                    threshold FLOAT
                )
            """)
            
            # Create index on alerts timestamp
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_alerts_timestamp 
                ON alerts(timestamp)
            """)
            
            conn.close()
            logger.info("Database initialized", path=str(self.db_path))
            
        except Exception as e:
            logger.error("Error initializing database", error=str(e))
            raise
    
    def store_metrics(self, metrics: SystemMetrics):
        """Store a metrics snapshot."""
        try:
            conn = duckdb.connect(str(self.db_path))
            
            conn.execute("""
                INSERT INTO metrics VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
            """, (
                metrics.timestamp,
                metrics.cpu.usage_percent,
                json.dumps(metrics.cpu.per_core),
                json.dumps(metrics.cpu.load_average),
                metrics.memory.total,
                metrics.memory.used,
                metrics.memory.percent,
                metrics.memory.swap_used,
                metrics.memory.swap_percent,
                json.dumps([d.model_dump(mode='json') for d in metrics.disks]),
                metrics.network.bytes_sent,
                metrics.network.bytes_recv,
                metrics.network.connections,
                json.dumps([p.model_dump() for p in metrics.top_processes]),
                metrics.uptime_seconds,
                metrics.boot_time,
            ))
            
            conn.close()
            logger.debug("Metrics stored", timestamp=metrics.timestamp)
            
        except Exception as e:
            logger.error("Error storing metrics", error=str(e))
    
    def store_alert(self, alert: HealthAlert):
        """Store a health alert."""
        try:
            conn = duckdb.connect(str(self.db_path))
            
            conn.execute("""
                INSERT INTO alerts VALUES (?, ?, ?, ?, ?, ?)
            """, (
                alert.timestamp,
                alert.level,
                alert.category,
                alert.message,
                alert.value,
                alert.threshold,
            ))
            
            conn.close()
            logger.info("Alert stored", level=alert.level, category=alert.category)
            
        except Exception as e:
            logger.error("Error storing alert", error=str(e))
    
    def get_latest_metrics(self) -> Optional[SystemMetrics]:
        """Get the most recent metrics."""
        try:
            conn = duckdb.connect(str(self.db_path))
            
            result = conn.execute("""
                SELECT * FROM metrics 
                ORDER BY timestamp DESC 
                LIMIT 1
            """).fetchone()
            
            conn.close()
            
            if not result:
                return None
            
            return self._row_to_metrics(result)
            
        except Exception as e:
            logger.error("Error getting latest metrics", error=str(e))
            return None
    
    def get_metrics_history(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[SystemMetrics]:
        """Get historical metrics."""
        try:
            conn = duckdb.connect(str(self.db_path))
            
            query = "SELECT * FROM metrics WHERE 1=1"
            params = []
            
            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time)
            
            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            results = conn.execute(query, params).fetchall()
            conn.close()
            
            return [self._row_to_metrics(row) for row in results]
            
        except Exception as e:
            logger.error("Error getting metrics history", error=str(e))
            return []
    
    def get_recent_alerts(self, hours: int = 24) -> List[HealthAlert]:
        """Get recent alerts."""
        try:
            conn = duckdb.connect(str(self.db_path))
            
            since = datetime.now() - timedelta(hours=hours)
            
            results = conn.execute("""
                SELECT * FROM alerts 
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
            """, (since,)).fetchall()
            
            conn.close()
            
            alerts = []
            for row in results:
                alerts.append(HealthAlert(
                    timestamp=row[0],
                    level=row[1],
                    category=row[2],
                    message=row[3],
                    value=row[4],
                    threshold=row[5],
                ))
            
            return alerts
            
        except Exception as e:
            logger.error("Error getting recent alerts", error=str(e))
            return []
    
    def cleanup_old_data(self):
        """Clean up old data based on retention policy."""
        try:
            conn = duckdb.connect(str(self.db_path))
            
            # Delete detailed metrics older than retention period
            cutoff = datetime.now() - timedelta(days=self.config.detailed_retention_days)
            conn.execute("DELETE FROM metrics WHERE timestamp < ?", (cutoff,))
            
            # Delete old alerts
            alert_cutoff = datetime.now() - timedelta(days=self.config.aggregated_retention_days)
            conn.execute("DELETE FROM alerts WHERE timestamp < ?", (alert_cutoff,))
            
            conn.close()
            logger.info("Old data cleaned up", cutoff=cutoff)
            
        except Exception as e:
            logger.error("Error cleaning up old data", error=str(e))
    
    def _row_to_metrics(self, row) -> SystemMetrics:
        """Convert a database row to SystemMetrics."""
        from models import CPUMetrics, MemoryMetrics, DiskMetrics, NetworkMetrics, ProcessInfo
        
        return SystemMetrics(
            timestamp=row[0],
            cpu=CPUMetrics(
                usage_percent=row[1],
                per_core=json.loads(row[2]),
                load_average=json.loads(row[3]),
                context_switches=0,  # Not stored
                interrupts=0,  # Not stored
            ),
            memory=MemoryMetrics(
                total=row[4],
                used=row[5],
                available=row[4] - row[5],
                percent=row[6],
                swap_total=0,  # Not stored separately
                swap_used=row[7],
                swap_percent=row[8],
            ),
            disks=[DiskMetrics(**d) for d in json.loads(row[9])],
            network=NetworkMetrics(
                bytes_sent=row[10],
                bytes_recv=row[11],
                packets_sent=0,  # Not stored
                packets_recv=0,  # Not stored
                connections=row[12],
            ),
            top_processes=[ProcessInfo(**p) for p in json.loads(row[13])],
            uptime_seconds=row[14],
            boot_time=row[15],
        )

