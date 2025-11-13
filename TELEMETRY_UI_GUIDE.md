# 🎛️ Telemetry Monitoring Dashboard - UI Documentation

## ✨ What Was Added

A **complete web-based Telemetry Monitoring Dashboard** with:
- ✅ Control buttons (Start/Stop/Refresh)
- ✅ Real-time status display
- ✅ List of monitored VMs
- ✅ Configuration display
- ✅ Activity log with timestamps
- ✅ Automatic status refresh every 2 seconds
- ✅ Beautiful gradient UI with responsive design

---

## 📍 Access the Dashboard

### URL
```
http://localhost:8000/telemetry
```

### Navigation
The telemetry link is added to the navbar on all pages:
- Main Gauges (`/`)
- Virtual Machines (`/vms`)
- **Telemetry** (`/telemetry`) ← NEW

---

## 🎮 UI Components

### 1. Control Panel
Three action buttons at the top:

| Button | Function | Icon |
|--------|----------|------|
| **Start Monitoring** | Begin telemetry collection | ▶ |
| **Stop Monitoring** | Gracefully stop collection | ⏹ |
| **Refresh Status** | Manually update status | 🔄 |

**Behavior:**
- Start button **disabled** when telemetry is running
- Stop button **disabled** when telemetry is stopped
- Buttons auto-sync with actual telemetry state

### 2. Status Card
Displays real-time telemetry statistics:

| Field | Shows |
|-------|-------|
| Status | Current state (running/stopped) |
| Running | Yes/No flag |
| Message | Status message |
| Collections | Number of data collection cycles |
| VMs Monitored | Count of discovered VMs |
| Total Metrics | Metrics written to InfluxDB |
| Last Collection | Timestamp of most recent collection |
| Errors | Number of errors encountered |

**Status Indicator:**
- 🟢 **Green** = Running
- 🔴 **Red** = Stopped

### 3. Monitored VMs Card
Shows all discovered KVM/QEMU virtual machines:

Each VM displays:
- **VM Name** (clickable ID if no name)
- **ID** - Unique identifier
- **Architecture** - CPU architecture (x86_64, etc)
- **Memory** - Max allocated (formatted as GB/MB/KB)
- **vCPUs** - Number of virtual CPUs
- **Status Badge** - Running (green) or Stopped (red)

### 4. Configuration Card
Shows current telemetry settings:

| Field | Value |
|-------|-------|
| LibVirt URI | KVM connection string |
| InfluxDB URL | Database URL |
| Database | Database name |
| Poll Interval | Collection frequency (seconds) |

**Tip:** All sensitive data is masked in responses (`***`)

### 5. Activity Log
Real-time log of all actions:

**Log Types:**
- 🔵 **Blue** (info) - General information
- 🟢 **Green** (success) - Successful operations
- 🔴 **Red** (error) - Errors and failures
- 🟡 **Yellow** (warning) - Warnings

**Features:**
- Auto-scrolls to latest entries
- Keeps last 50 entries
- Timestamps on every log entry
- "Clear" button to reset log

---

## 🚀 Usage Workflow

### Starting Telemetry Monitoring

1. Open dashboard: http://localhost:8000/telemetry
2. Click **"Start Monitoring"** button
3. See activity log: `Starting telemetry collection...`
4. Wait for success: `✓ Telemetry started successfully`
5. View status: Status changes to "Running" (green)
6. Check VMs: Discovered VMs appear in the VMs card
7. Monitor metrics: Collections counter increments

### Checking Status

1. Status automatically refreshes every 2 seconds
2. Or click **"Refresh Status"** for immediate update
3. View statistics:
   - How many collections have run
   - How many VMs are being monitored
   - How many metrics written
   - Timestamp of last collection

### Stopping Telemetry Monitoring

1. Click **"Stop Monitoring"** button
2. See activity log: `Stopping telemetry collection...`
3. Wait for confirmation: `✓ Telemetry stopped successfully`
4. Status changes to "Stopped" (red)
5. Collection statistics frozen until restart

---

## 🎨 Design Features

### Visual Hierarchy
- **Control Panel** at top (bright gradient buttons)
- **Status** prominent with color indicators
- **VMs** in responsive grid
- **Config** for reference
- **Activity Log** scrollable for details

### Color Scheme
- **Green**: Success, running state
- **Red**: Stopped, errors
- **Blue**: Information, actions
- **Yellow**: Warnings
- **Purple**: Primary accent (navbar, buttons)

### Responsive Design
- ✅ Works on desktop (1400px+)
- ✅ Works on tablet (768px+)
- ✅ Works on mobile (responsive grid collapses to single column)

### Real-time Updates
- Status refreshes automatically every 2 seconds
- No page reload needed
- Activity log updates live
- Button states sync with backend

---

## 📊 API Calls Behind the Scenes

The dashboard calls these endpoints automatically:

| Endpoint | Method | Called | Purpose |
|----------|--------|--------|---------|
| `/api/telemetry/start` | POST | On "Start" click | Start collection |
| `/api/telemetry/stop` | POST | On "Stop" click | Stop collection |
| `/api/telemetry/status` | GET | Every 2 seconds | Get status & stats |
| `/api/telemetry/vms` | GET | Every 2 seconds | List VMs |
| `/api/telemetry/config` | GET | Every 2 seconds | Get config |

---

## 🔧 Technical Details

### Files Created/Modified

| File | Change |
|------|--------|
| `templates/telemetry.html` | ✨ NEW - Main telemetry page |
| `templates/index.html` | Updated navbar (added Telemetry link) |
| `templates/vms.html` | Updated navbar (added Telemetry link) |
| `static/css/style.css` | Added 300+ lines of telemetry styling |
| `static/js/telemetry-monitor.js` | ✨ NEW - Telemetry control logic |
| `src/main.py` | Added `/telemetry` route |

### JavaScript Functions

**Control Functions:**
- `startTelemetry()` - Start collection
- `stopTelemetry()` - Stop collection
- `refreshStatus()` - Manual refresh

**UI Functions:**
- `updateUI(status)` - Update all status displays
- `displayVMs(vms)` - Render VM list
- `displayConfig(config)` - Show config
- `addActivityLog(message, type)` - Log entry
- `renderActivityLog()` - Render log
- `clearActivityLog()` - Clear log

**Utility Functions:**
- `escapeHtml(text)` - Prevent XSS
- `formatBytes(bytes)` - Format memory sizes

---

## 🎯 Key Features

### 1. Real-time Status
```
Status: running
Running: Yes
Collections: 42
VMs: 5
Metrics: 1,847
Last: 2025-11-11 14:23:45
```

### 2. Live VM Discovery
```
┌─ vm-1 (RUNNING) ─┐
│ ID: 1            │
│ Memory: 8.0 GB   │
│ vCPUs: 4         │
└──────────────────┘
```

### 3. Activity Timeline
```
[14:23:45] ✓ Telemetry started successfully
[14:23:46] Discovered 5 VMs
[14:23:47] Collection cycle 1 complete
[14:23:48] 184 metrics written
```

---

## 🐛 Troubleshooting

### "Telemetry collector not initialized"
**Solution:** Set environment variables first:
```bash
export LIBVIRT_URI="qemu+ssh://user@host/system"
export INFLUX_URL="http://127.0.0.1:8181"
export INFLUX_DB="vmstats"
export INFLUX_TOKEN="your-token"
```

### Start button still disabled
**Solution:** Refresh page or click "Refresh Status" button

### No VMs appear
**Solution:** 
1. Ensure LibVirt URI is correct
2. Check if VMs are actually running on target host
3. View error in activity log

### Activity log stuck
**Solution:** Click "Clear" button and try again

---

## 📈 Next Steps

1. **Start the server:**
   ```bash
   python -m uvicorn src.main:app --reload
   ```

2. **Open dashboard:**
   ```
   http://localhost:8000/telemetry
   ```

3. **Start monitoring:**
   - Click "Start Monitoring" button
   - Watch activity log for real-time updates
   - Monitor VM list and statistics

4. **Check InfluxDB:**
   - Data flows to InfluxDB in real-time
   - Query via InfluxDB UI or CLI

---

## 🎉 You're All Set!

The telemetry dashboard is now fully integrated with:
- ✅ Beautiful UI
- ✅ Real-time controls
- ✅ Live status updates
- ✅ Activity logging
- ✅ Responsive design
- ✅ Mobile friendly

**Happy monitoring!** 📊
