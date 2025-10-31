# Phase 3: Deep System Integration and Proactivity - Implementation Details

This document outlines the technical implementation of the modules introduced in Phase 3.

## Module 1: Temporal Intelligence

**Status:** ✅ Complete

The "Temporal Intelligence" module is the foundation of the system's proactivity. It introduces a new service responsible for securely and privately recording a timeline of user and system activities.

### 1. Service Structure

- A new service named `temporal` has been created under the `services/` directory.
- It follows the standard microservice architecture of the project, with a clear separation of concerns:
  - `service.py`: Main service entrypoint, orchestrating collectors and storage.
  - `config.py`: Configuration for NATS, database paths, and collector settings.
  - `models.py`: Pydantic models for structured event data (`CommandEvent`, `FileEvent`, `AppFocusEvent`, `SystemSnapshotEvent`).
  - `storage.py`: Manages the DuckDB database for storing the event timeline.
  - `collector.py`: Contains the logic for gathering different types of system events.

### 2. Data Collectors

- **`SystemSnapshotCollector`**: Periodically captures the state of the system.
- **`FilesystemCollector`**: Monitors key user directories for changes.
- **Command Collection**: The service is ready to receive command events via NATS.

### 3. Data Storage & Event Publishing

- **DuckDB** is used as the storage backend.
- After an event is stored, the `temporal` service now publishes it on the NATS bus under the subject `temporal.event.>` for other services to consume in real-time.

### 4. Integration & Testing

- The service is fully integrated into the project's lifecycle (`make start-all`, `make stop-all`).
- A utility script, `tests/query_timeline.py`, is available for inspecting the database.

## Module 2: Proactive Agent and Intelligent Notifications

**Status:** ✅ Complete

This module introduces the `agent` service, which listens to the event stream, identifies patterns, and offers contextual assistance via desktop notifications.

### 1. Service Structure

- A new `agent` service has been created under `services/`.
- Key components:
  - `service.py`: Listens to the NATS event stream.
  - `patterns.py`: Contains heuristic pattern logic (e.g., `GitClonePattern`) and orchestrates AI-driven suggestions.
  - `suggestion_engine.py`: Uses the LLM service to propose contextual follow-up actions for any command event.
  - `notifier.py`: Sends desktop notifications using `notify-send`.

### 2. Integration & Testing

- The `agent` service is managed by the project's lifecycle scripts.
- A test script, `scripts/test_proactive_agent.py`, allows for simulating a `git clone` event to trigger a notification.

## Module 3: System Control and Automation

**Status:** ✅ Complete

This module introduces the `system` service, which gives the AI direct, secure control over the system by exposing atomic actions via NATS.

### 1. Service Structure

- A new `system` service has been created.
- Key components:
  - `service.py`: Listens for action requests on the `system.action.>` NATS subject.
  - `actions.py`: Contains the implementation of the system control functions. The initial implementation includes `process.list` and `process.kill`.

### 2. Integration

- The `system` service is fully integrated into the project's lifecycle scripts (`make start-all`, `make stop-all`).

### 3. Testing

A test script is provided to verify the functionality of the exposed system actions.

1.  **Start all services**:
    ```bash
    make start-all
    ```
2.  **Run the test script**:
    ```bash
    # Make the script executable
    chmod +x scripts/test_system_service.py

    # Execute the script
    ./scripts/test_system_service.py
    ```
3.  **Check the output**: The script will call the `process.list` and `process.kill` actions and report on their success or failure.
