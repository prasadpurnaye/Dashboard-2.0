# 🎛️ Telemetry Dashboard - Complete Setup Guide

## 📋 What's New

You now have a **complete telemetry monitoring dashboard** with:

✅ **Web UI at `/telemetry`**
- Start/Stop buttons for telemetry collection
- Real-time status display
- Live VM discovery and monitoring
- Activity log with timestamps
- Configuration display

✅ **Updated Navigation**
- All pages now have Telemetry link in navbar
- Easy access from Main Gauges or VMs pages

✅ **Real-time Updates**
- Status refreshes every 2 seconds
- Auto-sync button states
- Live activity logging

---

## 🚀 Quick Start

### 1. Configure Environment
```bash
cd /home/r/Dashboard2.0/dashboard-2.0

# Set required environment variables
export LIBVIRT_URI="qemu+ssh://oneadmin@192.168.0.104/system"
export INFLUX_URL="http://127.0.0.1:8181"
export INFLUX_DB="vmstats"
export INFLUX_TOKEN="apiv3_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

### 2. Start the Server
```bash
python3 -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Open Dashboard
```
http://localhost:8000/telemetry
```

### 4. Start Monitoring
Click the **"Start Monitoring"** button and watch:
- Activity log updates in real-time
- Status changes to "Running" (green)
- VMs appear in the VM list
- Collection counter increments

---

## 📁 Files Added/Modified

### New Files
```
templates/telemetry.html              ← Main telemetry page
static/js/telemetry-monitor.js        ← Control logic
TELEMETRY_UI_GUIDE.md                 ← UI documentation
```

### Modified Files
```
src/main.py                           ← Added /telemetry route
templates/index.html                  ← Updated navbar
templates/vms.html                    ← Updated navbar
static/css/style.css                  ← Added 300+ lines of styling
```

---

## 🎮 Dashboard Overview

### Control Panel (Top)
Three gradient buttons:
- 🟢 **Start Monitoring** - Begin collection
- 🔴 **Stop Monitoring** - Gracefully stop
- 🔵 **Refresh Status** - Manual update

### Status Card
Real-time statistics:
```
Status: running
Running: Yes
Message: Telemetry is active
Collections: 42
VMs Monitored: 5
Total Metrics: 1,847
Last Collection: 2025-11-11 14:23:45
Errors: 0
```

### Monitored VMs Card
Grid of discovered VMs:
```
┌─ vm-ubuntu (RUNNING) ─┐    ┌─ vm-centos (RUNNING) ─┐
│ ID: 1                 │    │ ID: 2                  │
│ Arch: x86_64          │    │ Arch: x86_64           │
│ Memory: 8.0 GB        │    │ Memory: 16.0 GB        │
│ vCPUs: 4              │    │ vCPUs: 8               │
└───────────────────────┘    └────────────────────────┘
```

### Configuration Card
Current settings (masked sensitive data):
```
LibVirt URI: ***
InfluxDB URL: ***
Database: vmstats
Poll Interval: 1.0s
```

### Activity Log
Real-time timestamped log:
```
[14:23:43] Starting telemetry collection...
[14:23:44] ✓ Telemetry started successfully
[14:23:44] Connected to LibVirt
[14:23:44] Discovered 5 VMs
[14:23:44] InfluxDB writer started
[14:23:45] Collection cycle 1 complete
[14:23:45] 184 metrics written to InfluxDB
```

---

## 🔌 API Endpoints Used

The dashboard automatically calls these endpoints:

```bash
# Start collection
POST /api/telemetry/start
Response:
{
  "status": "started",
  "message": "Telemetry collection started successfully",
  "details": { ... }
}

# Stop collection
POST /api/telemetry/stop
Response:
{
  "status": "stopped",
  "message": "Telemetry collection stopped successfully"
}

# Get status (called every 2 seconds)
GET /api/telemetry/status
Response:
{
  "status": "running",
  "running": true,
  "message": "Telemetry is active",
  "statistics": {
    "collection_count": 42,
    "total_metrics_written": 1847,
    "vms_count": 5,
    "error_count": 0,
    "last_collection_time": 1731338625.12345
  }
}

# Get monitored VMs
GET /api/telemetry/vms
Response:
{
  "count": 5,
  "vms": [
    {
      "id": "1",
      "name": "vm-ubuntu",
      "state": "running",
      "arch": "x86_64",
      "max_mem": 8589934592,
      "vcpu_count": 4
    }
  ]
}

# Get configuration (masked)
GET /api/telemetry/config
Response:
{
  "config": {
    "libvirt_uri": "***",
    "influx_url": "***",
    "influx_db": "vmstats",
    "poll_interval": 1.0,
    "influx_token": "***"
  }
}
```

---

## 🎨 UI Components Breakdown

### Buttons
| Class | Color | Use |
|-------|-------|-----|
| `.btn-start` | Green gradient | Start action |
| `.btn-stop` | Red gradient | Stop action |
| `.btn-refresh` | Blue gradient | Refresh action |
| `.btn-small` | Purple | Secondary actions |

### Status Indicators
| Class | Color | Meaning |
|-------|-------|---------|
| `.status-running` | Green bg | Telemetry is running |
| `.status-stopped` | Red bg | Telemetry is stopped |
| `.status-error` | Yellow bg | Error state |

### VM Item Status
| Class | Color | Meaning |
|-------|-------|---------|
| `.vm-item-status.running` | Green | VM is running |
| `.vm-item-status.stopped` | Red | VM is stopped |

### Activity Log Types
| Class | Color | Type |
|-------|-------|------|
| `.activity-info` | Blue | Information |
| `.activity-success` | Green | Success |
| `.activity-error` | Red | Error |
| `.activity-warning` | Yellow | Warning |

---

## 🔧 JavaScript Functions

### Control Functions
```javascript
startTelemetry()      // POST /api/telemetry/start
stopTelemetry()       // POST /api/telemetry/stop
refreshStatus()       // GET /api/telemetry/status
```

### UI Update Functions
```javascript
updateUI(status)           // Update all status displays
displayVMs(vms)            // Render VM list
displayConfig(config)      // Show configuration
addActivityLog(msg, type)  // Add log entry
renderActivityLog()        // Render activity log
clearActivityLog()         // Clear log entries
```

### Utility Functions
```javascript
escapeHtml(text)       // Prevent XSS
formatBytes(bytes)     // Format memory sizes
```

---

## 📊 Monitoring Workflow

### 1. Page Load (Automatic)
- Dashboard initializes
- Calls `/api/telemetry/status` to get current state
- Auto-refresh starts (every 2 seconds)
- Logs "Telemetry dashboard loaded"

### 2. Start Monitoring (Click Start Button)
```
[User clicks Start]
   ↓
POST /api/telemetry/start
   ↓
Activity log: "Starting telemetry collection..."
   ↓
Server connects to KVM
Server starts InfluxDB writer
Server starts collection loop
   ↓
Response received
   ↓
Activity log: "✓ Telemetry started successfully"
Status updated to "Running" (green)
Start button disabled
Stop button enabled
```

### 3. Automatic Updates (Every 2 Seconds)
```
GET /api/telemetry/status
   ↓
Update:
- Collections counter
- VMs count
- Metrics written
- Last collection time
- Error count
   ↓
GET /api/telemetry/vms
   ↓
Refresh VM list display
   ↓
GET /api/telemetry/config
   ↓
Refresh config display
```

### 4. Stop Monitoring (Click Stop Button)
```
[User clicks Stop]
   ↓
POST /api/telemetry/stop
   ↓
Activity log: "Stopping telemetry collection..."
   ↓
Server stops collection loop
Server stops InfluxDB writer
Server closes KVM connection
   ↓
Response received
   ↓
Activity log: "✓ Telemetry stopped successfully"
Status updated to "Stopped" (red)
Stop button disabled
Start button enabled
```

---

## 🐛 Common Issues & Solutions

### Issue: "Telemetry collector not initialized"
**Cause:** Environment variables not set  
**Solution:**
```bash
export LIBVIRT_URI="qemu+ssh://user@host/system"
export INFLUX_URL="http://127.0.0.1:8181"
export INFLUX_DB="vmstats"
export INFLUX_TOKEN="your-token"
```

### Issue: Start button won't click
**Cause:** Telemetry already running  
**Solution:** Click "Refresh Status" or refresh the page

### Issue: No VMs appear
**Cause:** VMs not discovered or wrong LibVirt URI  
**Solution:** Check LibVirt connection and ensure VMs are running

### Issue: Activity log stuck
**Cause:** Page not updating  
**Solution:** Click "Refresh Status" or refresh the page

### Issue: Status shows error
**Cause:** Connection or credential issues  
**Solution:** Check:
- LibVirt URI is correct
- InfluxDB server is running
- Token/credentials are valid
- Network connectivity

---

## 📈 Performance Notes

- **Status refresh rate:** Every 2 seconds (configurable)
- **Activity log max entries:** 50 (prevents memory bloat)
- **UI responsiveness:** Non-blocking async API calls
- **Mobile compatible:** Responsive grid, single-column on small screens

---

## 🎯 Features at a Glance

| Feature | Status | Details |
|---------|--------|---------|
| Start/Stop buttons | ✅ | Gradient design, auto-disabled |
| Real-time status | ✅ | Updates every 2 seconds |
| VM discovery | ✅ | Live list with status badges |
| Configuration display | ✅ | Masked sensitive data |
| Activity logging | ✅ | Timestamped, color-coded |
| Auto-refresh | ✅ | No manual refresh needed |
| Mobile responsive | ✅ | Works on all screen sizes |
| Error handling | ✅ | Graceful error messages |
| XSS protection | ✅ | HTML escaping |

---

## 📖 Documentation Files

- **TELEMETRY.md** - Complete API reference
- **TELEMETRY_UI_GUIDE.md** - UI component documentation
- **TELEMETRY_QUICKSTART.md** - 5-minute setup
- **TELEMETRY_IMPLEMENTATION.md** - Architecture details
- **TELEMETRY_SUMMARY.md** - High-level overview
- **.env.example** - Environment template

---

## 🎉 You're Ready!

Everything is set up:
1. ✅ Telemetry page created
2. ✅ Control buttons integrated
3. ✅ Status display configured
4. ✅ Activity logging enabled
5. ✅ Auto-refresh implemented
6. ✅ Responsive design applied
7. ✅ Navigation updated

**Start the server and visit http://localhost:8000/telemetry**

**Happy monitoring!** 📊🎛️
