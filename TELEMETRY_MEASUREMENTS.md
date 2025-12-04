# Telemetry Module - InfluxDB3 Measurements Documentation

**Date:** November 13, 2025  
**Module:** `src/telemetry/`  
**Status:** ✅ Production Ready

---

## Overview

The telemetry module is a background service that continuously monitors KVM virtual machines and writes performance metrics to InfluxDB3. It uses line protocol format for efficient data storage and retrieval.

---

## InfluxDB3 Measurements Created

### 1. **vm_metrics** (Primary Measurement)

**Purpose:** Stores basic VM state and resource information

**Tags (indexed fields):**
- `VMID` - Virtual machine ID (numeric)
- `name` - Virtual machine name
- `uuid` - Virtual machine UUID

**Fields (data points):**
| Field | Type | Unit | Description |
|-------|------|------|-------------|
| `state` | string | - | VM state (running, paused, stopped) |
| `cpu_count` | integer | cores | Number of vCPU cores allocated |
| `memory_max_kb` | integer | KB | Maximum memory allocation |
| `memory_used_kb` | integer | KB | Current memory usage |
| `cputime_ns` | integer | nanoseconds | Cumulative CPU time used |

**Example Line Protocol:**
```
vm_metrics,VMID=1,name=ubuntu-vm,uuid=550e8400-e29b-41d4-a716-446655440000 state="running",cpu_count=2i,memory_max_kb=2097152i,memory_used_kb=1048576i,cputime_ns=5000000000i 1699868400000000000
```

**Time Range:** Real-time collection (every poll_interval, default: 5 seconds)

**Retention Policy:** Database default

---

### 2. **vm_features** (Derived Measurement)

**Purpose:** Stores computed performance features and trends

**Tags (indexed fields):**
- `VMID` - Virtual machine ID
- `name` - Virtual machine name
- `uuid` - Virtual machine UUID

**Fields (data points):**
| Field | Type | Unit | Description |
|-------|------|------|-------------|
| `memory_rate_kb_per_sec` | float | KB/sec | Memory usage rate of change |
| `memory_angle_deg` | float | degrees | Angular representation of memory trend |

**Calculation Logic:**
```python
# Memory rate
dt_sec = (current_timestamp - previous_timestamp).total_seconds()
memory_delta = current_memory_used - previous_memory_used
memory_rate_kb_per_sec = memory_delta / dt_sec

# Memory angle (arctangent for visualization)
memory_angle_deg = degrees(atan(memory_rate_kb_per_sec + 1e-12))
```

**Example Line Protocol:**
```
vm_features,VMID=1,name=ubuntu-vm,uuid=550e8400-e29b-41d4-a716-446655440000 memory_rate_kb_per_sec=1024.5,memory_angle_deg=45.3 1699868400000000000
```

**Frequency:** Every collection interval where previous metrics exist

**Note:** Created only if previous metrics available (after first 2 collections)

---

## Data Collection Architecture

### Collection Flow

```
┌─────────────────────────────────────────────────────────┐
│                 KVM Connector                            │
│         (Reads VM data from libvirt)                     │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ↓
┌─────────────────────────────────────────────────────────┐
│         Telemetry Collector (Main Thread)               │
│         _collect_vm_metrics()                            │
│                                                          │
│  For each VM:                                           │
│    1. Read: state, CPU, memory, cputime                │
│    2. Compute: memory rate, angle                       │
│    3. Format: Line protocol                             │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ↓
        ┌──────────────────────┐
        │  Queue (in-memory)   │
        │  (Max: 20,000 lines) │
        └──────────┬───────────┘
                   │
                   ↓
┌─────────────────────────────────────────────────────────┐
│      InfluxDB Connector (Background Thread)             │
│                                                          │
│  Batches lines:                                         │
│    - Max 2,000 lines per batch                          │
│    - Max 1 second between flushes                       │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ↓
    ┌──────────────────────────────────┐
    │  InfluxDB3 HTTP API              │
    │  POST /api/v1/write              │
    │  (Batch write with line protocol)│
    └──────────────────────────────────┘
```

---

## Configuration Parameters

### Key Settings (`src/config/telemetry_config.py`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `poll_interval` | 5.0 sec | How often to collect metrics |
| `batch_max_lines` | 2,000 | Lines per batch to InfluxDB |
| `batch_max_sec` | 1.0 | Max time before flushing batch |
| `libvirt_uri` | `qemu:///system` | KVM connection URI |
| `libvirt_timeout` | 10 sec | KVM operation timeout |
| `influx_url` | `http://localhost:8086` | InfluxDB API endpoint |
| `influx_db` | `vmstats` | Database/bucket name |
| `max_queue` | 20,000 | Max in-memory queue size |

---

## Module Components

### 1. **TelemetryCollector** (`collector.py`)

**Responsibilities:**
- Orchestrates KVM monitoring
- Manages collection lifecycle (start/stop)
- Calculates derived metrics
- Formats line protocol
- Tracks collection statistics

**Key Methods:**
```python
start()                  # Start background collection
stop()                   # Stop gracefully
_collect_metrics()       # Main collection loop
_collect_vm_metrics()    # Per-VM collection
_line_protocol()         # Line protocol formatting
```

**Statistics Tracked:**
- `started_at` - When collection started
- `total_collections` - Number of collection cycles
- `total_errors` - Errors encountered
- `last_collection_time` - Last successful collection
- `vms_monitored` - Currently active VMs
- `total_metrics_written` - Total lines written

### 2. **KVMConnector** (`kvm_connector.py`)

**Responsibilities:**
- Connect to libvirt daemon
- Retrieve VM information
- Extract performance metrics
- Handle connection errors

**Key Methods:**
```python
connect()           # Connect to libvirt
disconnect()        # Close connection
get_live_vms()     # Get all running VMs
get_vm_metrics()   # Extract VM metrics
```

### 3. **InfluxConnector** (`influx_connector.py`)

**Responsibilities:**
- Queue metrics in batches
- Send to InfluxDB HTTP API
- Handle retries and failures
- Run as background thread

**Key Methods:**
```python
enqueue(line)           # Add line to queue
start_writing()         # Begin background thread
stop_writing()          # Stop gracefully
_write_batch()          # Batch write to InfluxDB
```

---

## Data Storage & Query Examples

### Query 1: Get Latest VM Metrics

```sql
SELECT * 
FROM vm_metrics 
WHERE time > now() - 1h 
ORDER BY time DESC 
LIMIT 100
```

### Query 2: Memory Trend Analysis

```sql
SELECT memory_rate_kb_per_sec, memory_angle_deg 
FROM vm_features 
WHERE time > now() - 24h 
  AND name = 'ubuntu-vm'
```

### Query 3: Average CPU Count

```sql
SELECT MEAN(cpu_count) 
FROM vm_metrics 
WHERE time > now() - 7d 
GROUP BY name
```

### Query 4: Memory Usage Over Time

```sql
SELECT memory_used_kb 
FROM vm_metrics 
WHERE VMID = '1' 
  AND time > now() - 12h
ORDER BY time DESC
```

---

## Performance Characteristics

### Data Generation Rate

**Example for 10 VMs:**
```
Per Collection Cycle (5 seconds):
  - vm_metrics lines: 10 (one per VM)
  - vm_features lines: 10 (one per VM, after first collection)
  - Total: ~20 lines per cycle

Per Hour:
  - Collections: 720 (3600 sec / 5 sec)
  - Lines: ~14,400
  - Approximate storage: ~500 KB - 1 MB (depending on compression)

Per Day:
  - Lines: ~345,600
  - Approximate storage: ~12 - 25 MB

Per Month (30 days):
  - Lines: ~10,368,000
  - Approximate storage: ~360 - 750 MB
```

### Batching Efficiency

```
Default Configuration:
  - Batch size: 2,000 lines
  - Batch timeout: 1 second
  - API calls per minute (10 VMs): ~18
  - Bandwidth per minute: ~50 KB
```

---

## Error Handling

### Graceful Degradation

1. **KVM Connection Failure**
   - Logs error
   - Increments error counter
   - Retries on next cycle
   - Service continues running

2. **InfluxDB Write Failure**
   - Keeps lines in queue
   - Retries with exponential backoff
   - Drops oldest if queue full
   - Logs warning

3. **Metric Collection Errors**
   - Per-VM error logging
   - Continues with other VMs
   - Increments error counter
   - Does not stop service

---

## Integration with Dashboard

### Telemetry API Endpoints

The collected data is accessed through:

```
GET /api/telemetry/vms              # List monitored VMs
GET /api/telemetry/stats/{vm_id}    # Get VM statistics
GET /api/telemetry/history          # Get historical data
```

### Data Flow to Frontend

```
InfluxDB3
    ↓
Telemetry API (influx_query.py - HTTP REST API)
    ↓
Routes (api/telemetry.py)
    ↓
Dashboard Pages (telemetry.html)
    ↓
JavaScript (dashboard.js)
    ↓
User Interface
```

---

## Monitoring the Telemetry Service

### Check Service Status

```python
from src.telemetry.collector import TelemetryCollector
from src.config.telemetry_config import TelemetryConfig

config = TelemetryConfig()
collector = TelemetryCollector(config)
collector.start()

# Get statistics
stats = collector.stats
print(f"Running: {collector._running}")
print(f"VMs monitored: {stats['vms_monitored']}")
print(f"Total collections: {stats['total_collections']}")
print(f"Total errors: {stats['total_errors']}")
print(f"Metrics written: {stats['total_metrics_written']}")
```

### Monitor InfluxDB

```bash
# Check database exists
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8086/api/v1/buckets

# Query recent data
curl -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT * FROM vm_metrics LIMIT 10"}' \
  http://localhost:8086/api/v1/query
```

---

## Troubleshooting

### No Data Appearing

**Checklist:**
- [ ] Telemetry service is running: `collector._running == True`
- [ ] KVM connection established: Check logs for connection errors
- [ ] InfluxDB is accessible: Test HTTP endpoint
- [ ] Database exists: Verify bucket name in config
- [ ] Authentication token is valid: Check INFLUX_TOKEN

### High Error Rate

**Common Causes:**
1. KVM daemon not running or unreachable
2. Insufficient permissions for libvirt access
3. InfluxDB authentication failures
4. Network connectivity issues
5. Queue size exceeded (20,000 lines)

**Solutions:**
```bash
# Restart libvirt daemon
sudo systemctl restart libvirtd

# Check permissions
groups $USER  # Should include 'libvirt'

# Monitor queue depth
# (Check collector.influx._queue.qsize() in code)

# Verify InfluxDB connectivity
curl -H "Authorization: Bearer $INFLUX_TOKEN" \
  http://localhost:8086/health
```

### Memory Growing

**Possible Causes:**
1. Queue not flushing (InfluxDB connection down)
2. Collection errors accumulating
3. Large number of VMs

**Solutions:**
1. Check InfluxDB connectivity
2. Monitor logs for errors
3. Increase `batch_max_lines` to flush sooner
4. Reduce `poll_interval` to collect less frequently

---

## Future Enhancements

### Planned Features

1. **Additional Measurements**
   - Disk I/O metrics
   - Network metrics
   - GPU metrics
   - Custom application metrics

2. **Performance Optimization**
   - Connection pooling
   - Metric filtering
   - Compression
   - Sampling policies

3. **Advanced Analytics**
   - Anomaly detection
   - Trend forecasting
   - Auto-scaling recommendations
   - Performance bottleneck identification

4. **High Availability**
   - Multi-node collection
   - Failover support
   - Load balancing
   - Distributed collection

---

## Summary

**Measurements Created:**
1. ✅ `vm_metrics` - Basic VM state and resources
2. ✅ `vm_features` - Derived features and trends

**Data Points per Measurement:**
- `vm_metrics`: 5 fields + 3 tags
- `vm_features`: 2 fields + 3 tags

**Collection Frequency:** Every 5 seconds

**Storage Efficiency:** ~1-2 MB per day per 10 VMs

**Status:** ✅ Production Ready

---

**Documentation Version:** 1.0  
**Last Updated:** November 13, 2025  
**Module Version:** 2.0
