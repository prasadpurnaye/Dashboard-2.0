# Resource Monitoring Page - API Integration Guide

## Endpoint Requirements

### 1. VM List Endpoint: `GET /api/telemetry/live-vms`

**Purpose**: Populate VM selection dropdown

**Expected Response Format**:
```json
{
  "count": 3,
  "source": "libvirt",
  "vms": [
    {
      "id": 1,
      "name": "vm-name",
      "uuid": "uuid-string",
      "state": "running",
      "cpu_count": 4,
      "memory_max": 8388608,
      "memory_used": 8388608,
      "cputime": 1234567890
    }
  ]
}
```

**Frontend Usage** (in `loadVMs()`):
```javascript
const response = await fetch('/api/telemetry/live-vms');
const data = await response.json();
state.vms = data.vms;
```

---

### 2. VM Stats Endpoint: `GET /api/telemetry/vm-stats/{vm_id}`

**Purpose**: Get current metrics for a specific VM (called every 5 seconds)

**Expected Response Format**:
```json
{
  "vm_id": "1",
  "timestamp": 1699564800,
  "metrics": {
    "state": "running",
    "cpus": 4,
    "cputime": 1234567890,
    "timeusr": 1000000000,
    "timesys": 500000000,
    "memactual": 4194304,
    "memrss": 3145728,
    "memavailable": 1048576,
    "memusable": 2097152,
    "memswap_in": 0,
    "memswap_out": 0,
    "memmajor_fault": 10,
    "memminor_fault": 5000,
    "memdisk_cache": 512000,
    "net_rxbytes": 5242880,
    "net_rxpackets": 1000,
    "net_rxerrors": 0,
    "net_rxdrops": 0,
    "net_txbytes": 2097152,
    "net_txpackets": 500,
    "net_txerrors": 0,
    "net_txdrops": 0,
    "disk_rd_req": 1000,
    "disk_rd_bytes": 10485760,
    "disk_wr_reqs": 500,
    "disk_wr_bytes": 5242880,
    "disk_errors": 0
  }
}
```

**Frontend Usage** (in `fetchVMTelemetry()`):
```javascript
const response = await fetch(`/api/telemetry/vm-stats/${state.selectedVmId}`);
const data = await response.json();
const metrics = data.metrics;
```

---

## Metric Field Reference

### CPU & Memory Metrics

| Field | Type | Unit | Description |
|-------|------|------|-------------|
| `timeusr` | number | nanoseconds | CPU time spent in user mode |
| `timesys` | number | nanoseconds | CPU time spent in system/kernel mode |
| `memactual` | number | KB | Physical memory currently used by VM |
| `memrss` | number | KB | Resident set size (memory in RAM) |
| `memavailable` | number | KB | Memory available for allocation |
| `memusable` | number | KB | Memory actually usable by VM |
| `memswap_in` | number | pages | Pages swapped from disk to RAM |
| `memswap_out` | number | pages | Pages swapped from RAM to disk |
| `memmajor_fault` | number | count | Major page faults (required disk read) |
| `memminor_fault` | number | count | Minor page faults (in-memory) |
| `memdisk_cache` | number | KB | Disk cache used by VM |

### Network Metrics

| Field | Type | Unit | Description |
|-------|------|------|-------------|
| `net_rxbytes` | number | bytes | Total bytes received on all interfaces |
| `net_rxpackets` | number | packets | Total packets received on all interfaces |
| `net_rxerrors` | number | count | RX errors on all interfaces |
| `net_rxdrops` | number | count | RX dropped packets on all interfaces |
| `net_txbytes` | number | bytes | Total bytes transmitted on all interfaces |
| `net_txpackets` | number | packets | Total packets transmitted on all interfaces |
| `net_txerrors` | number | count | TX errors on all interfaces |
| `net_txdrops` | number | count | TX dropped packets on all interfaces |

### Disk Metrics

| Field | Type | Unit | Description |
|-------|------|------|-------------|
| `disk_rd_req` | number | requests | Total disk read requests |
| `disk_rd_bytes` | number | bytes | Total bytes read from disk |
| `disk_wr_reqs` | number | requests | Total disk write requests |
| `disk_wr_bytes` | number | bytes | Total bytes written to disk |
| `disk_errors` | number | count | Total disk I/O errors |

---

## Data Type & Format Requirements

### Numbers
- **CPU Times**: Should be in nanoseconds (for accurate rate calculations)
- **Memory**: Should be in KB
- **Network**: Bytes and packets should be totals
- **Disk**: Requests are counts, bytes are totals

### Compatibility Notes

The frontend handles these field transformations:
- **Bytes → Human Readable**: Uses `formatBytes()` function
  - KB, MB, GB, TB conversion
- **Nanoseconds → Seconds**: Divides by 1e9
- **Rates**: Calculates difference / time delta using arctangent formula

### Missing Fields

If a metric field is missing from the response:
```javascript
// Frontend will display as "N/A" with warning in console
const value = metrics[key] ?? 'N/A';
```

---

## Implementation Checklist

### Backend Requirements

- [ ] `/api/telemetry/live-vms` returns list of running VMs
- [ ] `/api/telemetry/vm-stats/{vm_id}` returns metrics object
- [ ] All 26 metric fields are populated (or gracefully missing)
- [ ] Timestamps are accurate
- [ ] Data types are correct (numbers for all metrics)
- [ ] Endpoint responds in < 200ms
- [ ] Error handling returns appropriate HTTP status codes

### Frontend Integration

- [ ] VM dropdown populates from `/api/telemetry/live-vms`
- [ ] Metrics display on VM selection
- [ ] Graphs update every 5 seconds via polling
- [ ] Values format correctly with units
- [ ] Errors display in UI without crashing

### Testing Steps

1. **VM List Test**
   ```bash
   curl http://localhost:8000/api/telemetry/live-vms
   ```
   Expected: JSON array of VMs

2. **Metrics Test**
   ```bash
   curl http://localhost:8000/api/telemetry/vm-stats/1
   ```
   Expected: JSON object with metrics

3. **Frontend Test**
   - Open: http://localhost:8000/resource-monitoring
   - Select VM from dropdown
   - Verify metrics display
   - Check console for errors (F12)

---

## Error Handling

### Common Frontend Errors

**"Error loading VMs"**
- Check if `/api/telemetry/live-vms` is working
- Verify CORS headers are set correctly
- Check application logs

**"Error fetching telemetry"**
- Verify selected VM ID is valid
- Check if `/api/telemetry/vm-stats/{vm_id}` returns data
- Review network tab in DevTools

**"No metrics data"**
- Endpoint may be returning empty metrics object
- Verify all 26 metric fields are populated
- Check if InfluxDB has data for this VM

---

## Performance Considerations

### Response Time SLAs

- **VM List**: < 100ms (called once at page load)
- **VM Stats**: < 200ms (called every 5 seconds)

### Data Volume

- **VM List**: ~1-2 KB per response
- **VM Stats**: ~2-3 KB per response
- **Total per poll**: ~3 KB (repeated every 5 seconds)

### Bandwidth Estimation

For 10 concurrent users:
- Base load: ~24 KB/s from metrics polling alone
- Peak: Much higher during page loads

### Optimization Tips

1. **Cache VM list**: Only refresh on page load or when manually requested
2. **Batch requests**: Could combine VM list + metrics if many VMs
3. **Delta updates**: Only return changed metrics
4. **Compression**: Enable gzip for HTTP responses

---

## Integration Examples

### Example Backend Response (Python FastAPI)

```python
@app.get("/api/telemetry/vm-stats/{vm_id}")
async def get_vm_stats(vm_id: int):
    # Query InfluxDB for latest metrics
    metrics = {
        "state": "running",
        "cpus": 4,
        "cputime": 1234567890,
        "timeusr": 1000000000,
        "timesys": 500000000,
        "memactual": 4194304,
        "memrss": 3145728,
        "memavailable": 1048576,
        "memusable": 2097152,
        "memswap_in": 0,
        "memswap_out": 0,
        "memmajor_fault": 10,
        "memminor_fault": 5000,
        "memdisk_cache": 512000,
        "net_rxbytes": 5242880,
        "net_rxpackets": 1000,
        "net_rxerrors": 0,
        "net_rxdrops": 0,
        "net_txbytes": 2097152,
        "net_txpackets": 500,
        "net_txerrors": 0,
        "net_txdrops": 0,
        "disk_rd_req": 1000,
        "disk_rd_bytes": 10485760,
        "disk_wr_reqs": 500,
        "disk_wr_bytes": 5242880,
        "disk_errors": 0,
    }
    
    return {
        "vm_id": str(vm_id),
        "timestamp": int(time.time()),
        "metrics": metrics
    }
```

### Example Frontend Usage (JavaScript)

```javascript
async function fetchVMTelemetry() {
    try {
        const response = await fetch(`/api/telemetry/vm-stats/${state.selectedVmId}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const data = await response.json();
        const metrics = data.metrics;
        
        // Update UI with metrics
        updateMetrics(metrics);
        updateGraphs(metrics);
        
    } catch (error) {
        console.error('Error fetching telemetry:', error);
        showError('Failed to fetch metrics');
    }
}
```

---

## Validation & Testing

### Endpoint Validation

```bash
# Test endpoint accessibility
curl -i http://localhost:8000/api/telemetry/vm-stats/1

# Test response format
curl http://localhost:8000/api/telemetry/vm-stats/1 | jq .

# Check response headers
curl -I http://localhost:8000/api/telemetry/vm-stats/1
```

### Frontend Console Tests

```javascript
// In browser console (F12 → Console tab)

// Test VM loading
fetch('/api/telemetry/live-vms').then(r => r.json()).then(d => console.log(d))

// Test metrics endpoint
fetch('/api/telemetry/vm-stats/1').then(r => r.json()).then(d => console.log(d))
```

---

## Deployment Notes

### Production Checklist

- [ ] Endpoints return only required fields (no internal data)
- [ ] Error responses have appropriate HTTP status codes
- [ ] Response times meet SLA requirements
- [ ] CORS headers correctly configured
- [ ] Rate limiting implemented if needed
- [ ] Database queries are optimized
- [ ] Caching strategy is in place

### Security Considerations

- [ ] Only authenticated users can access endpoints
- [ ] Input validation on vm_id parameter
- [ ] No sensitive data in metric fields
- [ ] HTTPS enforced in production
- [ ] Query injection prevention (parameterized queries)

---

## Changelog

### v1.0 (Current)
- Initial implementation with 26 metrics
- 5-second polling interval
- VM selection dropdown
- 4 metric categories

### Future Versions
- Per-device metrics
- Historical data export
- Custom metric selection
- Threshold-based alerting
