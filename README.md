# ProxyMaze

A lightweight, in-memory proxy health monitoring service built with FastAPI. ProxyMaze continuously probes HTTP endpoints, tracks their availability, and alerts you when your pool failure rate crosses a threshold.

## Features

- **Continuous monitoring** -- Probes your proxy pool on a configurable schedule, not just on-demand
- **Real HTTP probes** -- Status is derived from actual HTTP checks (2xx = up, timeout/5xx/connection failure = down)
- **Alert lifecycle** -- Fires alerts when failure rate >= 20%, resolves when it drops below, with at most one active alert at a time
- **Webhook delivery** -- Sends `alert.fired` and `alert.resolved` payloads to registered URLs with retry on transient failures
- **Slack & Discord integrations** -- Formatted alert notifications for your ops channels
- **Full observability** -- Per-proxy history, uptime percentages, consecutive failure tracking, and service metrics

## Quick Start

### Prerequisites

- Python 3.13+

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd proxymaze

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Service

```bash
# Development mode with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The service starts a background scheduler that begins monitoring the proxy pool immediately.

## API Reference

### Health Check

**GET /health**

Check if the service is running.

```bash
curl http://localhost:8000/health
```

Response:
```json
{"status": "ok"}
```

### Configuration

**POST /config**

Set the monitoring cadence and probe timeout. Changes apply immediately.

```bash
curl -X POST http://localhost:8000/config \
  -H "Content-Type: application/json" \
  -d '{
    "check_interval_seconds": 15,
    "request_timeout_ms": 3000
  }'
```

Response:
```json
{"check_interval_seconds": 15, "request_timeout_ms": 3000}
```

**GET /config**

Read the current runtime configuration.

### Proxy Pool Management

**POST /proxies**

Load proxy URLs into the monitoring pool. New proxies start as `pending` until their first probe completes.

```bash
curl -X POST http://localhost:8000/proxies \
  -H "Content-Type: application/json" \
  -d '{
    "proxies": [
      "https://proxy-provider.example/proxy/px-101",
      "https://proxy-provider.example/proxy/px-102"
    ],
    "replace": true
  }'
```

| Field | Type | Description |
|-------|------|-------------|
| `proxies` | string[] | List of proxy URLs to monitor |
| `replace` | boolean | If `true`, clears the existing pool first. Defaults to `false` (append). |

Response: `201 Created`
```json
{
  "accepted": 2,
  "proxies": [
    {"id": "px-101", "url": "...", "status": "pending"},
    {"id": "px-102", "url": "...", "status": "pending"}
  ]
}
```

The proxy ID is extracted from the last path segment of the URL.

**GET /proxies**

Survey the entire pool with live counts and per-proxy state.

```bash
curl http://localhost:8000/proxies
```

Response:
```json
{
  "total": 10,
  "up": 7,
  "down": 3,
  "failure_rate": 0.3,
  "proxies": [
    {
      "id": "px-101",
      "url": "...",
      "status": "up",
      "last_checked_at": "2026-04-24T10:15:30Z",
      "consecutive_failures": 0
    }
  ]
}
```

**GET /proxies/{id}**

Get detailed information about a single proxy including its full history.

```bash
curl http://localhost:8000/proxies/px-101
```

Response:
```json
{
  "id": "px-101",
  "url": "...",
  "status": "up",
  "last_checked_at": "2026-04-24T10:15:30Z",
  "consecutive_failures": 0,
  "total_checks": 12,
  "uptime_percentage": 91.7,
  "history": [
    {"checked_at": "2026-04-24T10:15:30Z", "status": "up"}
  ]
}
```

**GET /proxies/{id}/history**

Get the raw check history for a proxy as a JSON array.

```bash
curl http://localhost:8000/proxies/px-101/history
```

Response:
```json
[
  {"checked_at": "2026-04-24T10:15:30Z", "status": "up"},
  {"checked_at": "2026-04-24T10:16:00Z", "status": "down"}
]
```

**DELETE /proxies**

Clear the proxy pool. Alert history is preserved.

```bash
curl -X DELETE http://localhost:8000/proxies
```

Response: `204 No Content`

### Alerts

**GET /alerts**

Retrieve all alerts (active and resolved).

```bash
curl http://localhost:8000/alerts
```

Response:
```json
[
  {
    "alert_id": "alert-a1b2c3",
    "status": "active",
    "failure_rate": 0.3,
    "total_proxies": 10,
    "failed_proxies": 3,
    "failed_proxy_ids": ["px-103", "px-104", "px-105"],
    "threshold": 0.2,
    "fired_at": "2026-04-24T10:20:00Z",
    "resolved_at": null,
    "message": "Proxy pool failure rate exceeded threshold"
  }
]
```

### Webhooks

**POST /webhooks**

Register a URL to receive alert webhook notifications.

```bash
curl -X POST http://localhost:8000/webhooks \
  -H "Content-Type: application/json" \
  -d '{"url": "https://receiver.example/webhook"}'
```

Response: `201 Created`
```json
{"webhook_id": "wh-123abc", "url": "https://receiver.example/webhook"}
```

#### Webhook Payloads

**alert.fired** -- Delivered when the failure rate first reaches or exceeds 20%:
```json
{
  "event": "alert.fired",
  "alert_id": "alert-a1b2c3",
  "fired_at": "2026-04-24T10:20:00Z",
  "failure_rate": 0.3,
  "total_proxies": 10,
  "failed_proxies": 3,
  "failed_proxy_ids": ["px-103", "px-104", "px-105"],
  "threshold": 0.2,
  "message": "Proxy pool failure rate exceeded threshold"
}
```

**alert.resolved** -- Delivered when the pool recovers below 20%:
```json
{
  "event": "alert.resolved",
  "alert_id": "alert-a1b2c3",
  "resolved_at": "2026-04-24T10:30:00Z"
}
```

Webhooks are delivered within 60 seconds, with automatic retry on `500/502/503/504`.

### Integrations

**POST /integrations**

Register a Slack or Discord integration for formatted alert notifications.

#### Slack

```bash
curl -X POST http://localhost:8000/integrations \
  -H "Content-Type: application/json" \
  -d '{
    "type": "slack",
    "webhook_url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
    "username": "ProxyWatch",
    "events": ["alert.fired", "alert.resolved"]
  }'
```

#### Discord

```bash
curl -X POST http://localhost:8000/integrations \
  -H "Content-Type: application/json" \
  -d '{
    "type": "discord",
    "webhook_url": "https://discord.com/api/webhooks/YOUR/WEBHOOK/URL",
    "username": "ProxyWatch",
    "events": ["alert.fired", "alert.resolved"]
  }'
```

### Metrics

**GET /metrics**

Get operational monitoring data.

```bash
curl http://localhost:8000/metrics
```

Response:
```json
{
  "total_checks": 120,
  "current_pool_size": 10,
  "active_alerts": 1,
  "total_alerts": 3,
  "webhook_deliveries": 4
}
```

## Alert Behavior

- **Threshold**: 0.20 (20%)
- **Fire condition**: Failure rate >= 0.20
- **Resolve condition**: Failure rate < 0.20
- **Single active alert**: A continuous breach never creates duplicate active alerts
- **Fresh breach**: After resolution, a new breach creates a brand-new `alert_id`
- **Consistency**: `GET /proxies`, `GET /alerts`, and webhook payloads always agree on the failed proxy set

## Running Tests

```bash
python -m pytest tests/ -v
```

## Architecture

- **In-memory state** -- No database required; all state lives in `AppState` protected by an asyncio lock
- **Background scheduler** -- An async loop probes the pool at the configured interval
- **Concurrent probing** -- All proxies in the pool are checked in parallel
- **Lock-free webhook dispatch** -- Alerts hold the lock only for state updates, not during HTTP delivery
- **Pydantic v2** -- All request/response models with `extra="ignore"` for forward compatibility

## License

MIT
