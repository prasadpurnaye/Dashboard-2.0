# Memory Dump Service Integration - Quick Reference

## Service Connection

```
Dashboard API (localhost:8000)
         ↓ HTTP
memdump_service (10.10.0.94:5001)
         ↓ libvirt
Remote KVM Host
```

## API Endpoints

### Trigger Dumps
```bash
POST /api/memory-dumps/trigger
Content-Type: application/json

{"vms": ["vm1", "vm2"]}
```

### Get All Dump Status
```bash
GET /api/memory-dumps/status
```
Returns: Service health, active dumps, last trigger info

### Get Specific VM Status
```bash
GET /api/memory-dumps/status/{vm_id}
```
Returns: Individual dump progress and state

### Get Historical Records
```bash
GET /api/memory-dumps/records?limit=100&offset=0
```
Returns: Past dumps from InfluxDB

### Get Statistics
```bash
GET /api/memory-dumps/stats
```
Returns: Aggregate dump statistics

## Dump States

| State | Meaning |
|-------|---------|
| `queued` | Waiting to run |
| `running` | Currently dumping (progress 0-100%) |
| `completed` | Successfully finished |
| `failed` | Error occurred |

## Environment Setup

```bash
# Optional - defaults provided
export MEMDUMP_SERVICE_URL=http://10.10.0.94:5001
export MEMDUMP_SERVICE_TIMEOUT=30
```

## Real-World Example

### Step 1: Trigger Dumps
```bash
curl -X POST http://localhost:8000/api/memory-dumps/trigger \
  -H "Content-Type: application/json" \
  -d '{"vms": ["web-server", "db-server"]}'
```

### Step 2: Check Status Immediately
```bash
curl http://localhost:8000/api/memory-dumps/status
```

Response shows `state: "queued"` - dumps in queue

### Step 3: Wait and Check Again
```bash
sleep 5
curl http://localhost:8000/api/memory-dumps/status
```

Response shows `state: "running"` with progress percentage

### Step 4: Monitor Specific VM
```bash
curl http://localhost:8000/api/memory-dumps/status/web-server
```

### Step 5: View Final Results
```bash
curl http://localhost:8000/api/memory-dumps/records?limit=5
```

Returns recent completed dumps with file paths and hashes

## Typical Workflow

1. **User clicks "Dump" button** in dashboard UI
2. **UI calls** `POST /api/memory-dumps/trigger` with VM names
3. **API returns immediately** with "scheduled" status
4. **Backend spawns polling task** (non-blocking)
5. **Polling task** monitors memdump_service every 5 seconds
6. **UI periodically calls** `GET /api/memory-dumps/status` to update display
7. **When complete**, UI shows dump path and download link

## Common Issues & Fixes

| Issue | Cause | Fix |
|-------|-------|-----|
| "Domain not found" | VM name doesn't exist on remote host | Use correct VM name from `virsh list --all` on 10.10.0.94 |
| Service unavailable | memdump_service not running or unreachable | Check: `curl http://10.10.0.94:5001/api/dumps` |
| Dumps don't appear in records | InfluxDB write failing | Check memdump_service logs and InfluxDB connectivity |
| Progress stuck at 0% | Normal - based on estimated size | Let it complete, progress is approximate |
| Timeout after 1 hour | Very large dump or network issues | Check dump size and network connection |

## Performance Notes

- **Trigger Response Time**: <100ms
- **Status Check Response Time**: <50ms
- **Concurrent Dumps**: Limited to 2 (configurable on memdump_service)
- **Max Dump Wait Time**: 1 hour
- **Polling Interval**: 5 seconds

## URL Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/memory-dumps/trigger` | POST | Start dumps |
| `/api/memory-dumps/status` | GET | Check all active dumps |
| `/api/memory-dumps/status/{id}` | GET | Check specific VM |
| `/api/memory-dumps/records` | GET | View historical dumps |
| `/api/memory-dumps/stats` | GET | Get statistics |

## Architecture Notes

### Frontend Integration
The Dashboard frontend can call these endpoints to:
1. Display a "Request Dump" button
2. Show real-time progress as dumps run
3. Display completed dumps with download links
4. Show dump statistics in a dashboard widget

### Backend Integration
The Dashboard backend:
1. Accepts dump requests
2. Forwards to memdump_service
3. Polls for status updates
4. Queries InfluxDB for historical data
5. Provides status to frontend

### Data Flow
```
User Request
    ↓
Dashboard API (/api/memory-dumps/*)
    ↓
memdump_service (/api/dumps)
    ↓
libvirt → VMs → Memory → Disk
    ↓
InfluxDB (metadata)
    ↓
Dashboard API (query & return)
    ↓
Dashboard UI (display)
```

## Testing Checklist

- [ ] Service URL configured correctly
- [ ] Can connect to memdump_service: `curl http://10.10.0.94:5001/api/dumps`
- [ ] Trigger endpoint responds: `POST /api/memory-dumps/trigger`
- [ ] Status endpoint responds: `GET /api/memory-dumps/status`
- [ ] VM name resolves on remote host: `virsh list --all | grep vm-name`
- [ ] InfluxDB has mem_dumps measurement
- [ ] Records endpoint returns data: `GET /api/memory-dumps/records`

## Support

For issues or questions:
1. Check memdump_service logs: `tail -f <service-logs>`
2. Verify connectivity: `curl http://10.10.0.94:5001/api/dumps`
3. Check InfluxDB: `influx query 'from(bucket:"vmstats") |> range(start:-1h) |> filter(fn: (r) => r._measurement == "mem_dumps")'`
4. Review Dashboard logs: `tail -f <dashboard-logs>`
