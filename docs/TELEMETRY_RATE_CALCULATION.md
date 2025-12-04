# VM Telemetry with Rate-of-Change Calculation

## Overview

The VM Dashboard now displays real-time telemetry data with calculated rates of change for all metrics. Instead of using random demo values, the frontend fetches actual metrics from the backend InfluxDB database.

## Architecture

### Frontend (vm-dashboard.js)

The frontend implements a real-time telemetry polling system:

1. **VM Card Creation** (`createVMCards()`)
   - Fetches live VMs from `/api/telemetry/live-vms`
   - Creates gauge charts for CPU, Memory, and Disk
   - Adds network metric display areas
   - Adds rate-of-change display elements

2. **Telemetry Fetching** (`fetchVmTelemetry()`)
   - Calls `/api/telemetry/vm-telemetry` endpoint
   - Returns metrics and rate values for all VMs
   - Error handling with automatic retry on next cycle

3. **Card Updates** (`updateVMCardFromTelemetry()`)
   - Updates gauge values with real metrics
   - Displays rate-of-change values below each gauge
   - Formats network data (RX/TX bytes with rates)

4. **Periodic Refresh** (`startVMTelemetryUpdates()`)
   - Default: Updates every 1 second
   - Can be customized via parameter
   - Auto-stops on page unload

### Backend (telemetry.py)

New endpoint: `GET /api/telemetry/vm-telemetry`

**Response Format:**
```json
{
  "count": 4,
  "timestamp": "2025-12-04T10:30:45.123456",
  "vms": [
    {
      "id": 10,
      "name": "one-71",
      "uuid": "546d32c1-133b-4cff-ad56-3ee253e44adb",
      "state": "running",
      "cpu_count": 1,
      "memory_max": 8388608,
      "memory_used": 8388608,
      "cputime": 1906240000000,
      "cpu_usage_percent": 45.2,
      "memory_usage_percent": 23.5,
      "disk_read_bytes": 1024000,
      "disk_write_bytes": 512000,
      "network_rx_bytes": 1048576,
      "network_tx_bytes": 524288,
      "cpu_rate": 12.5,
      "memory_rate": -3.2,
      "disk_read_rate": 8.7,
      "disk_write_rate": -5.1,
      "network_rx_rate": 15.3,
      "network_tx_rate": 9.8
    }
  ]
}
```

### Database (influx_query.py)

New method: `get_vm_telemetry_with_rates(vm_id, minutes=5)`

**Features:**
- Queries current and previous data points from InfluxDB
- Calculates rates using arctan formula
- Handles missing data gracefully
- Formats results for frontend consumption

## Rate Calculation Formula

The rate of change uses the arctangent (inverse tangent) approach:

$$\text{rate} = \arctan\left(\frac{\text{newValue} - \text{oldValue}}{\Delta t}\right) \times \frac{180}{\pi}$$

Where:
- **newValue**: Current metric value at time $t$
- **oldValue**: Previous metric value at time $t_1$
- **$\Delta t$**: Time delta (typically 1 second)
- **Result**: Rate in degrees (0-90° range for most cases)

### Interpretation

- **0°**: No change
- **45°**: Linear growth/decline
- **~90°**: Rapid change
- **Negative values**: Decline

## Metrics Collected

### CPU
- **cpu_usage_percent**: Percentage of CPU used (0-100%)
- **cpu_rate**: Rate of CPU usage change (degrees)
- **Source**: cputime in nanoseconds converted to percentage

### Memory
- **memory_usage_percent**: Percentage of memory used (0-100%)
- **memory_rate**: Rate of memory change (degrees)
- **Source**: vm_totals measurement in InfluxDB

### Disk
- **disk_read_bytes**: Total disk read bytes
- **disk_write_bytes**: Total disk write bytes
- **disk_read_rate**: Rate of disk read changes (degrees)
- **disk_write_rate**: Rate of disk write changes (degrees)
- **Source**: Aggregated from vm_devices measurements

### Network
- **network_rx_bytes**: Total received bytes
- **network_tx_bytes**: Total transmitted bytes
- **network_rx_rate**: Rate of RX change (degrees)
- **network_tx_rate**: Rate of TX change (degrees)
- **Source**: Aggregated from vm_devices measurements (per-NIC)

## Data Flow

```
┌─────────────────┐
│   libvirt       │
│  (KVM Host)     │
└────────┬────────┘
         │ (via KVMConnector)
         ↓
┌─────────────────┐
│  TelemetryCollector
│  (Collects every 10s)
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  InfluxDB       │
│  (vm_totals,    │
│   vm_devices)   │
└────────┬────────┘
         │ (queries for current + previous)
         ↓
┌─────────────────┐
│  InfluxQuery    │
│  (Rate calc)    │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  API Endpoint   │
│  /vm-telemetry  │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  Browser        │
│  (Updates UI    │
│   every 1s)     │
└─────────────────┘
```

## Frontend Functions Reference

### Core Functions

#### `fetchVmTelemetry()`
- **Purpose**: Fetch real telemetry data from backend
- **Returns**: Promise with telemetry object
- **Endpoint**: `/api/telemetry/vm-telemetry`
- **Error Handling**: Returns `{ count: 0, vms: [], error: true }` on failure

#### `updateVMCardFromTelemetry(vmId, vmData)`
- **Purpose**: Update a single VM card with telemetry data
- **Params**:
  - `vmId`: VM identifier (id or uuid)
  - `vmData`: Telemetry data object
- **Updates**: Gauges, rates, network metrics

#### `updateAllVMGaugesFromTelemetry(telemetryData)`
- **Purpose**: Batch update all VM cards
- **Params**: `telemetryData` from `fetchVmTelemetry()`

#### `refreshVmTelemetry()`
- **Purpose**: Execute one telemetry refresh cycle
- **Calls**: `fetchVmTelemetry()` + `updateAllVMGaugesFromTelemetry()`
- **Error Handling**: Logs errors, continues on next cycle

#### `startVMTelemetryUpdates(intervalMs = 1000)`
- **Purpose**: Start periodic telemetry polling
- **Params**: `intervalMs` - refresh interval (default 1000ms)

#### `stopVMTelemetryUpdates()`
- **Purpose**: Stop periodic telemetry polling
- **Called Automatically**: On page unload

### Utility Functions

#### `updateVMGaugeChart(vmId, metricType, newValue)`
- Updates Chart.js gauge with new value
- Updates display element with formatted value

#### `updateGauge(elementId, value, unit = '%')`
- Generic gauge element updater

#### `formatBytes(bytes)`
- Converts bytes to human-readable format (B, KB, MB, GB)

#### `formatRate(rate)`
- Formats rate value with degree symbol
- Handles NaN/Infinity values

## Configuration

### Polling Interval

Default: 1000ms (1 second)

To change:
```javascript
startVMTelemetryUpdates(500);  // Update every 500ms
startVMTelemetryUpdates(2000); // Update every 2 seconds
```

### Rate Calculation Window

Default: 5 minutes (backend)

To change, modify `InfluxQuery.get_vm_telemetry_with_rates()`:
```python
telemetry = influx_query.get_vm_telemetry_with_rates(vm_id, minutes=10)  # 10 minute window
```

## Performance Considerations

1. **Polling Frequency**: 1 second is reasonable for most use cases
   - Lower values (100-500ms) increase server load
   - Higher values (5000ms+) reduce responsiveness

2. **Data Retention**: InfluxDB should retain data for at least 5 minutes
   - Longer retention improves rate accuracy over time

3. **Query Optimization**: The backend queries vm_totals measurement
   - Pre-aggregated data reduces query time
   - Device-level queries would be significantly slower

## Error Handling

### Frontend

- **Network errors**: Logged, retry on next cycle
- **Missing telemetry**: Displays "Rate: 0.0°"
- **Invalid values**: Clamped to 0-100 range for gauges

### Backend

- **Uninitialized collector**: Returns 500 error
- **InfluxDB query failure**: Returns default/zero values
- **Missing previous data**: Skips rate calculation (returns 0)

## Troubleshooting

### Telemetry Not Updating

1. Check browser console for errors
2. Verify `/api/telemetry/vm-telemetry` endpoint is working
3. Verify InfluxDB has data (check `/api/telemetry/diagnostic`)
4. Check network tab in DevTools (should see requests every 1s)

### Rates Always Zero

1. Wait 5+ minutes for sufficient data history
2. Check InfluxDB retention policy
3. Verify collector is running and writing data

### High Server Load

1. Reduce polling frequency
2. Reduce number of VMs being monitored
3. Check InfluxDB query performance

## Future Enhancements

1. **Configurable polling interval** via UI
2. **Rate calculation smoothing** (moving average)
3. **Historical rate trends** (rate of rate change)
4. **Per-VM rate thresholds** (alerts)
5. **Export telemetry data** (CSV/JSON)

## Testing

### Manual API Test

```bash
# Test telemetry endpoint
curl http://localhost:8000/api/telemetry/vm-telemetry | jq

# Test live VMs endpoint
curl http://localhost:8000/api/telemetry/live-vms | jq

# Test status
curl http://localhost:8000/api/telemetry/status | jq
```

### Frontend Console

```javascript
// Manually trigger telemetry fetch
await fetchVmTelemetry()

// Manually trigger refresh
await refreshVmTelemetry()

// Check gauge state
console.log(vmGaugeCharts)

// Check live VMs
console.log(liveVMs)
```

## Code Examples

### Customizing Refresh Interval

```javascript
// Change refresh to 2 seconds
stopVMTelemetryUpdates();
startVMTelemetryUpdates(2000);

// Change refresh to 500ms
stopVMTelemetryUpdates();
startVMTelemetryUpdates(500);
```

### Accessing Current Metrics

```javascript
// After telemetry refresh, metrics are in HTML elements
const cpuElement = document.getElementById('vm-value-10-cpu');
console.log(cpuElement.innerText); // "45.2%"

const rateElement = document.getElementById('vm-rate-10-cpu');
console.log(rateElement.innerText); // "Rate: 12.5°"
```

### Adding Custom Metric Display

```javascript
// In updateVMCardFromTelemetry()
const customElement = document.getElementById(`vm-custom-${vmId}`);
if (customElement) {
    customElement.innerText = `Custom: ${vmData.custom_metric}`;
}
```
