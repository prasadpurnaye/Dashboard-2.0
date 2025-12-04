# Main Gauges Page Refactor - Complete Documentation

## Overview

The Main Gauges page has been completely refactored to display **rate-of-change based gauges** for VM resource metrics. Instead of showing random values, the page now:

1. ✅ Displays a **VM dropdown selector** to choose which VM to monitor
2. ✅ Fetches **real telemetry data** from the backend API
3. ✅ Calculates **rate-of-change angles** for 8 critical metrics
4. ✅ Updates gauges every **2 seconds** with live data
5. ✅ Tracks **previous values** to compute accurate rates

---

## Architecture Overview

### Frontend Components

```
Main Gauges Page (index.html)
├── VM Selector Dropdown (select from live VMs)
├── 8 Gauge Components (rate-of-change display)
│   ├── Network RX Rate
│   ├── Network TX Rate
│   ├── Disk Read Rate
│   ├── Disk Write Rate
│   ├── CPU User Time Rate
│   ├── CPU System Time Rate
│   ├── Memory RSS Rate
│   └── Disk Read Requests Rate
└── Gauge Info Panel (formula explanation)
```

### Backend Integration

```
Frontend Dashboard
    ↓
1. Fetch available VMs
    → GET /api/telemetry/live-vms
    ← Returns list of running VMs
    
2. Fetch telemetry for selected VM
    → GET /api/telemetry/vm-stats/{vm_id}
    ← Returns 26+ metrics from InfluxDB
    
3. Compute rate-of-change angles
    → Compare current vs previous value
    → Calculate: atan((newValue - oldValue) / timeDelta) * 180 / π
    
4. Update gauges every 2 seconds
```

---

## Rate-of-Change Calculation

### Formula

```
rate = atan((newValue - oldValue) / timeDelta_seconds) * 180 / π
```

Where:
- **newValue** = Current metric value
- **oldValue** = Previous metric value from last update
- **timeDelta_seconds** = Time elapsed since last update (in seconds)
- **atan** = Arctangent function (inverse tangent)
- **180 / π** = Conversion from radians to degrees

### Implementation

```javascript
function calculateRateOfChange(newValue, oldValue, timeDeltaMs) {
    // If no previous value or no time delta, return neutral angle
    if (oldValue === undefined || timeDeltaMs === 0) {
        return 0;
    }
    
    // Convert time delta to seconds
    const timeDeltaSeconds = timeDeltaMs / 1000;
    
    // Calculate rate: (change in value) / (time in seconds)
    const valueDelta = newValue - oldValue;
    const rate = valueDelta / timeDeltaSeconds;
    
    // Apply arctangent formula to convert to degrees (0-90 range)
    const rateInRadians = Math.atan(rate);
    const rateInDegrees = rateInRadians * 180 / Math.PI;
    
    // Clamp to 0-90 range
    const clampedDegrees = Math.max(0, Math.min(90, rateInDegrees));
    
    return clampedDegrees;
}
```

### Example Scenarios

**Scenario 1: Network increasing rapidly**
- Previous RX bytes: 1,000,000
- Current RX bytes: 2,000,000
- Time delta: 2 seconds
- Rate: (2,000,000 - 1,000,000) / 2 = 500,000 bytes/s
- Angle: atan(500,000) * 180 / π ≈ **89.99°** (maximum activity)

**Scenario 2: Network stable**
- Previous RX bytes: 1,000,000
- Current RX bytes: 1,000,050
- Time delta: 2 seconds
- Rate: (1,000,050 - 1,000,000) / 2 = 25 bytes/s
- Angle: atan(25) * 180 / π ≈ **1.43°** (minimal activity)

**Scenario 3: First update (no previous value)**
- Angle: **0°** (neutral/default)

---

## Metrics Monitored

| Gauge # | Metric | Field Name | Source | Unit |
|---------|--------|------------|--------|------|
| 1 | Network RX Rate | `net_rxbytes` | InfluxDB | bytes/s |
| 2 | Network TX Rate | `net_txbytes` | InfluxDB | bytes/s |
| 3 | Disk Read Rate | `disk_rd_bytes` | InfluxDB | bytes/s |
| 4 | Disk Write Rate | `disk_wr_bytes` | InfluxDB | bytes/s |
| 5 | CPU User Time Rate | `timeusr` | InfluxDB | ns/s |
| 6 | CPU System Time Rate | `timesys` | InfluxDB | ns/s |
| 7 | Memory RSS Rate | `memrss` | InfluxDB | bytes/s |
| 8 | Disk Read Requests Rate | `disk_rd_req` | InfluxDB | reqs/s |

All metrics are fetched from the backend API, which queries InfluxDB for real telemetry data.

---

## Code Implementation

### 1. HTML Structure (`templates/index.html`)

```html
<!-- VM Selection Dropdown -->
<div class="vm-selector-container">
    <label for="vm-dropdown">Select VM:</label>
    <select id="vm-dropdown">
        <option value="">-- Loading VMs --</option>
    </select>
    <span id="loading-indicator" class="loading-indicator" style="display: none;">⟳ Updating...</span>
</div>

<!-- Gauges Container (8 gauges) -->
<div class="gauges-container">
    <div class="gauge-wrapper" id="gauge-wrapper-1">
        <div class="gauge-title">Network RX Rate</div>
        <div class="gauge-subtitle">Rate of change (bytes/s)</div>
        <div class="gauge-container">
            <canvas id="gauge-1"></canvas>
        </div>
        <div class="gauge-value-display" id="gauge-value-1">0.00° (rate)</div>
    </div>
    <!-- ... more gauges ... -->
</div>

<!-- Gauge Info Panel -->
<div class="gauge-info-panel">
    <h3>About These Gauges</h3>
    <p>Each gauge displays the <strong>rate of change</strong> (in degrees 0-90°) for VM resource metrics...</p>
</div>
```

### 2. Gauge Configuration (`dashboard.js`)

```javascript
const GAUGE_CONFIG = {
    1: {
        title: 'Network RX Rate',
        field: 'net_rxbytes',
        type: 'rate-of-change',
        unit: 'bytes/s'
    },
    2: {
        title: 'Network TX Rate',
        field: 'net_txbytes',
        type: 'rate-of-change',
        unit: 'bytes/s'
    },
    // ... 6 more gauges ...
};
```

### 3. State Management (`dashboard.js`)

```javascript
const STATE = {
    gaugeCharts: {},                    // Chart.js instances
    currentVmId: null,                  // Selected VM ID
    previousValues: {},                 // Previous metric values per VM
    lastUpdateTime: {},                 // Last update timestamp per VM
    updateInterval: null,               // Update interval ID
    vms: []                             // Available VMs list
};
```

### 4. Key Functions

#### Initialize Previous Values
```javascript
function initializePreviousValues(vmId) {
    if (!STATE.previousValues[vmId]) {
        STATE.previousValues[vmId] = {};
        STATE.lastUpdateTime[vmId] = Date.now();
    }
}
```

#### Store Previous Values for Next Update
```javascript
function storePreviousValues(vmId, metrics) {
    const gaugeIds = Object.keys(GAUGE_CONFIG);
    
    gaugeIds.forEach(gaugeId => {
        const field = GAUGE_CONFIG[gaugeId].field;
        if (metrics[field] !== undefined) {
            STATE.previousValues[vmId][field] = metrics[field];
        }
    });
    
    STATE.lastUpdateTime[vmId] = Date.now();
}
```

#### Fetch and Update Gauges
```javascript
async function fetchAndUpdateGauges() {
    if (!STATE.currentVmId) {
        console.debug('No VM selected');
        return;
    }
    
    try {
        // Fetch telemetry for selected VM
        const response = await fetch(`/api/telemetry/vm-stats/${STATE.currentVmId}`);
        const data = await response.json();
        const metrics = data.metrics;
        
        // Update each gauge with rate-of-change angle
        Object.keys(GAUGE_CONFIG).forEach(gaugeId => {
            const config = GAUGE_CONFIG[gaugeId];
            const field = config.field;
            const currentValue = metrics[field];
            
            // Get previous value and calculate rate
            const previousValue = STATE.previousValues[STATE.currentVmId][field];
            const previousTime = STATE.lastUpdateTime[STATE.currentVmId];
            const currentTime = Date.now();
            const timeDelta = currentTime - previousTime;
            
            // Calculate rate-of-change angle
            const angleInDegrees = calculateRateOfChange(currentValue, previousValue, timeDelta);
            
            // Update the gauge
            updateGaugeChart(gaugeId, angleInDegrees);
        });
        
        // Store current values as previous for next update
        storePreviousValues(STATE.currentVmId, metrics);
        
    } catch (error) {
        console.error('Error fetching/updating gauges:', error);
    }
}
```

#### Fetch Available VMs
```javascript
async function fetchAvailableVms() {
    try {
        const response = await fetch('/api/telemetry/live-vms');
        const data = await response.json();
        STATE.vms = data.vms || [];
        
        updateVmDropdown();
        console.log(`✓ Loaded ${STATE.vms.length} VMs`);
    } catch (error) {
        console.error('Error fetching VMs:', error);
    }
}
```

#### Handle VM Selection
```javascript
function selectVm(vmId) {
    if (!vmId) return;
    
    console.log(`✓ Selected VM: ${vmId}`);
    STATE.currentVmId = vmId;
    
    // Initialize previous values for this VM
    initializePreviousValues(vmId);
    
    // Fetch initial telemetry
    fetchAndUpdateGauges();
}
```

### 5. Initialization

```javascript
function initializeGauges() {
    console.log('Initializing Main Gauges Dashboard...');
    
    // Create gauge charts
    for (let i = 1; i <= 8; i++) {
        createGaugeChart(i, 0);
    }
    
    // Set up VM dropdown listener
    const dropdown = document.getElementById('vm-dropdown');
    if (dropdown) {
        dropdown.addEventListener('change', (e) => {
            selectVm(e.target.value);
        });
    }
    
    // Fetch available VMs
    fetchAvailableVms();
    
    // Set up periodic updates (every 2 seconds)
    STATE.updateInterval = setInterval(() => {
        fetchAndUpdateGauges();
    }, 2000);
    
    console.log('✓ Main Gauges Dashboard initialized');
}

document.addEventListener('DOMContentLoaded', initializeGauges);
```

---

## CSS Styling (`static/css/style.css`)

### VM Selector
```css
.vm-selector-container {
    background: #fff;
    border-radius: 10px;
    padding: 20px;
    margin-bottom: 30px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    display: flex;
    align-items: center;
    gap: 15px;
    flex-wrap: wrap;
}

.vm-selector-container select {
    padding: 12px 15px;
    border: 2px solid #e0e0e0;
    border-radius: 6px;
    font-size: 1em;
    background: #fff;
    color: #333;
    cursor: pointer;
    min-width: 250px;
    transition: all 0.3s ease;
}

.vm-selector-container select:focus {
    outline: none;
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}
```

### Gauge Titles with Subtitles
```css
.gauge-title {
    font-size: 1.3em;
    font-weight: 600;
    color: #333;
    margin-bottom: 5px;
    text-align: center;
}

.gauge-subtitle {
    font-size: 0.85em;
    color: #999;
    margin-bottom: 15px;
    text-align: center;
    font-style: italic;
}
```

### Gauge Info Panel
```css
.gauge-info-panel {
    background: linear-gradient(135deg, #f9fafb 0%, #f3f4f6 100%);
    border-radius: 10px;
    padding: 25px;
    margin-top: 40px;
    border: 1px solid #e5e7eb;
}

.gauge-info-panel h3 {
    color: #333;
    font-size: 1.2em;
    margin-bottom: 15px;
}

.gauge-info-panel p {
    color: #666;
    line-height: 1.6;
    margin-bottom: 12px;
}

.gauge-info-panel code {
    background: #fff;
    border: 1px solid #e0e0e0;
    padding: 2px 6px;
    border-radius: 4px;
    font-family: 'Courier New', monospace;
    color: #d63384;
    font-size: 0.9em;
}
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ User selects VM from dropdown                               │
│ → selectVm(vmId)                                             │
└──────────────────┬──────────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────────────┐
│ Initialize previous values storage for this VM               │
│ → initializePreviousValues(vmId)                             │
└──────────────────┬──────────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────────────┐
│ Fetch telemetry from backend                                │
│ → GET /api/telemetry/vm-stats/{vmId}                        │
│ ← Returns 26+ metrics (net_rxbytes, disk_rd_bytes, etc.)    │
└──────────────────┬──────────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────────────┐
│ For each gauge:                                             │
│  1. Get current metric value from response                  │
│  2. Get previous metric value from STATE                    │
│  3. Calculate time delta since last update                  │
│  4. Compute rate-of-change angle                            │
│     angle = atan((current - previous) / timeDelta) * 180/π  │
│  5. Update gauge with angle                                 │
└──────────────────┬──────────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────────────┐
│ Store current values as previous for next update             │
│ → storePreviousValues(vmId, metrics)                         │
└──────────────────┬──────────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────────────┐
│ Set interval to repeat every 2 seconds                      │
│ → setInterval(fetchAndUpdateGauges, 2000)                   │
└─────────────────────────────────────────────────────────────┘
```

---

## Testing & Verification

### Step 1: Verify VM Dropdown
1. Open `http://localhost:8000/`
2. Check that VM dropdown shows available VMs
3. Verify first VM is auto-selected

### Step 2: Verify API Response
```bash
curl http://localhost:8000/api/telemetry/vm-stats/1 | python3 -m json.tool
```
Should return metrics with fields like:
- `net_rxbytes` (network receive)
- `net_txbytes` (network transmit)
- `disk_rd_bytes` (disk read)
- `disk_wr_bytes` (disk write)
- `timeusr` (CPU user time)
- `timesys` (CPU system time)
- `memrss` (memory RSS)
- `disk_rd_req` (disk read requests)

### Step 3: Monitor Console Logs
1. Open browser DevTools (F12)
2. Check Console tab
3. Watch for:
   - `✓ Loaded X VMs`
   - `✓ Selected VM: 1`
   - `✓ Fetched metrics for VM 1`
   - Rate calculations printed for each gauge
   - Updates every 2 seconds

### Step 4: Verify Gauge Updates
1. Select a VM from dropdown
2. Watch gauges for ~10 seconds
3. Verify angles are between 0-90°
4. Verify angles change as metrics change
5. Verify loading indicator appears during updates

---

## Browser Compatibility

| Browser | Compatibility | Notes |
|---------|----------------|-------|
| Chrome 90+ | ✅ Full support | Async/await, fetch, Chart.js all supported |
| Firefox 88+ | ✅ Full support | Same as Chrome |
| Safari 14+ | ✅ Full support | Same as Chrome |
| Edge 90+ | ✅ Full support | Same as Chrome |

---

## Performance Considerations

- **Update Interval**: 2 seconds (configurable via `setInterval`)
- **Gauge Rendering**: Chart.js updates only changed canvas elements
- **Memory Usage**: Stores one previous value per metric per VM (minimal)
- **Network**: One API call every 2 seconds per selected VM
- **CPU**: Lightweight calculations (arithmetic only, no heavy computations)

---

## Future Enhancements

1. **Multi-Metric Aggregation**: Show average/median rate across time windows
2. **Gauge Styling**: Color-code gauges based on activity level
3. **Historical Trends**: Graph rate-of-change over time
4. **Threshold Alerts**: Alert when rate exceeds thresholds
5. **Configurable Metrics**: Let users select which metrics to monitor
6. **Export Data**: Download gauge data as CSV/JSON
7. **Comparison View**: Compare rates across multiple VMs side-by-side

---

## Troubleshooting

### Gauges Not Updating
- Check browser console for errors
- Verify `/api/telemetry/live-vms` returns VMs
- Verify `/api/telemetry/vm-stats/{vm_id}` returns metrics
- Check network tab for failed requests
- Ensure INFLUX_TOKEN environment variable is set

### No VMs in Dropdown
- Check if KVM host is accessible
- Verify libvirt connection is working
- Check backend logs for connection errors
- Try: `curl http://localhost:8000/api/telemetry/live-vms`

### Incorrect Angle Calculations
- Enable console logging to see debug messages
- Verify metric values are changing between updates
- Check time delta calculation (should be ~2000ms)
- Verify arctangent formula is correct

---

## Files Modified

1. **`templates/index.html`** - Updated HTML structure
2. **`static/js/dashboard.js`** - Complete JavaScript rewrite
3. **`static/css/style.css`** - Added VM selector and gauge info panel styles

---

## API Endpoints Used

### GET /api/telemetry/live-vms
Returns list of currently running VMs.

**Response:**
```json
{
    "count": 2,
    "source": "libvirt",
    "vms": [
        {
            "id": 1,
            "name": "vm-one",
            "state": 1,
            "cpu_count": 4,
            "memory_max": 8589934592,
            "memory_used": 4294967296
        },
        {
            "id": 2,
            "name": "vm-two",
            "state": 1,
            "cpu_count": 2,
            "memory_max": 4294967296,
            "memory_used": 2147483648
        }
    ]
}
```

### GET /api/telemetry/vm-stats/{vm_id}
Returns 26+ metrics for specified VM.

**Response:**
```json
{
    "vm_id": "1",
    "metrics": {
        "state": 1,
        "cpus": 1,
        "cputime": 462300000000,
        "timeusr": 386634828000,
        "timesys": 75687191000,
        "memactual": 4194304,
        "memrss": 4241820,
        "net_rxbytes": 466770622,
        "net_rxpackets": 1234567,
        "net_txbytes": 9378567,
        "net_txpackets": 987654,
        "disk_rd_bytes": 2796095488,
        "disk_rd_req": 233253,
        "disk_wr_bytes": 2991244800,
        "disk_wr_reqs": 37720,
        "disk_errors": -1,
        "... and 10+ more metrics ..."
    }
}
```

---

## Summary

The refactored Main Gauges page provides a modern, data-driven interface for monitoring VM resource trends through rate-of-change visualization. By displaying how fast metrics are changing (rather than absolute values), users can quickly identify which resources are being actively used or are experiencing spikes in activity.

The implementation is:
- ✅ **Modular** - Easy to add/remove gauges
- ✅ **Responsive** - Works on mobile, tablet, desktop
- ✅ **Real-time** - Updates every 2 seconds with live data
- ✅ **Performant** - Lightweight calculations and rendering
- ✅ **Maintainable** - Well-documented with clear code structure

