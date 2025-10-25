"""Health monitoring service main entry point."""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
import structlog
from fastapi import FastAPI, HTTPException

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "packages" / "common"))

from neuralux.config import NeuraluxConfig
from neuralux.logger import setup_logging
from neuralux.messaging import MessageBusClient

from config import HealthServiceConfig
from collector import MetricsCollector
from storage import HealthStorage
from detector import AnomalyDetector
from models import (
    HealthSummary,
    HealthHistoryRequest,
    HealthHistoryResponse,
)

logger = structlog.get_logger(__name__)


class HealthService:
    """Health monitoring service."""
    
    def __init__(self):
        """Initialize the health service."""
        self.config = HealthServiceConfig()
        self.neuralux_config = NeuraluxConfig()
        self.message_bus = MessageBusClient(self.neuralux_config)
        
        self.collector = MetricsCollector()
        self.storage = HealthStorage(self.config)
        self.detector = AnomalyDetector(self.config)
        
        self.app = FastAPI(
            title="Neuralux Health Service",
            version="0.1.0",
            description="System health monitoring and alerting"
        )
        self._setup_routes()
        
        self.collection_task = None
        self.cleanup_task = None
        
    async def connect_to_message_bus(self):
        """Connect to NATS and register handlers."""
        await self.message_bus.connect()
        
        # Register reply handlers (for request-response pattern)
        await self.message_bus.reply_handler(
            "system.health.current", self._handle_current_request
        )
        await self.message_bus.reply_handler(
            "system.health.history", self._handle_history_request
        )
        await self.message_bus.reply_handler(
            "system.health.alerts", self._handle_alerts_request
        )
        await self.message_bus.reply_handler(
            "system.health.summary", self._handle_summary_request
        )
        
        logger.info("Health service connected to NATS and handlers registered")
    
    async def disconnect_from_message_bus(self):
        """Disconnect from NATS."""
        await self.message_bus.disconnect()
        logger.info("Health service disconnected from NATS")
    
    def _setup_routes(self):
        """Setup FastAPI routes."""
        
        @self.app.get("/")
        async def read_root():
            return {"service": self.config.service_name, "version": "0.1.0", "status": "running"}
        
        @self.app.get("/health")
        async def get_health():
            """Get current health summary."""
            return await self._get_health_summary()
        
        @self.app.post("/history")
        async def get_history(request: HealthHistoryRequest):
            """Get historical metrics."""
            metrics = self.storage.get_metrics_history(
                start_time=request.start_time,
                end_time=request.end_time,
                limit=request.limit
            )
            return HealthHistoryResponse(
                metrics=metrics,
                count=len(metrics)
            )
    
    async def _handle_current_request(self, data: dict) -> dict:
        """Handle request for current metrics."""
        try:
            metrics = self.collector.collect_all(self.config.top_processes_count)
            return metrics.model_dump(mode='json')
        except Exception as e:
            logger.error("Error handling current request", error=str(e))
            return {"error": str(e)}
    
    async def _handle_history_request(self, data: dict) -> dict:
        """Handle request for historical metrics."""
        try:
            request = HealthHistoryRequest(**data)
            metrics = self.storage.get_metrics_history(
                start_time=request.start_time,
                end_time=request.end_time,
                limit=request.limit
            )
            response = HealthHistoryResponse(
                metrics=metrics,
                count=len(metrics)
            )
            return response.model_dump(mode='json')
        except Exception as e:
            logger.error("Error handling history request", error=str(e))
            return {"error": str(e)}
    
    async def _handle_alerts_request(self, data: dict) -> dict:
        """Handle request for recent alerts."""
        try:
            hours = data.get("hours", 24)
            alerts = self.storage.get_recent_alerts(hours)
            return {
                "alerts": [alert.model_dump(mode='json') for alert in alerts],
                "count": len(alerts)
            }
        except Exception as e:
            logger.error("Error handling alerts request", error=str(e))
            return {"error": str(e)}
    
    async def _handle_summary_request(self, data: dict) -> dict:
        """Handle request for health summary."""
        try:
            logger.info("Handling summary request")
            summary = await self._get_health_summary()
            result = summary.model_dump(mode='json')
            logger.info("Summary request successful", result_keys=list(result.keys()))
            return result
        except Exception as e:
            logger.error("Error handling summary request", error=str(e), exc_info=True)
            return {"error": str(e)}
    
    async def _get_health_summary(self) -> HealthSummary:
        """Get current health summary."""
        # Collect current metrics
        metrics = self.collector.collect_all(self.config.top_processes_count)
        
        # Detect anomalies
        alerts = self.detector.detect_anomalies(metrics)
        
        # Determine overall status
        status = self.detector.get_overall_status(alerts)
        
        return HealthSummary(
            current_metrics=metrics,
            alerts=alerts,
            status=status
        )
    
    async def start_collection(self):
        """Start periodic metrics collection."""
        logger.info("Starting metrics collection", interval=self.config.collection_interval)
        
        while True:
            try:
                # Collect metrics
                metrics = self.collector.collect_all(self.config.top_processes_count)
                
                # Store metrics
                self.storage.store_metrics(metrics)
                
                # Detect anomalies
                alerts = self.detector.detect_anomalies(metrics)
                
                # Store alerts
                for alert in alerts:
                    self.storage.store_alert(alert)
                    logger.warning(
                        "Health alert",
                        level=alert.level,
                        category=alert.category,
                        message=alert.message
                    )
                
            except Exception as e:
                logger.error("Error in collection loop", error=str(e))
            
            await asyncio.sleep(self.config.collection_interval)
    
    async def start_cleanup(self):
        """Start periodic cleanup of old data."""
        logger.info("Starting cleanup task")
        
        while True:
            try:
                # Run cleanup once per day
                await asyncio.sleep(86400)  # 24 hours
                self.storage.cleanup_old_data()
            except Exception as e:
                logger.error("Error in cleanup loop", error=str(e))
    
    async def start(self):
        """Start the health service."""
        try:
            await self.connect_to_message_bus()
            
            # Start background tasks
            self.collection_task = asyncio.create_task(self.start_collection())
            self.cleanup_task = asyncio.create_task(self.start_cleanup())
            
            logger.info("Health service started")
        except Exception as e:
            logger.error("Failed to start health service", error=str(e))
    
    async def stop(self):
        """Stop the health service."""
        logger.info("Stopping health service")
        if self.collection_task:
            self.collection_task.cancel()
        if self.cleanup_task:
            self.cleanup_task.cancel()
        await self.disconnect_from_message_bus()


# Create service instance
service = HealthService()


if __name__ == "__main__":
    import uvicorn
    
    setup_logging("health_service")
    
    async def startup():
        await service.start()
    
    async def shutdown():
        await service.stop()
    
    # Add startup/shutdown handlers
    service.app.add_event_handler("startup", startup)
    service.app.add_event_handler("shutdown", shutdown)
    
    # Run the service
    uvicorn.run(
        service.app,
        host=service.config.host,
        port=service.config.service_port,
        log_level="info",
    )

