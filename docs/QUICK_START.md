# Resource Monitoring Page - Quick Start Guide

## 🚀 Quick Access

### URL
```
http://localhost:8000/resource-monitoring
```

### Prerequisites
- ✅ Dashboard backend running
- ✅ FastAPI server listening on port 8000
- ✅ Telemetry data available in InfluxDB
- ✅ Live VMs in libvirt

---

## 📋 Step-by-Step Usage

### 1️⃣ Access the Page
```
1. Open browser
2. Navigate to: http://localhost:8000/resource-monitoring
3. Page should load with VM dropdown visible
```

### 2️⃣ Select a VM
```
1. Click the VM dropdown menu
2. Choose a VM from the list (shows vCPU count and RAM)
3. Page updates automatically with selected VM's metrics
```

### 3️⃣ View Real-Time Metrics
```
1. Metrics display in 4 tabs:
   - CPU & Memory (11 metrics)
   - Network (8 metrics)
   - Disk (5 metrics)
   - Per-Device (expandable)

2. Each metric shows:
   - Current value with unit
   - Time-series line graph
   - Last 60 data points (5-second intervals = 5 minutes history)
```

### 4️⃣ Interact with Graphs
```
1. Hover over graph line to see tooltip with exact value
2. Scroll horizontally in graph container to view history
3. Click refresh button (🔄) to manually update all metrics
```

### 5️⃣ Switch VMs
```
1. Select different VM from dropdown
2. All graphs and values update automatically
3. History persists per VM (cleared on page reload)
```

---

## 📊 Metric Categories

### CPU & Memory
- User CPU Time (ns)
- System CPU Time (ns)
- Actual Memory (KB)
- Memory RSS (KB)
- Available Memory (KB)
- Usable Memory (KB)
- Swap In (pages)
- Swap Out (pages)
- Major Page Faults
- Minor Page Faults
- Disk Cache (KB)

### Network
- RX Bytes (total received)
- RX Packets (total received)
- RX Errors (total errors)
- RX Drops (total dropped)
- TX Bytes (total transmitted)
- TX Packets (total transmitted)
- TX Errors (total errors)
- TX Drops (total dropped)

### Disk
- Read Requests (count)
- Read Bytes (total)
- Write Requests (count)
- Write Bytes (total)
- Disk Errors (count)

### Per-Device (Expandable)
- Future: Device-specific metrics
- Show metrics for individual NICs, disks

---

## 🎯 Common Tasks

### View Memory Trends
```
1. Go to "CPU & Memory" tab
2. Look at "Actual Memory" metric
3. Graph shows memory usage over last 5 minutes
4. Hover to see exact values
```

### Check Network Activity
```
1. Go to "Network" tab
2. View RX Bytes and TX Bytes
3. Compare incoming vs outgoing traffic
4. Check for errors or drops
```

### Monitor Disk I/O
```
1. Go to "Disk" tab
2. Watch Read/Write requests and bytes
3. Identify I/O patterns
4. Check for disk errors
```

### Compare Current vs Historical
```
1. View metric graph
2. Scroll right to see latest point
3. Scroll left to see historical data
4. Identify trends and anomalies
```

### Get Latest Data
```
1. Click "🔄 Refresh Now" button
2. All metrics update immediately
3. Next automatic update in 5 seconds
```

---

## 🔧 Customization

### Change Polling Interval
In `/static/js/resource-monitoring.js`, find line ~160:
```javascript
// Current: 5000ms = 5 seconds
state.pollingInterval = setInterval(async () => {
    if (state.selectedVmId) {
        await fetchVMTelemetry();
    }
}, 5000); // Change this value (milliseconds)
```

**Recommended values:**
- Fast: 1000ms (1 second) - updates frequently, more data
- Standard: 5000ms (5 seconds) - balanced
- Slow: 10000ms (10 seconds) - less bandwidth, coarser updates

### Change History Size
In `/static/js/resource-monitoring.js`, find line ~15:
```javascript
// Current: 60 points
state.maxHistoryPoints = 60; // With 5-sec interval = 5 minutes

// Examples:
// 12 points @ 5sec = 1 minute
// 60 points @ 5sec = 5 minutes  
// 120 points @ 5sec = 10 minutes
```

### Change Graph Colors
In `/static/css/resource-monitoring.css`, find `.metric-card`:
```css
/* Change primary graph color */
border-color: #4caf50; /* Current: green */
background-color: #2a2a3e; /* Dark background */
```

---

## ⚠️ Troubleshooting

### VMs Not Showing in Dropdown

**Problem**: Dropdown is empty

**Solutions**:
1. Check if any VMs are running:
   ```bash
   virsh list --all
   ```

2. Check API endpoint:
   ```bash
   curl http://localhost:8000/api/telemetry/live-vms
   ```
   Should return list of VMs

3. Check browser console (F12):
   - Look for error messages
   - Check network tab for failed requests

### Metrics Not Updating

**Problem**: Values stay at 0 or "N/A"

**Solutions**:
1. Verify telemetry data exists:
   ```bash
   # Check if InfluxDB has data
   curl http://localhost:8000/api/telemetry/vm-stats/1
   ```

2. Click "🔄 Refresh Now" button manually

3. Check browser console for errors:
   ```
   F12 → Console tab → Look for errors
   ```

4. Try switching VMs:
   - Select different VM
   - See if that VM has data
   - Switch back

### Graphs Not Displaying

**Problem**: Graph containers show but no lines

**Solutions**:
1. Wait 10-15 seconds for data to accumulate
2. Click refresh button
3. Try different metric tab
4. Check browser console for JavaScript errors

### High Memory Usage

**Problem**: Browser tab uses lots of memory

**Solutions**:
1. Reduce polling interval (less frequent updates)
2. Reduce `maxHistoryPoints` (keep less history)
3. Close other browser tabs
4. Reload page to clear history

### Slow Page Performance

**Problem**: Graphs lag when updating

**Solutions**:
1. Increase polling interval (less frequent updates)
2. Reduce number of VMs being monitored
3. Check network bandwidth (Network tab in F12)
4. Try different browser or clear cache

---

## 🔍 Developer Console

### Access Developer Tools
```
Windows/Linux: F12
Mac: Cmd + Option + I
```

### Useful Console Commands

Check VM list:
```javascript
fetch('/api/telemetry/live-vms').then(r => r.json()).then(d => console.log(d))
```

Check VM metrics:
```javascript
fetch('/api/telemetry/vm-stats/1').then(r => r.json()).then(d => console.log(d))
```

Check application state:
```javascript
console.log(state)
```

Check active charts:
```javascript
console.log(state.charts)
```

---

## 📱 Mobile Usage

### Supported Devices
- iPhone/iPad (iOS 14+)
- Android phones/tablets (Chrome, Firefox)
- Responsive on all screen sizes

### Mobile Limitations
- Smaller graphs (scroll horizontally to see history)
- Touch-friendly dropdown
- Same 5-second polling

### Tips for Mobile
1. Landscape mode for better graph visibility
2. Use pinch-zoom to zoom into graphs
3. Tap and hold on graph to see tooltip
4. Swipe to scroll between metrics

---

## 🎮 Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| F12 | Open Developer Tools |
| Ctrl+F5 | Force reload page |
| Arrow Keys | Navigate dropdown |
| Tab | Move between elements |
| Enter | Select from dropdown |

---

## 📞 Support Resources

### Documentation
- **Main Docs**: `docs/RESOURCE_MONITORING_PAGE.md`
- **API Guide**: `docs/API_INTEGRATION_GUIDE.md`

### Key Files
- HTML: `/templates/resource-monitoring.html`
- CSS: `/static/css/resource-monitoring.css`
- JavaScript: `/static/js/resource-monitoring.js`

### Backend Configuration
- Main: `/src/main.py`
- API: `/src/api/routes.py` or `/src/api/telemetry.py`

---

## ✅ Verification Checklist

After deployment, verify:

- [ ] Page loads at http://localhost:8000/resource-monitoring
- [ ] VM dropdown shows at least one VM
- [ ] Selecting VM displays metrics
- [ ] Graphs show lines (wait 10+ seconds if needed)
- [ ] Values update automatically every 5 seconds
- [ ] Refresh button updates all metrics
- [ ] Tab switching works
- [ ] No console errors (F12)
- [ ] Page is responsive on mobile
- [ ] Scrollable graph containers work

---

## 🚀 Next Steps

1. **Test with live data**: Monitor real VMs
2. **Fine-tune settings**: Adjust polling interval and history size
3. **Review metrics**: Ensure all 26 metrics are needed
4. **Add to navigation**: Link from main dashboard
5. **Set up monitoring**: Use for production monitoring

---

## 💡 Tips & Best Practices

### Monitoring Best Practices
1. **Watch trends, not absolutes**: Look for patterns
2. **Correlate metrics**: Check CPU + Memory together
3. **Monitor network + disk**: Identify bottlenecks
4. **Set baselines**: Know normal for your VMs

### Performance Tips
1. **Use Safari/Chrome**: Better performance
2. **Monitor one VM at a time**: Faster UI
3. **Adjust polling interval**: Balance vs bandwidth
4. **Keep history reasonable**: 60 points is standard

### Troubleshooting Tips
1. **Always check console**: F12 Console tab
2. **Try refresh**: Click 🔄 button
3. **Reload page**: Clear history/state
4. **Check network**: DevTools Network tab

---

## Version Information

**Current Version**: 1.0
**Last Updated**: 2024
**Compatible With**: FastAPI 0.100+, Python 3.8+

---

**Ready to monitor? Open http://localhost:8000/resource-monitoring and get started! 🎯**
