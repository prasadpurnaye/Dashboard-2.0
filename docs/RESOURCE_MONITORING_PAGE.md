# Resource Monitoring Page - Complete Implementation

## Overview

The Resource Monitoring page provides comprehensive real-time monitoring of individual VM resources with detailed metrics visualization. Users can select a VM from a dropdown and view time-series graphs for all available metrics.

## Features

### ✅ Implemented

1. **VM Selection Dropdown**
   - Lists all live VMs with vCPU and RAM info
   - Updates telemetry on selection change
   - Shows VM state and last update time

2. **Four Metric Categories (Tabbed Interface)**
   - CPU & Memory metrics
   - Network metrics
   - Disk metrics
   - Per-device metrics (expandable)

3. **Time-Series Graphs**
   - Individual line charts for each metric
   - Real-time updates every 5 seconds
   - Scrollable containers for history
   - Color-coded graphs (green for normal, orange for errors)
   - Tooltips showing exact values on hover

4. **Responsive Layout**
   - Grid-based metric card layout
   - Adapts to different screen sizes
   - Mobile-friendly interface

5. **Summary Panel**
   - Quick overview of VM state
   - CPU cores count
   - CPU time info
   - Last update timestamp

## File Structure

```
Dashboard2.0/
├── templates/
│   └── resource-monitoring.html      # Main HTML template
├── static/
│   ├── css/
│   │   └── resource-monitoring.css   # Styling and layout
│   └── js/
│       └── resource-monitoring.js    # Core logic and data fetching
└── src/
    └── main.py                       # Added route: GET /resource-monitoring
```

## HTML Structure (`resource-monitoring.html`)

### Main Sections

1. **Navigation Bar**
   - Integrated with existing dashboard navigation
   - Active indicator for Resource Monitoring page

2. **VM Selection Panel**
   - Dropdown for VM selection
   - Refresh button for manual updates
   - Info display showing current VM details

3. **Summary Panel**
   - 4 summary cards for key metrics
   - VM state, CPU count, CPU time, last update

4. **Tabbed Interface**
   - Tab navigation buttons
   - 4 content sections (CPU/Memory, Network, Disk, Devices)

5. **Metrics Grid**
   - Each metric displayed as a card
   - Card contains:
     - Metric name and label
     - Current value
     - Time-series graph canvas

## CSS Styling (`resource-monitoring.css`)

### Key Classes

- `.resource-monitoring-container` - Main container
- `.vm-selection-panel` - VM selection area
- `.metrics-grid` - Grid layout for metric cards
- `.metric-card` - Individual metric card
- `.graph-container` - Scrollable graph area
- `.tabs-container` - Tabbed interface
- `.tab-btn` - Tab buttons
- `.tab-content` - Tab content sections

### Features

- Dark theme matching existing dashboard
- Green accent color (#4caf50) for primary elements
- Orange accent (#ff9800) for error/warning metrics
- Smooth transitions and hover effects
- Custom scrollbar styling
- Responsive grid layout (auto-fill columns)
- Mobile breakpoints at 1200px and 768px

## JavaScript Logic (`resource-monitoring.js`)

### Global State Object

```javascript
state = {
    selectedVmId: null,           // Currently selected VM ID
    selectedVmName: null,         // VM name
    vms: [],                      // List of all live VMs
    charts: {},                   // Chart.js instances
    metricsHistory: {},           // Historical data for graphs
    pollingInterval: null,        // Polling timer ID
    maxHistoryPoints: 60,         // Max data points to keep
}
```

### Core Functions

#### `loadVMs()`
- Fetches live VMs from `/api/telemetry/live-vms`
- Populates VM dropdown
- Handles errors gracefully

#### `selectVM(vm)`
- Sets selected VM in state
- Shows content area
- Fetches initial telemetry
- Starts polling for updates (every 5 seconds)

#### `fetchVMTelemetry()`
- Calls `/api/telemetry/vm-stats/{vm_id}`
- Gets current metrics for selected VM
- Updates UI and graphs
- Runs on intervals and on manual refresh

#### `updateMetrics(metrics)`
- Updates current value display for all metrics
- Formats values with appropriate units

#### `updateGraphs(metrics)`
- Maintains historical data for each metric
- Keeps only last 60 data points
- Calls graph update/creation function

#### `createOrUpdateGraph(canvasId, history, metricKey)`
- Creates new Chart.js line chart or updates existing
- Color-codes based on metric type
- Enables tooltips and responsive sizing

### Metric Definitions

Each metric has metadata:

```javascript
{
    key: 'metric_name',           // Used in API and DOM
    name: 'Display Name',         // Human-readable name
    unit: 'unit',                 // Unit of measurement
    type: 'number|bytes'          // For formatting
}
```

Three categories:
- **cpu-memory**: 11 metrics
- **network**: 8 metrics  
- **disk**: 5 metrics

## API Integration

### Required Endpoints

#### `GET /api/telemetry/live-vms`
Returns list of running VMs:
```json
{
  "count": 3,
  "source": "libvirt",
  "vms": [
    {
      "id": 1,
      "name": "vm-name",
      "uuid": "...",
      "state": "running",
      "cpu_count": 4,
      "memory_max": 8388608,
      "memory_used": 8388608,
      "cputime": 1234567890
    }
  ]
}
```

#### `GET /api/telemetry/vm-stats/{vm_id}`
Returns metrics for specific VM:
```json
{
  "vm_id": "1",
  "metrics": {
    "state": "running",
    "cpus": 4,
    "cputime": 1234567890,
    "timeusr": 1000000000,
    "timesys": 500000000,
    "memactual": 4194304,
    "memrss": 3145728,
    "memavailable": 1048576,
    ...
  }
}
```

## Metrics Reference

### CPU & Memory
| Metric | Key | Unit | Description |
|--------|-----|------|-------------|
| User CPU Time | timeusr | ns | CPU time in user mode |
| System CPU Time | timesys | ns | CPU time in kernel mode |
| Actual Memory | memactual | KB | Physical memory used |
| Memory RSS | memrss | KB | Resident set size |
| Available Memory | memavailable | KB | Available for allocation |
| Usable Memory | memusable | KB | Usable memory |
| Swap In | memswap_in | - | Pages swapped in |
| Swap Out | memswap_out | - | Pages swapped out |
| Major Faults | memmajor_fault | - | Major page faults |
| Minor Faults | memminor_fault | - | Minor page faults |
| Disk Cache | memdisk_cache | KB | Disk cache memory |

### Network
| Metric | Key | Unit | Description |
|--------|-----|------|-------------|
| RX Bytes | net_rxbytes | B | Bytes received |
| RX Packets | net_rxpackets | - | Packets received |
| RX Errors | net_rxerrors | - | RX errors |
| RX Drops | net_rxdrops | - | RX dropped packets |
| TX Bytes | net_txbytes | B | Bytes transmitted |
| TX Packets | net_txpackets | - | Packets transmitted |
| TX Errors | net_txerrors | - | TX errors |
| TX Drops | net_txdrops | - | TX dropped packets |

### Disk
| Metric | Key | Unit | Description |
|--------|-----|------|-------------|
| Read Requests | disk_rd_req | - | Disk read requests |
| Read Bytes | disk_rd_bytes | B | Bytes read |
| Write Requests | disk_wr_reqs | - | Disk write requests |
| Write Bytes | disk_wr_bytes | B | Bytes written |
| Disk Errors | disk_errors | - | Disk I/O errors |

## Usage

### Accessing the Page
Navigate to: `http://localhost:8000/resource-monitoring`

### Selecting a VM
1. Click the VM dropdown
2. Select a VM from the list
3. The page loads telemetry for that VM
4. Graphs begin updating every 5 seconds

### Viewing Metrics
1. Click tabs to switch between metric categories
2. View current values and time-series graphs
3. Scroll within graph containers to see history
4. Hover over graph lines to see tooltips

### Manual Refresh
- Click the "🔄 Refresh Now" button to update immediately

### Switching VMs
- Select a different VM from dropdown to instantly switch
- All graphs and values update automatically

## Performance Considerations

### Polling Interval
- **Current**: 5 seconds (configurable in `resource-monitoring.js`)
- **Can be changed**: Modify `setInterval(..., 5000)`

### Data Retention
- **Current**: Last 60 data points per metric
- **Can be changed**: Modify `state.maxHistoryPoints = 60`

### Graph Performance
- Charts updated without animation for smooth updates
- Only displayed metrics are graphed (lazy initialization)
- Old data points automatically discarded

### Optimization Tips
1. Increase polling interval for slower networks
2. Decrease max history points if memory is low
3. Use browser dev tools to monitor chart instances

## Browser Compatibility

✅ Chrome/Chromium 90+
✅ Firefox 88+
✅ Safari 14+
✅ Edge 90+

Requires:
- ES6 (async/await)
- Canvas API
- Fetch API
- Chart.js 4.x

## Future Enhancements

1. **Per-Device Metrics Display**
   - Show individual NIC metrics
   - Show individual disk metrics

2. **Export Data**
   - Export graphs as PNG
   - Export metrics as CSV

3. **Alerting**
   - Set thresholds for metrics
   - Notifications on threshold breach

4. **Metric Comparison**
   - Compare multiple VMs side-by-side
   - Compare time periods

5. **Historical Data**
   - Load longer history from InfluxDB
   - Zoom and pan capabilities

6. **Custom Dashboards**
   - Select which metrics to display
   - Save dashboard layouts

## Troubleshooting

### VMs not appearing in dropdown
- Check if `/api/telemetry/live-vms` returns data
- Verify libvirt connection is working
- Check browser console for errors

### Graphs not updating
- Verify `/api/telemetry/vm-stats/{vm_id}` endpoint works
- Check network tab in DevTools
- Ensure polling interval is reasonable

### High memory usage
- Reduce `maxHistoryPoints` value
- Increase polling interval
- Close unused charts

## Code Examples

### Change Polling Interval
```javascript
// In resource-monitoring.js, line ~160
state.pollingInterval = setInterval(async () => {
    if (state.selectedVmId) {
        await fetchVMTelemetry();
    }
}, 10000); // Change 5000 to 10000 for 10-second interval
```

### Add Custom Metric
```javascript
// In metricDefinitions, add to appropriate category
{
    key: 'custom_metric',
    name: 'Custom Metric',
    unit: 'units',
    type: 'number'
}
```

### Change Graph Colors
```javascript
// In createOrUpdateGraph function
borderColor = '#your-color';
backgroundColor = 'rgba(r,g,b,a)';
```

## Testing Checklist

- [ ] Page loads without errors
- [ ] VM dropdown populates with all VMs
- [ ] Selecting VM updates all metrics
- [ ] Graphs display and update in real-time
- [ ] Tab switching works correctly
- [ ] Scrollable graph containers work
- [ ] Refresh button updates data
- [ ] Error messages display appropriately
- [ ] Page is responsive on mobile
- [ ] Console shows no errors

## Support

For issues or questions:
1. Check browser console (F12)
2. Verify API endpoints are working
3. Check application logs
4. Review troubleshooting section above
