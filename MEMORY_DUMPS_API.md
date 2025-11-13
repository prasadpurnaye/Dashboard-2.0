# Memory Dumps API Reference

## Base URL
```
http://localhost:8000/api/memory-dumps
```

## Authentication
Currently, no authentication is required. Secure with your firewall/proxy as needed.

---

## Endpoints

### 1. Trigger Memory Dumps
**POST** `/trigger`

Schedules memory dumps for one or more VMs.

#### Request
```bash
curl -X POST http://localhost:8000/api/memory-dumps/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "vm_ids": ["101", "102", "103"]
  }'
```

#### Request Body
```json
{
  "vm_ids": ["101", "102", "103"]
}
```

#### Response (200 OK)
```json
{
  "status": "scheduled",
  "message": "Memory dump scheduled for 3 VM(s)",
  "vm_ids": ["101", "102", "103"],
  "timestamp": "2025-11-11T10:30:45.123456"
}
```

#### Error Response (400)
```json
{
  "detail": "No VM IDs specified"
}
```

#### Response Time
Immediate (background task)

#### Processing Time
5-30 seconds per VM (depends on memory size)

---

### 2. Get Dump Records
**GET** `/records`

Retrieve memory dump records from InfluxDB3.

#### Request
```bash
# Get first 50 records
curl -X GET "http://localhost:8000/api/memory-dumps/records?limit=50&offset=0"

# Get records 100-150
curl -X GET "http://localhost:8000/api/memory-dumps/records?limit=50&offset=100"

# Get all records (default 1000)
curl -X GET "http://localhost:8000/api/memory-dumps/records"
```

#### Query Parameters
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | 1000 | Max records to return |
| `offset` | integer | 0 | Records to skip (pagination) |

#### Response (200 OK)
```json
{
  "records": [
    {
      "timestamp": "2025-11-11T10:30:00.000000",
      "dom": "vm-web-01",
      "vmid": "101",
      "sha256": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6",
      "duration_sec": 5.234,
      "gzip_size_bytes": 2147483648,
      "ctime": 1699520400,
      "mtime": 1699520405,
      "atime": 1699520410,
      "dump_path": "/var/dumps/101_1699520400.mem.gz"
    },
    {
      "timestamp": "2025-11-10T15:45:30.000000",
      "dom": "vm-db-01",
      "vmid": "102",
      "sha256": "z9y8x7w6v5u4t3s2r1q0p9o8n7m6l5k4j3i2h1g0f9e8d7c6b5a4",
      "duration_sec": 8.567,
      "gzip_size_bytes": 3221225472,
      "ctime": 1699430730,
      "mtime": 1699430738,
      "atime": 1699430745,
      "dump_path": "/var/dumps/102_1699430730.mem.gz"
    }
  ],
  "count": 2,
  "limit": 50,
  "offset": 0
}
```

#### Response Fields
| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | ISO 8601 | When the dump was created |
| `dom` | string | VM domain/name |
| `vmid` | string | VM ID |
| `sha256` | string | SHA256 hash of raw dump |
| `duration_sec` | float | Time to complete dump |
| `gzip_size_bytes` | integer | Compressed size in bytes |
| `ctime` | integer | File creation Unix timestamp |
| `mtime` | integer | File modification Unix timestamp |
| `atime` | integer | File access Unix timestamp |
| `dump_path` | string | Full path to dump file |

#### Error Response (500)
```json
{
  "detail": "Error fetching records: [error details]"
}
```

---

### 3. Get Dump Status
**GET** `/status`

Get the status of the last memory dump operation.

#### Request
```bash
curl -X GET http://localhost:8000/api/memory-dumps/status
```

#### Response (200 OK) - Completed
```json
{
  "last_trigger": {
    "timestamp": "2025-11-11T10:30:45.123456",
    "vm_ids": ["101", "102"],
    "status": "completed",
    "duration": 15.234
  },
  "status": "completed",
  "vm_ids": ["101", "102"],
  "timestamp": "2025-11-11T10:30:45.123456",
  "duration": 15.234,
  "error": null
}
```

#### Response (200 OK) - In Progress
```json
{
  "last_trigger": {
    "timestamp": "2025-11-11T10:30:45.123456",
    "vm_ids": ["101", "102"],
    "status": "in_progress"
  },
  "status": "in_progress",
  "vm_ids": ["101", "102"],
  "timestamp": "2025-11-11T10:30:45.123456",
  "duration": null,
  "error": null
}
```

#### Response (200 OK) - Idle
```json
{
  "last_trigger": {},
  "status": "idle",
  "vm_ids": [],
  "timestamp": null,
  "duration": null,
  "error": null
}
```

#### Possible Status Values
| Status | Meaning |
|--------|---------|
| `idle` | No operations in progress |
| `in_progress` | Dump currently running |
| `completed` | Last dump completed successfully |
| `failed` | Last dump encountered an error |
| `timeout` | Dump exceeded 5-minute timeout |
| `error` | Unexpected error occurred |

---

### 4. Get Dump Statistics
**GET** `/stats`

Get aggregate statistics about all dumps.

#### Request
```bash
curl -X GET http://localhost:8000/api/memory-dumps/stats
```

#### Response (200 OK)
```json
{
  "total_dumps": 42,
  "total_vms": 5,
  "total_size_bytes": 107374182400,
  "avg_duration_sec": 4.567,
  "last_dump": "2025-11-11T10:30:00.000000"
}
```

#### Response Fields
| Field | Type | Description |
|-------|------|-------------|
| `total_dumps` | integer | Total number of dumps recorded |
| `total_vms` | integer | Number of unique VMs dumped |
| `total_size_bytes` | integer | Total compressed size of all dumps |
| `avg_duration_sec` | float | Average dump time |
| `last_dump` | ISO 8601 | Timestamp of most recent dump |

#### Statistics Calculations
- **Storage Used**: `total_size_bytes / 1024 / 1024 / 1024` (GB)
- **Per-Dump Average**: `total_size_bytes / total_dumps` (bytes)
- **Per-VM Average**: `total_dumps / total_vms` (dumps per VM)

---

## Common Usage Patterns

### Pattern 1: Weekly Automated Dump
```bash
#!/bin/bash
# Trigger dumps every Monday at 2 AM

# Add to crontab:
# 0 2 * * 1 curl -X POST http://localhost:8000/api/memory-dumps/trigger \
#   -H "Content-Type: application/json" \
#   -d '{"vm_ids": ["all"]}'
```

### Pattern 2: Check Dump Progress
```bash
#!/bin/bash
# Poll status until complete

while true; do
  status=$(curl -s http://localhost:8000/api/memory-dumps/status | jq -r '.status')
  if [ "$status" = "completed" ] || [ "$status" = "failed" ]; then
    echo "Dump finished with status: $status"
    break
  fi
  echo "Status: $status - waiting..."
  sleep 5
done
```

### Pattern 3: Export Recent Dumps
```python
import requests
import csv
from datetime import datetime, timedelta

# Get dumps from last 7 days
limit = 1000
response = requests.get(f'http://localhost:8000/api/memory-dumps/records?limit={limit}')
records = response.json()['records']

# Filter by date
week_ago = (datetime.now() - timedelta(days=7)).isoformat()
recent = [r for r in records if r['timestamp'] > week_ago]

# Export to CSV
with open('recent_dumps.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=recent[0].keys())
    writer.writeheader()
    writer.writerows(recent)

print(f"Exported {len(recent)} recent dumps")
```

### Pattern 4: Analyze Storage Usage
```python
import requests

stats = requests.get('http://localhost:8000/api/memory-dumps/stats').json()

total_gb = stats['total_size_bytes'] / (1024**3)
avg_gb = (stats['total_size_bytes'] / stats['total_dumps']) / (1024**3)

print(f"Total Storage: {total_gb:.2f} GB")
print(f"Average Dump: {avg_gb:.2f} GB")
print(f"Total VMs: {stats['total_vms']}")
print(f"Total Dumps: {stats['total_dumps']}")
print(f"Avg Duration: {stats['avg_duration_sec']:.2f}s")
```

### Pattern 5: Monitor for Failures
```python
import requests
import time

while True:
    status = requests.get('http://localhost:8000/api/memory-dumps/status').json()
    
    if status['status'] == 'failed':
        print(f"❌ ALERT: Dump failed!")
        print(f"Error: {status['error']}")
        # Send email/slack notification here
        break
    
    if status['status'] == 'completed':
        print(f"✅ Dump completed in {status['duration']:.2f}s")
        break
    
    print(f"⏳ Status: {status['status']}")
    time.sleep(5)
```

---

## Rate Limiting

Currently no rate limiting is implemented. Consider adding:

1. **Query Limits**: Max 1000 records per request
2. **Trigger Limits**: Max 1 dump per 60 seconds
3. **Concurrent Limits**: Max 3 concurrent dumps

---

## Data Types

### Timestamps
- Format: ISO 8601 with microseconds
- Example: `2025-11-11T10:30:45.123456`
- Timezone: UTC
- Parseable by: JavaScript `new Date()`, Python `datetime.fromisoformat()`

### File Sizes
- Format: Bytes (integer)
- Examples:
  - 1 MB = 1,048,576 bytes
  - 1 GB = 1,073,741,824 bytes
  - 2 GB = 2,147,483,648 bytes

### Durations
- Format: Seconds (float)
- Precision: Milliseconds (3 decimal places)
- Example: 5.234 seconds

### Hashes
- Algorithm: SHA256
- Format: Hexadecimal string
- Length: 64 characters
- Example: `a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6`

---

## Error Handling

### HTTP Status Codes
| Code | Meaning | Example |
|------|---------|---------|
| 200 | Success | Dump triggered, records fetched |
| 400 | Bad Request | Invalid JSON, missing parameters |
| 500 | Server Error | InfluxDB unavailable, subprocess failure |

### Error Response Format
```json
{
  "detail": "Human-readable error message"
}
```

### Common Error Scenarios

**Missing VM IDs:**
```json
{
  "detail": "No VM IDs specified"
}
```

**InfluxDB Unavailable:**
```json
{
  "detail": "Error fetching records: Connection refused"
}
```

**Subprocess Timeout:**
```json
{
  "detail": "Error: Dump exceeded 5-minute timeout"
}
```

---

## Performance Characteristics

| Operation | Typical Time | Range |
|-----------|--------------|-------|
| Trigger dump | <100ms | Immediate response |
| Single VM dump | 2-5s | 1-10s depending on size |
| All VMs dump | 20-120s | N * single dump time |
| Query 1000 records | 500-1000ms | Network dependent |
| Export CSV | 100-200ms | File size dependent |

---

## Monitoring & Alerts

### Recommended Metrics to Track

1. **Dump Duration Trend**
   ```sql
   SELECT AVG(duration_sec) FROM mem_dumps 
   GROUP BY time(1d)
   ```

2. **Storage Growth**
   ```sql
   SELECT SUM(gzip_size_bytes) FROM mem_dumps 
   GROUP BY time(1d)
   ```

3. **Failed Dumps**
   Monitor `/status` endpoint for `"status": "failed"`

4. **Query Performance**
   Monitor API response times

### Alert Thresholds (Recommendations)

- ⚠️ Dump duration > 10 minutes
- 🔴 Dump failed (any status != completed)
- ⚠️ Storage > 1 TB (adjust based on capacity)
- 🔴 API latency > 5 seconds

---

## Integration Examples

### JavaScript/React
```javascript
async function dumpVM(vmId) {
  const response = await fetch('/api/memory-dumps/trigger', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ vm_ids: [vmId] })
  });
  return response.json();
}

async function getRecords(limit = 50, offset = 0) {
  const response = await fetch(
    `/api/memory-dumps/records?limit=${limit}&offset=${offset}`
  );
  return response.json();
}
```

### Python/Requests
```python
import requests

# Trigger dumps
response = requests.post(
    'http://localhost:8000/api/memory-dumps/trigger',
    json={'vm_ids': ['101', '102']}
)
print(response.json())

# Get records
records = requests.get('http://localhost:8000/api/memory-dumps/records').json()
for record in records['records']:
    print(f"{record['dom']}: {record['gzip_size_bytes']} bytes")
```

### cURL
```bash
# Trigger
curl -X POST http://localhost:8000/api/memory-dumps/trigger \
  -H "Content-Type: application/json" \
  -d '{"vm_ids":["101"]}'

# Get records
curl http://localhost:8000/api/memory-dumps/records?limit=10

# Get stats
curl http://localhost:8000/api/memory-dumps/stats
```

---

## Changelog

### Version 1.0.0 (2025-11-11)
- ✅ Initial release
- ✅ 4 endpoints
- ✅ InfluxDB3 integration
- ✅ Background dump processing
- ✅ Statistics and status tracking

---

**Last Updated**: November 11, 2025  
**API Version**: 1.0.0  
**Status**: Stable ✅
