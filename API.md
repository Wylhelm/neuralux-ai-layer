# Neuralux API Reference (Phase 2A)

## Health Service

### REST

- GET `/health` → Current snapshot
- GET `/history?start=<iso>&end=<iso>&interval=<sec>` → Time-range metrics

Response (abridged):

```json
{
  "status": "healthy|warning|critical",
  "current_metrics": {
    "cpu": { "usage_percent": 12.3, "per_core": [], "load_average": [0.12, 0.20, 0.25] },
    "memory": { "total": 0, "used": 0, "percent": 0 },
    "disks": [ { "mountpoint": "/", "used": 0, "free": 0, "percent": 0 } ],
    "network": { "bytes_sent": 0, "bytes_recv": 0, "connections": 0 },
    "top_processes": [ { "pid": 0, "name": "", "cpu_percent": 0, "memory_percent": 0 } ]
  },
  "alerts": [ { "level": "warning", "category": "cpu", "message": "", "value": 0, "threshold": 0 } ]
}
```

### NATS Subjects

- `system.health.current` → Current snapshot
- `system.health.history` → Time-range metrics
- `system.health.alerts` → Recent alerts
- `system.health.summary` → Aggregated health status

Example (Python):

```python
response = await message_bus.request("system.health.summary", {}, timeout=5.0)
```

## Overlay Control (NATS)

- `ui.overlay.toggle`
- `ui.overlay.show`
- `ui.overlay.hide`
- `ui.overlay.quit`

CLI helpers:

```bash
# Send control signals
aish overlay --toggle
aish overlay --show
aish overlay --hide
```
