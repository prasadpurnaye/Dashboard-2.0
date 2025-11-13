# 🎛️ Telemetry Dashboard - Visual Overview

## 📍 Navigation Structure

```
┌─────────────────────────────────────────────────────┐
│  Dashboard 2.0  │  Main Gauges  │  VMs  │  Telemetry  │
└─────────────────────────────────────────────────────┘
                    Purple Gradient Navbar
```

Each page has the telemetry link, making it easy to jump between pages.

---

## 🎨 Telemetry Dashboard Layout

```
┌────────────────────────────────────────────────────────────┐
│  Dashboard 2.0  │ Main Gauges  │  VMs  │ Telemetry (ACTIVE) │
└────────────────────────────────────────────────────────────┘

    Telemetry Monitoring
    Control and monitor KVM/QEMU telemetry collection

┌────────────────────────────────────────────────────────────┐
│ Telemetry Controls                                          │
│ ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│ │ ▶ Start         │  │ ⏹ Stop          │  │ 🔄 Refresh   │ │
│ │ Monitoring      │  │ Monitoring      │  │ Status       │ │
│ └─────────────────┘  └─────────────────┘  └──────────────┘ │
│        (Green)           (Red)               (Blue)         │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│ Telemetry Status                          🟢 Running       │
├────────────────────────────────────────────────────────────┤
│ Status: running              Running: Yes                  │
│ Message: Telemetry is active     Collections: 42           │
│ VMs Monitored: 5             Total Metrics: 1,847          │
│ Last Collection: 2025-11-11 14:23:45                       │
│ Errors: 0                                                   │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│ Monitored Virtual Machines                                  │
├────────────────────────────────────────────────────────────┤
│ ┌──────────────────────┐  ┌──────────────────────┐         │
│ │ vm-ubuntu            │  │ vm-centos            │         │
│ │ ID: 1                │  │ ID: 2                │         │
│ │ Arch: x86_64         │  │ Arch: x86_64         │         │
│ │ Memory: 8.0 GB       │  │ Memory: 16.0 GB      │         │
│ │ vCPUs: 4             │  │ vCPUs: 8             │         │
│ │ 🟢 RUNNING           │  │ 🟢 RUNNING           │         │
│ └──────────────────────┘  └──────────────────────┘         │
│                                                              │
│ ┌──────────────────────┐  ┌──────────────────────┐         │
│ │ vm-debian            │  │ vm-windows           │         │
│ │ ID: 3                │  │ ID: 4                │         │
│ │ Arch: x86_64         │  │ Arch: x86_64         │         │
│ │ Memory: 4.0 GB       │  │ Memory: 12.0 GB      │         │
│ │ vCPUs: 2             │  │ vCPUs: 6             │         │
│ │ 🟢 RUNNING           │  │ 🔴 STOPPED           │         │
│ └──────────────────────┘  └──────────────────────┘         │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│ Configuration                                               │
├────────────────────────────────────────────────────────────┤
│ LibVirt URI: ***                                            │
│ InfluxDB URL: ***                                           │
│ Database: vmstats                                           │
│ Poll Interval: 1.0s                                         │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│ Recent Activity                                 [Clear]     │
├────────────────────────────────────────────────────────────┤
│ [14:23:43] Starting telemetry collection...               │
│ [14:23:44] ✓ Telemetry started successfully              │
│ [14:23:44] Connected to LibVirt                           │
│ [14:23:44] Discovered 5 VMs                               │
│ [14:23:44] InfluxDB writer started                        │
│ [14:23:45] Collection cycle 1 complete                    │
│ [14:23:45] 184 metrics written to InfluxDB                │
│ [14:23:46] Collection cycle 2 complete                    │
│ [14:23:46] 181 metrics written to InfluxDB                │
└────────────────────────────────────────────────────────────┘
```

---

## 🎮 Interactive Elements

### Control Buttons
```
┌─────────────────────────────────────────────────────────────┐
│ Telemetry Controls                                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐    ┌──────────────────┐               │
│  │  ▶ START         │    │  ⏹ STOP          │               │
│  │ Monitoring       │    │ Monitoring       │               │
│  │ (Green Gradient) │    │ (Red Gradient)   │               │
│  │ [enabled]        │    │ [disabled]       │               │
│  └──────────────────┘    └──────────────────┘               │
│                                                              │
│  When telemetry is STOPPED:                                │
│    - Start button:  ✅ Enabled (clickable)                 │
│    - Stop button:   ❌ Disabled (grayed out)               │
│                                                              │
│  When telemetry is RUNNING:                                │
│    - Start button:  ❌ Disabled (grayed out)               │
│    - Stop button:   ✅ Enabled (clickable)                 │
│                                                              │
│  Refresh button:                                            │
│    - Always ✅ Enabled (manually refresh status)           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Status Indicator
```
             │ STOPPED        │ RUNNING
─────────────┼────────────────┼─────────────
Background  │ Red (#fee2e2)  │ Green (#d1fae5)
Foreground  │ Dark Red       │ Dark Green
Text        │ "Stopped"      │ "Running"
Icon        │ 🔴            │ 🟢
```

### Activity Log Colors
```
[Blue]   ℹ️  Information messages
[Green]  ✓  Success messages
[Red]    ✗  Error messages
[Yellow] ⚠️  Warning messages
```

---

## 📊 Data Flow Diagram

```
┌──────────────────────────────────────────────────────────┐
│ Telemetry Dashboard (Browser)                             │
├──────────────────────────────────────────────────────────┤
│                                                            │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ Control Panel                                       │ │
│  │ [Start] [Stop] [Refresh]                           │ │
│  └──────────────┬────────────────────────────────────┬─ │
│                 │ Click "Start"                      │  │
│                 │ POST /api/telemetry/start          │  │
│                 │ (with callback on response)        │  │
│                 ↓                                      ↓  │
│  ┌──────────────────────────┐   ┌──────────────────────┐ │
│  │ Activity Log             │   │ Status Display       │ │
│  │ Real-time updates        │   │ Auto-refresh every   │ │
│  │ Timestamped entries      │   │ 2 seconds            │ │
│  │ Color-coded by type      │   │ GET /api/telemetry/  │ │
│  │ [Clear] button           │   │ status               │ │
│  └──────────────────────────┘   ├──────────────────────┤ │
│                                  │ Collections: 42      │ │
│                                  │ VMs: 5               │ │
│  ┌──────────────────────────────┴──────────────────────┐ │
│  │ VM Grid                                             │ │
│  │ Auto-refresh every 2 seconds                        │ │
│  │ GET /api/telemetry/vms                              │ │
│  │ ┌────────────┐ ┌────────────┐ ┌────────────┐        │ │
│  │ │ vm-ubuntu  │ │ vm-centos  │ │ vm-debian  │        │ │
│  │ │ 🟢 Running │ │ 🟢 Running │ │ 🔴 Stopped │        │ │
│  │ └────────────┘ └────────────┘ └────────────┘        │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ Configuration                                       │ │
│  │ Auto-refresh every 2 seconds                        │ │
│  │ GET /api/telemetry/config                           │ │
│  │ LibVirt URI: ***                                    │ │
│  │ InfluxDB: ***                                       │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
└────────────────────┬─────────────────────────────────────┘
                     │ API Calls
                     ↓
        ┌──────────────────────────┐
        │ FastAPI Backend          │
        ├──────────────────────────┤
        │ /api/telemetry/start     │
        │ /api/telemetry/stop      │
        │ /api/telemetry/status    │
        │ /api/telemetry/vms       │
        │ /api/telemetry/config    │
        └────────┬─────────────────┘
                 │
        ┌────────┴────────┬─────────────┐
        ↓                 ↓             ↓
    ┌────────┐    ┌───────────┐   ┌──────────┐
    │ KVM    │    │ InfluxDB  │   │ Telemetry│
    │LibVirt │    │ v3        │   │ Collector│
    │        │    │           │   │          │
    │ VMs    │    │ Metrics   │   │ Service  │
    └────────┘    └───────────┘   └──────────┘
```

---

## 🔄 Auto-Refresh Timeline

```
0s   → Page loads
       └→ GET /api/telemetry/status
       └→ Update status display
       └→ GET /api/telemetry/vms
       └→ Update VM list
       └→ GET /api/telemetry/config
       └→ Update config display
       └→ Start auto-refresh timer

2s   → Auto-refresh tick
       └→ GET /api/telemetry/status (Collections: 5)
       └→ GET /api/telemetry/vms
       └→ GET /api/telemetry/config

4s   → Auto-refresh tick
       └→ GET /api/telemetry/status (Collections: 6)
       └→ GET /api/telemetry/vms
       └→ GET /api/telemetry/config

6s   → Auto-refresh tick
       └→ GET /api/telemetry/status (Collections: 7)
       └→ GET /api/telemetry/vms
       └→ GET /api/telemetry/config

... continues every 2 seconds ...

∞    → When "Stop" clicked:
       └→ POST /api/telemetry/stop
       └→ GET /api/telemetry/status
       └→ Update UI (status→stopped, buttons disabled)
```

---

## 📱 Responsive Breakpoints

```
Desktop (1400px+)
┌─────────────────────────────────────────────────────────┐
│ [Start] [Stop] [Refresh]                               │
├─────────────────────────────────────────────────────────┤
│ Status (grid: 2 columns)  │ VMs (grid: 3 columns)      │
│ Collections: 42           │ ┌──────┐ ┌──────┐         │
│ VMs: 5                    │ │vm-1  │ │vm-2  │         │
│ Metrics: 1,847            │ └──────┘ └──────┘         │
└─────────────────────────────────────────────────────────┘

Tablet (768px)
┌──────────────────────────────────────────┐
│ [Start] [Stop] [Refresh]                │
├──────────────────────────────────────────┤
│ Status (grid: 1 column)  │ VMs (grid: 2) │
│ Collections: 42          │ ┌──────┐      │
│ VMs: 5                   │ │vm-1  │      │
│ Metrics: 1,847           │ └──────┘      │
└──────────────────────────────────────────┘

Mobile (480px)
┌────────────────────────────┐
│ [Start] [Stop] [Refresh]  │
├────────────────────────────┤
│ Status (1 column)          │
│ Collections: 42            │
│ VMs: 5                     │
├────────────────────────────┤
│ VMs (1 column)             │
│ ┌──────────────────────┐   │
│ │ vm-1 (🟢 RUNNING)    │   │
│ │ 8.0 GB, 4 vCPUs      │   │
│ └──────────────────────┘   │
└────────────────────────────┘
```

---

## 🎯 State Machine

```
START PAGE
    ↓
CHECK CONFIG
    ├→ Found: Initialize collector
    └→ Not found: Show warning, but allow UI access

TELEMETRY STOPPED (Initial State)
    ├→ User clicks [Start]
    │  ├→ POST /api/telemetry/start
    │  ├→ Wait for response
    │  ├→ If success → TELEMETRY RUNNING
    │  └→ If error → TELEMETRY STOPPED (show error)
    │
    ├→ User clicks [Refresh]
    │  └→ GET status, VMs, config (no state change)
    │
    └→ Page auto-refreshes every 2s
       └→ GET status (confirm still stopped)

TELEMETRY RUNNING (Active Collection)
    ├→ User clicks [Stop]
    │  ├→ POST /api/telemetry/stop
    │  ├→ Wait for response
    │  ├→ If success → TELEMETRY STOPPED
    │  └→ If error → TELEMETRY RUNNING (show error)
    │
    ├→ User clicks [Refresh]
    │  └→ GET status, VMs, config (no state change)
    │
    └→ Page auto-refreshes every 2s
       ├→ GET status (update counters)
       ├→ GET VMs (show updated list)
       └→ GET config (show settings)

ON PAGE UNLOAD
    └→ Cleanup: Clear auto-refresh interval
```

---

## 💡 User Interactions

### Scenario 1: Start Monitoring
```
User sees: Dashboard with status = STOPPED (🔴)
User action: Click "Start Monitoring"
System response:
  1. Button becomes disabled
  2. Activity log: "Starting telemetry collection..."
  3. POST request sent to /api/telemetry/start
  4. Server initializes KVM connection
  5. Server starts InfluxDB writer
  6. Server starts collection loop
  7. Response received
  8. Status updates to "Running" (🟢)
  9. Activity log: "✓ Telemetry started successfully"
  10. Stop button enables
  11. Auto-updates continue (every 2s):
      - Collections counter increments
      - VMs list updates
      - Last collection time updates
```

### Scenario 2: Stop Monitoring
```
User sees: Dashboard with status = RUNNING (🟢)
User action: Click "Stop Monitoring"
System response:
  1. Button becomes disabled
  2. Activity log: "Stopping telemetry collection..."
  3. POST request sent to /api/telemetry/stop
  4. Server stops collection loop
  5. Server flushes remaining metrics to InfluxDB
  6. Server closes KVM connection
  7. Response received
  8. Status updates to "Stopped" (🔴)
  9. Activity log: "✓ Telemetry stopped successfully"
  10. Start button enables
  11. Collection statistics freeze (no more updates)
```

### Scenario 3: Check Status
```
User sees: Telemetry status card
User sees: Collections = 42, Last = 14:23:45
Time passes: 5 seconds
System action:
  1. Auto-refresh timer fires (every 2 seconds)
  2. GET /api/telemetry/status
  3. Response received
  4. Collections now = 45 (3 new cycles)
  5. Last = 14:23:50 (5 seconds later)
  6. VMs list refreshed (check for new VMs)
  7. Config refreshed (check for changes)
```

---

## ✨ Visual Features

### Gradient Buttons
```
Start (Green Gradient):    #10b981 → #059669
Stop (Red Gradient):       #ef4444 → #dc2626
Refresh (Blue Gradient):   #3b82f6 → #2563eb
```

### Card Styling
```
- Rounded corners (10px radius)
- White background (#fff)
- Subtle shadow (0 2px 8px rgba(0,0,0,0.1))
- Header divider line
- Hover effects on VM cards
```

### Text Hierarchy
```
Page title:     2em, bold
Card titles:    1.3em, bold
Labels:         0.9-1em, medium weight
Values:         0.9-1em, regular weight
Status badge:   0.85em, bold, colored
Activity log:   0.95em, monospace font
```

---

## 🎉 Complete Feature Set

✅ Real-time start/stop controls
✅ Live status display with color indicators
✅ VM discovery and monitoring
✅ Configuration display (masked sensitive data)
✅ Activity log with timestamps
✅ Auto-refresh every 2 seconds
✅ Responsive design (mobile to desktop)
✅ Error handling and user feedback
✅ Graceful button state management
✅ Navbar integration on all pages
✅ HTML escaping (XSS protection)
✅ Memory-efficient logging (max 50 entries)

---

**Ready to monitor!** 🚀📊
