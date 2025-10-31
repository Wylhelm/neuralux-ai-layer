import duckdb
import os
from pathlib import Path
import logging
from services.temporal import config
from services.temporal.models import BaseEvent, CommandEvent, FileEvent, AppFocusEvent, SystemSnapshotEvent

logger = logging.getLogger(config.SERVICE_NAME)

class TimelineStorage:
    """Manages the DuckDB database for storing temporal events."""

    def __init__(self):
        storage_path = Path(config.STORAGE_PATH)
        storage_path.mkdir(parents=True, exist_ok=True)
        self.db_path = storage_path / config.DB_FILENAME
        logger.info(f"Initializing timeline database at: {self.db_path}")
        self.conn = duckdb.connect(database=str(self.db_path), read_only=False)
        self._create_tables()

    def _create_tables(self):
        """Creates the necessary tables if they don't exist."""
        with self.conn.cursor() as cur:
            # Command Events Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS command_events (
                    event_id VARCHAR PRIMARY KEY,
                    timestamp TIMESTAMP,
                    event_type VARCHAR,
                    command VARCHAR,
                    cwd VARCHAR,
                    exit_code INTEGER,
                    user VARCHAR
                );
            """)
            # File Events Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS file_events (
                    event_id VARCHAR PRIMARY KEY,
                    timestamp TIMESTAMP,
                    event_type VARCHAR,
                    path VARCHAR,
                    change_type VARCHAR,
                    is_directory BOOLEAN,
                    user VARCHAR
                );
            """)
            # App Focus Events Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS app_focus_events (
                    event_id VARCHAR PRIMARY KEY,
                    timestamp TIMESTAMP,
                    event_type VARCHAR,
                    app_name VARCHAR,
                    window_title VARCHAR,
                    user VARCHAR
                );
            """)
            # System Snapshot Events Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS system_snapshot_events (
                    event_id VARCHAR PRIMARY KEY,
                    timestamp TIMESTAMP,
                    event_type VARCHAR,
                    active_app_name VARCHAR,
                    active_window_title VARCHAR,
                    running_processes VARCHAR[],
                    cpu_usage FLOAT,
                    memory_usage FLOAT
                );
            """)
        logger.info("Database tables created or verified successfully.")

    def add_event(self, event: BaseEvent):
        """Adds a new event to the appropriate table."""
        table_name = f"{event.event_type}_events"
        
        # We need to handle the model dict carefully
        event_dict = event.model_dump()
        
        columns = ", ".join(event_dict.keys())
        placeholders = ", ".join(["?" for _ in event_dict])
        
        sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        
        try:
            with self.conn.cursor() as cur:
                cur.execute(sql, list(event_dict.values()))
            logger.debug(f"Added {event.event_type} event: {event.event_id}")
        except duckdb.Error as e:
            logger.error(f"Failed to add event to table {table_name}: {e}")
            logger.error(f"Event data: {event_dict}")

    def close(self):
        """Closes the database connection."""
        self.conn.close()
        logger.info("Database connection closed.")
