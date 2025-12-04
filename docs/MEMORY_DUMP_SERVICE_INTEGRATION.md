# Memory Dump Service Integration

This document describes the integration between the Dashboard API and the remote `memdump_service`.

## Overview

The memory dump module has been refactored to use a remote HTTP-based memory dump service instead of executing dumps locally. The service running at `http://10.10.0.94:5001` handles all memory dump operations for KVM/libvirt VMs.

### Benefits
- **Decoupled**: Dumps can be triggered from the Dashboard but executed on a remote host
- **Scalable**: Concurrent dumps are capped at `MAX_PARALLEL_DUMPS` on the service side
- **Resilient**: Per-VM exclusion ensures only one active dump per VM at a time
- **Observable**: Real-time progress tracking for each dump operation

## Configuration

Set these environment variables to customize the integration:

```bash
# memdump_service endpoint
MEMDUMP_SERVICE_URL=http://10.10.0.94:5001

# HTTP request timeout for memdump_service calls (seconds)
MEMDUMP_SERVICE_TIMEOUT=30
```

## API Endpoints

### Trigger Memory Dumps

**Endpoint**: `POST /api/memory-dumps/trigger`

Trigger memory dumps for one or more VMs.

**Request Body**:
```json
{
  "vms": ["vm_name_1", "vm_name_2"]
}
```

Or alternatively:
```json
{
  "vm_ids": ["vm_name_1", "vm_name_2"]
}
```

**Response**:
```json
{
  "status": "scheduled",
  "message": "Memory dump scheduled for 2 VM(s)",
  "vm_ids": ["vm_name_1", "vm_name_2"],
  "timestamp": "2025-11-14T14:28:23.509869"
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/api/memory-dumps/trigger \
  -H "Content-Type: application/json" \
  -d '{"vms": ["my-vm-1", "my-vm-2"]}'
```

### Get All Dump Status

**Endpoint**: `GET /api/memory-dumps/status`

Get status of all active dumps from the memdump_service.

**Response**:
```json
{
  "service": "http://10.10.0.94:5001",
  "status": "ok",
  "active_dumps": {
    "my-vm-1": {
      "dump_id": "uuid-here",
      "vm": "my-vm-1",
      "state": "running",
      "progress": 45.5,
      "message": "Dump in progress (45.5%)",
      "started_at": "2025-11-14T08:58:23.550273Z",
      "finished_at": null,
      "dump_path": "/home/r/Desktop/1_1699970303.mem",
      "duration_sec": null
    }
  },
  "last_trigger": {
    "timestamp": "2025-11-14T14:28:23.520194",
    "vm_ids": ["my-vm-1", "my-vm-2"],
    "status": "in_progress",
    "trigger_response": {...}
  },
  "timestamp": "2025-11-14T14:28:23.509869"
}
```

**Example**:
```bash
curl http://localhost:8000/api/memory-dumps/status | python3 -m json.tool
```

### Get Status for Specific VM

**Endpoint**: `GET /api/memory-dumps/status/{vm_id}`

Get detailed status of a specific VM's dump operation.

**Response**:
```json
{
  "dump_id": "uuid-here",
  "vm": "my-vm-1",
  "state": "running",
  "progress": 45.5,
  "message": "Dump in progress (45.5%)",
  "started_at": "2025-11-14T08:58:23.550273Z",
  "finished_at": null,
  "dump_path": "/home/r/Desktop/1_1699970303.mem",
  "duration_sec": null
}
```

**States**:
- `queued`: Waiting to be processed
- `running`: Currently dumping (progress 0-100%)
- `completed`: Successfully finished
- `failed`: Encountered an error

**Example**:
```bash
curl http://localhost:8000/api/memory-dumps/status/my-vm-1 | python3 -m json.tool
```

### Get Dump Records

**Endpoint**: `GET /api/memory-dumps/records?limit=100&offset=0`

Fetch memory dump records from InfluxDB3. Records contain metadata written by the memdump_service.

**Query Parameters**:
- `limit`: Number of records to return (default: 1000, max recommended: 10000)
- `offset`: Skip first N records (default: 0)

**Response**:
```json
{
  "records": [
    {
      "time": "2025-11-14T08:58:30.123456Z",
      "dom": "vm-name-1",
      "vmid": "10",
      "sha256": "a1b2c3d4e5f6...",
      "duration_sec": 7.25,
      "gzip_size_bytes": 2147483648,
      "ctime": 1699970310,
      "mtime": 1699970317,
      "atime": 1699970320,
      "dump_path": "/home/r/Desktop/10_1699970303.mem"
    }
  ],
  "count": 1,
  "limit": 1000,
  "offset": 0
}
```

**Example**:
```bash
curl "http://localhost:8000/api/memory-dumps/records?limit=10" | python3 -m json.tool
```

### Get Dump Statistics

**Endpoint**: `GET /api/memory-dumps/stats`

Get aggregate statistics about all memory dumps from InfluxDB3.

**Response**:
```json
{
  "total_dumps": 42,
  "total_vms": 8,
  "total_size_bytes": 85899345920,
  "avg_duration_sec": 12.5,
  "last_dump": "2025-11-14T08:58:30.123456Z"
}
```

**Example**:
```bash
curl http://localhost:8000/api/memory-dumps/stats | python3 -m json.tool
```

## Workflow

### Triggering a Dump

1. **Dashboard** sends `POST /api/memory-dumps/trigger` with VM names
2. **Dashboard API** spawns a background task that:
   - POSTs to `memdump_service /api/dumps` to trigger the dump
   - Polls `memdump_service /api/dumps` every 5 seconds for status
   - Continues polling until all requested VMs are completed/failed (or timeout)
3. **memdump_service** executes the actual memory dumps on its configured libvirt host
4. **memdump_service** writes metadata to InfluxDB3 when dumps complete
5. **Dashboard API** updates internal `active_dumps` dict with final status

### Checking Status

1. **Frontend** calls `GET /api/memory-dumps/status` to see all active dumps
2. **Dashboard API** proxies call to `memdump_service /api/dumps`
3. Returns live status including progress percentage and messages

### Historical Records

1. **Frontend** calls `GET /api/memory-dumps/records` to see past dumps
2. **Dashboard API** queries InfluxDB3 directly
3. Returns sorted list of completed dumps with metadata (path, hash, size, etc.)

## Error Handling

### Service Unavailable

If `memdump_service` is unreachable:
- `/api/memory-dumps/status` returns status "unavailable" with error message
- `/api/memory-dumps/trigger` returns 503 error
- `/api/memory-dumps/status/{vm_id}` returns 503 error

### VM Not Found

If a requested VM doesn't exist on the memdump_service host:
- The dump will fail with state "failed"
- Error message indicates "Domain not found"
- Check that VM names match those on the remote libvirt host

### InfluxDB Query Failures

If InfluxDB is unavailable when fetching records/stats:
- `/api/memory-dumps/records` falls back from SQL to InfluxQL
- If both fail, returns empty records with error message
- `/api/memory-dumps/stats` returns partial results with warnings for failed metrics

## Integration Flow Diagram

```
┌─────────────────┐
│   Dashboard UI  │
└────────┬────────┘
         │
         │ POST /api/memory-dumps/trigger
         ↓
┌─────────────────────────────────┐
│   Dashboard API                 │
│ ├─ POST memdump_service/dumps   │
│ ├─ Poll memdump_service/dumps   │
│ └─ Update active_dumps state    │
└────────┬────────────────────────┘
         │
         ├─────────────────────────────────────┐
         │                                     │
         ↓                                     ↓
┌──────────────────────┐           ┌──────────────────────┐
│  memdump_service     │           │    InfluxDB3         │
│ ├─ Get libvirt VMs   │           │ ├─ Store mem_dumps   │
│ ├─ Execute dumps     │           │ └─ Store metadata    │
│ └─ Hash files        │───────────→ (sha256, path, etc)  │
└──────────────────────┘           └──────────────────────┘
         │
         ↓
┌──────────────────────┐
│  libvirt Host        │
│ ├─ qemu processes    │
│ └─ Memory dumps      │
└──────────────────────┘
```

## Concurrency & Limits

### Remote Service

- **MAX_PARALLEL_DUMPS**: Limited to 2 concurrent dumps by default
- **Per-VM Exclusion**: Only one active dump per VM at a time
- **Timeout**: 1 hour maximum wait per dump cycle

### Local Dashboard

- **Polling Interval**: 5 seconds between status checks
- **HTTP Timeout**: 30 seconds per request to memdump_service
- **Background Tasks**: Unlimited (limited by FastAPI task scheduler)

## Environment Variables Reference

```bash
# Service URL
MEMDUMP_SERVICE_URL=http://10.10.0.94:5001

# Service communication timeout
MEMDUMP_SERVICE_TIMEOUT=30

# InfluxDB configuration (for records/stats)
INFLUX_URL=http://localhost:8181
INFLUX_DB=vmstats
INFLUX_TOKEN=your-token-here
```

## Testing

### Manual Test: Trigger Dump

```bash
# Trigger dumps for two VMs
curl -X POST http://localhost:8000/api/memory-dumps/trigger \
  -H "Content-Type: application/json" \
  -d '{"vms": ["vm1", "vm2"]}'

# Check status
curl http://localhost:8000/api/memory-dumps/status

# Check specific VM
curl http://localhost:8000/api/memory-dumps/status/vm1
```

### Manual Test: Query Records

```bash
# Get recent dumps
curl "http://localhost:8000/api/memory-dumps/records?limit=5"

# Get statistics
curl http://localhost:8000/api/memory-dumps/stats
```

## Troubleshooting

### Dumps Always Fail with "Domain not found"

- **Cause**: VM names don't match between Dashboard and memdump_service host
- **Solution**: Use VM names that exist on the memdump_service's libvirt host
- **Check**: SSH to 10.10.0.94 and run `virsh list --all`

### Service Unreachable

- **Cause**: memdump_service not running or firewall blocking
- **Solution**: 
  - Verify service is running: `ssh 10.10.0.94 'ps aux | grep memdump_service'`
  - Test connectivity: `curl http://10.10.0.94:5001/api/dumps`
  - Check firewall rules on 10.10.0.94

### InfluxDB Records Not Showing

- **Cause**: memdump_service can't reach InfluxDB or write is failing
- **Solution**:
  - Check memdump_service logs for write errors
  - Verify INFLUX_URL and INFLUX_TOKEN are correct
  - Check InfluxDB is running and accessible

### Progress Stuck at 0%

- **Cause**: Estimated file size doesn't match actual dump size
- **Solution**: Normal - progress is approximate based on maxMemory vs actual file size. Wait for completion.

## Future Enhancements

- [ ] Support scheduled dumps at regular intervals
- [ ] Add dump storage backend selection (local, S3, etc)
- [ ] Implement automatic dump retention policies
- [ ] Add dump comparison/analysis features
- [ ] Support dump compression options
- [ ] Real-time progress WebSocket streaming
