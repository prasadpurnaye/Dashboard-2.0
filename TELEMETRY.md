# Telemetry Monitoring Setup

## Overview

The telemetry system provides secure, modular monitoring of KVM/QEMU virtual machines with metrics stored in InfluxDB.

**Key Features:**
- ✅ Secure credential storage (environment variables only)
- ✅ Background collection thread with start/stop controls
- ✅ Modular architecture (KVM, InfluxDB, Collector, API)
- ✅ REST API for managing collection
- ✅ Web UI controls

## Architecture

```
┌─────────────────────────────────────────────────┐
│          Dashboard Web Interface                 │
│    (Start/Stop/Status Telemetry Controls)        │
└────────────────┬────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│        Telemetry API Routes (/api/telemetry)    │
│  ├─ POST /start    (start collection)           │
│  ├─ POST /stop     (stop collection)            │
│  ├─ GET  /status   (get status & stats)         │
│  ├─ GET  /vms      (list monitored VMs)         │
│  └─ GET  /config   (get safe config)            │
└────────────────┬────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│       TelemetryCollector Service                 │
│  ├─ Coordinates KVM and InfluxDB                │
│  ├─ Runs collection loop in background          │
│  ├─ Tracks metrics and errors                   │
│  └─ Computes rate features                      │
└────┬─────────────────────────────────┬──────────┘
     │                                 │
┌────▼──────────────┐      ┌──────────▼────────────┐
│  KVMConnector     │      │  InfluxConnector      │
│  ├─ libvirt API   │      │  ├─ Batch writer      │
│  ├─ Get live VMs  │      │  ├─ Queue-based       │
│  ├─ Device info   │      │  ├─ Background thread │
│  └─ Connection    │      │  └─ Line protocol     │
└────┬──────────────┘      └──────────┬────────────┘
     │                                 │
┌────▼──────────────┐      ┌──────────▼────────────┐
│  KVM/QEMU Host    │      │  InfluxDB v3          │
│  (libvirt API)    │      │  (Line Protocol API)  │
└───────────────────┘      └───────────────────────┘
```

## Module Structure

```
src/
├── config/
│   ├── __init__.py
│   └── telemetry_config.py          # Secure configuration
├── telemetry/
│   ├── __init__.py
│   ├── kvm_connector.py             # Libvirt connector
│   ├── influx_connector.py          # InfluxDB writer
│   └── collector.py                 # Main coordinator
└── api/
    └── telemetry.py                 # REST API endpoints
```

## Configuration

### Environment Variables

**Required:**
```bash
# KVM/Libvirt
export LIBVIRT_URI="qemu+ssh://oneadmin@192.168.0.104/system"

# InfluxDB v3
export INFLUX_URL="http://127.0.0.1:8181"
export INFLUX_DB="vmstats"
export INFLUX_TOKEN="apiv3_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

**Optional:**
```bash
export POLL_INTERVAL="1.0"              # Collection interval in seconds (default: 1.0)
export BATCH_MAX_LINES="2000"           # Max lines per InfluxDB write (default: 2000)
export BATCH_MAX_SEC="1.0"              # Max time before InfluxDB flush (default: 1.0)
export DEVICE_CACHE_TTL="300"           # Device cache lifetime (default: 300s)
export LIBVIRT_TIMEOUT="30.0"           # Libvirt timeout (default: 30.0s)
```

### Example Setup

```bash
# Set environment variables
export LIBVIRT_URI="qemu+ssh://oneadmin@192.168.0.104/system"
export INFLUX_URL="http://127.0.0.1:8181"
export INFLUX_DB="vmstats"
export INFLUX_TOKEN="apiv3_LNeKzeLNyQqZAFJiVPN96OUVtjeYsdJURAGDXwi3rq5NZCPfpTpbzr0C096s9m9"

# Run FastAPI server
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

### Start Telemetry Collection
```bash
POST /api/telemetry/start
```
**Response:**
```json
{
  "status": "started",
  "message": "Telemetry collection started successfully",
  "details": {
    "running": true,
    "started_at": "2025-11-11T12:34:56.789Z",
    "vms_monitored": 5,
    "total_collections": 0
  }
}
```

### Stop Telemetry Collection
```bash
POST /api/telemetry/stop
```
**Response:**
```json
{
  "status": "stopped",
  "message": "Telemetry collection stopped successfully"
}
```

### Get Telemetry Status
```bash
GET /api/telemetry/status
```
**Response:**
```json
{
  "running": true,
  "started_at": "2025-11-11T12:34:56.789Z",
  "total_collections": 150,
  "total_errors": 2,
  "last_collection_time": "2025-11-11T12:40:00.123Z",
  "vms_monitored": 5,
  "influx_queue_size": 45,
  "config": {
    "libvirt_uri": "***",
    "influx_url": "***",
    "influx_db": "vmstats",
    "poll_interval": 1.0
  }
}
```

### Get Monitored VMs
```bash
GET /api/telemetry/vms
```
**Response:**
```json
{
  "count": 5,
  "vms": [
    {
      "id": 1,
      "name": "vm-server-01",
      "uuid": "550e8400-e29b-41d4-a716-446655440000",
      "state": "running",
      "cpu_count": 4,
      "memory_max": 8388608,
      "memory_used": 4194304,
      "cputime": 123456789
    }
  ]
}
```

### Get Configuration
```bash
GET /api/telemetry/config
```
**Response:**
```json
{
  "config": {
    "libvirt_uri": "***",
    "influx_url": "***",
    "influx_db": "vmstats",
    "poll_interval": 1.0,
    "batch_max_lines": 2000,
    "batch_max_sec": 1.0,
    "device_cache_ttl": 300.0
  }
}
```

## Usage

### Python Code

```python
from src.config.telemetry_config import TelemetryConfig
from src.telemetry.collector import TelemetryCollector

# Load configuration from environment
config = TelemetryConfig.from_env()

# Create and start collector
collector = TelemetryCollector(config)
collector.start()

# Monitor status
print(collector.get_status())

# Stop when done
collector.stop()
```

### Web Interface

The dashboard provides UI controls to:
1. **Start** telemetry collection
2. **Stop** telemetry collection
3. **View** collection status and statistics
4. **Monitor** active VMs

## Security Features

✅ **Credentials Never Exposed:**
- Environment variables only (not in code)
- API returns masked values (*** for sensitive data)
- Tokens stored only in memory for active connections

✅ **Secure Configuration:**
- All credentials validated at startup
- Missing credentials prevent telemetry init
- Clear error messages without exposing secrets

✅ **Modular Design:**
- Each component handles single responsibility
- Easy to test and audit
- Clean separation of concerns

## Error Handling

The system gracefully handles:
- Libvirt connection failures
- InfluxDB write failures
- Missing environment variables
- Invalid configurations
- Network timeouts

All errors are logged but never exposed to frontend.

## Performance

- **Background threading:** Collection doesn't block HTTP requests
- **Batched writes:** Reduces InfluxDB load
- **Queue-based:** Handles burst metrics gracefully
- **Device caching:** Reduces repeated XML parsing

## Monitoring Metrics Collected

Per VM:
- Virtual CPU count and time
- Memory usage and statistics
- Network interface stats (RX/TX bytes, packets, errors, drops)
- Disk I/O (read/write requests, bytes, errors)
- Derived features (rate, angle_deg)

## Troubleshooting

### Telemetry not initializing
```bash
# Check environment variables
echo $LIBVIRT_URI
echo $INFLUX_URL
echo $INFLUX_DB
echo $INFLUX_TOKEN
```

### No VMs showing
```bash
# Verify libvirt connectivity
virsh -c qemu+ssh://user@host/system list
```

### InfluxDB write failures
```bash
# Check InfluxDB is running
curl http://localhost:8181/api/v3/config

# Verify token is valid
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8181/api/v3/ping
```

## References

- [Libvirt Documentation](https://libvirt.org/)
- [InfluxDB v3 Line Protocol](https://docs.influxdata.com/influxdb/cloud/reference/line-protocol/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
