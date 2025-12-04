# Main Gauges Dashboard - Timeline & Rate Explanation

## Update Timeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     MAIN GAUGES PAGE LIFECYCLE                             │
└─────────────────────────────────────────────────────────────────────────────┘

T=0s    PAGE LOADS
        ┌─────────────────────────────────────┐
        │ 🚀 Initialize Dashboard             │
        │ • Create 8 gauge charts             │
        │ • Fetch available VMs               │
        │ • Populate dropdown                 │
        │ • Auto-select VM 1                  │
        └─────────────────────────────────────┘
                        ↓
        VMs: [one-82, one-83] ✓
        Dropdown: one-82 selected ✓
        Gauges: All at 0° (initialization) ✓


T=2s    FIRST PERIODIC UPDATE (Phase 1)
        ┌─────────────────────────────────────┐
        │ 📊 Fetch Telemetry for VM 1         │
        │ GET /api/telemetry/vm-stats/1       │
        └─────────────────────────────────────┘
                        ↓
        ┌─────────────────────────────────────┐
        │ Metrics Received:                   │
        │ • net_rxbytes: 532,000,000          │
        │ • disk_rd_bytes: 2,799,700,000      │
        │ • timeusr: 476,070,000,000          │
        │ • ... (26 metrics total)            │
        └─────────────────────────────────────┘
                        ↓
        ┌─────────────────────────────────────┐
        │ 📌 FIRST UPDATE - PHASE 1           │
        │ • Store baseline values             │
        │ • NO previous values to compare     │
        │ • Set all gauges to 0°              │
        │ • Save metrics for next cycle       │
        └─────────────────────────────────────┘
                        ↓
        Console Output:
        "📌 First update for VM 1 - storing 
         initial values, gauges will show 0° 
         until next update"
        
        Display: All gauges show 0° ✓


T=4s    SECOND PERIODIC UPDATE (Phase 2)
        ┌─────────────────────────────────────┐
        │ 📊 Fetch Telemetry for VM 1         │
        │ GET /api/telemetry/vm-stats/1       │
        └─────────────────────────────────────┘
                        ↓
        ┌─────────────────────────────────────┐
        │ Metrics Received:                   │
        │ • net_rxbytes: 532,042,479 ← NEW   │
        │ • disk_rd_bytes: 2,799,755,264 ←  │
        │ • timeusr: 476,076,540,000 ←       │
        │ • ... (all slightly different)      │
        └─────────────────────────────────────┘
                        ↓
        ┌─────────────────────────────────────┐
        │ ✓ UPDATE #2+ - PHASE 2              │
        │ • HAVE previous values (from T=2s)  │
        │ • Calculate rate-of-change angles   │
        │ • For each metric:                  │
        │   delta = new - previous            │
        │   rate = delta / 2 seconds          │
        │   angle = atan(log10(rate)/5)      │
        │ • Display real angles on gauges    │
        │ • Save current for next cycle       │
        └─────────────────────────────────────┘
                        ↓
        Console Output:
        "✓ Update #2+ for VM 1 - calculating rates"
        "Gauge 1: current=532042479, previous=532000000,
         delta=42479, time=2000ms, angle=40.87°"
        "Gauge 2: current=9416299, previous=9400000,
         delta=16299, time=2000ms, angle=32.14°"
        ... [more gauges]
        
        Display: Gauges show real angles ✓
        Example values: 25°, 40°, 35°, 22°, 18°, 31°, 15°, 28°


T=6s    THIRD PERIODIC UPDATE (Phase 2)
        ┌─────────────────────────────────────┐
        │ 📊 Fetch Telemetry for VM 1         │
        │ GET /api/telemetry/vm-stats/1       │
        └─────────────────────────────────────┘
                        ↓
        ┌─────────────────────────────────────┐
        │ ✓ UPDATE #2+ - PHASE 2 (repeat)     │
        │ • Calculate new rates               │
        │ • Display updated angles            │
        └─────────────────────────────────────┘
                        ↓
        Display: Gauges update with new angles ✓
        Example values: 28°, 42°, 31°, 25°, 21°, 35°, 18°, 32°


T=8s+   CONTINUOUS UPDATES
        ┌─────────────────────────────────────┐
        │ ✓ Updates continue every 2 seconds   │
        │ • Fresh metrics fetched             │
        │ • Rates recalculated                │
        │ • Angles displayed                  │
        │ • Values stored for next cycle      │
        └─────────────────────────────────────┘
                        ↓
        Display: Gauges show live rate changes ✓
```

---

## Rate Calculation Formula Explained

### Problem
Raw metric values are HUGE (millions/billions). Simple rate calculation maxes out gauge:

```
Example: Network bytes changing by 50,000 in 2 seconds
rate = 50,000 / 2 = 25,000 bytes/sec
angle = atan(25,000) radians = 1.5321 rad
angle_degrees = 1.5321 * 180/π ≈ 87.7°  ← TOO HIGH!

Example 2: CPU time changing by 6,500,000,000 in 2 seconds
rate = 6,500,000,000 / 2 = 3,250,000,000 ns/sec
angle = atan(3,250,000,000) ≈ 1.5708 rad = 89.9°  ← MAXED OUT!
```

### Solution: Log-Scaled Formula

```javascript
// For Network bytes: 532M → 532.04M (delta ~42K) in 2 sec
rate = 42,000 / 2 = 21,000 bytes/sec

logRate = log10(21,000) = 4.322
angle = atan(4.322 / 5) * 180/π
      = atan(0.8644) * 180/π
      = 0.713 * 180/π
      = 40.87°  ← GOOD! Leaves room for variation
```

### Visual Mapping

```
0°           = No activity (δ = 0)
5°-15°       = Very light activity (δ < 1K/sec)
15°-30°      = Light activity (δ = 1K-10K/sec)
30°-50°      = Moderate activity (δ = 10K-100K/sec)
50°-70°      = Heavy activity (δ = 100K-1M/sec)
70°-90°      = Very heavy activity (δ > 1M/sec)
```

---

## Rate Examples (with log-scaled formula)

### Network RX Bytes
```
Previous: 532,000,000 bytes
Current:  532,042,479 bytes
Delta:    42,479 bytes
Time:     2 seconds
Rate:     21,239.5 bytes/sec

log10(21,239.5) = 4.327
angle = atan(4.327/5) * 180/π = 40.91°

Interpretation: Light-to-moderate network activity
```

### Disk Read Bytes
```
Previous: 2,799,700,000 bytes
Current:  2,799,755,264 bytes
Delta:    55,264 bytes
Time:     2 seconds
Rate:     27,632 bytes/sec

log10(27,632) = 4.441
angle = atan(4.441/5) * 180/π = 41.54°

Interpretation: Light-to-moderate disk read activity
```

### CPU User Time
```
Previous: 476,070,000,000 ns
Current:  476,076,540,000 ns
Delta:    6,540,000 ns
Time:     2 seconds
Rate:     3,270,000 ns/sec

log10(3,270,000) = 6.514
angle = atan(6.514/5) * 180/π = 52.59°

Interpretation: Moderate-to-heavy CPU usage
```

### Idle VM (very low activity)
```
Previous: 100,000,000 bytes
Current:  100,001,000 bytes
Delta:    1,000 bytes
Time:     2 seconds
Rate:     500 bytes/sec

log10(500) = 2.699
angle = atan(2.699/5) * 180/π = 28.44°

Interpretation: Light activity (idle VM)
```

### Busy VM (high activity)
```
Previous: 500,000,000 bytes
Current:  1,000,000,000 bytes
Delta:    500,000,000 bytes (500MB!)
Time:     2 seconds
Rate:     250,000,000 bytes/sec

log10(250,000,000) = 8.398
angle = atan(8.398/5) * 180/π = 59.31°

Interpretation: Very heavy activity (busy VM)
```

---

## First Update Problem (Before Fix)

```
T=2s: First fetch
├─ previousValue = UNDEFINED
├─ currentValue = 532,000,000
├─ calculateRateOfChange(532,000,000, UNDEFINED, 2000)
├─ Returns 0 (because previousValue === undefined)
└─ All gauges show 0°  ✗ WRONG!
   (User sees: "Why are all gauges 0°?")

T=4s: Second fetch
├─ previousValue = 532,000,000  (from T=2s)
├─ currentValue = 532,042,479
├─ calculateRateOfChange(532,042,479, 532,000,000, 2000)
├─ Calculates real rate = 40.87°
└─ Gauges update!  ✓ NOW WORKING
   (User finally sees angles and understands it's alive)
```

---

## Two-Phase Solution (After Fix)

```
T=2s: FIRST UPDATE (Phase 1)
├─ Fetch metrics: net_rxbytes=532,000,000, etc.
├─ previousValues[VM1] = EMPTY (no previous data)
├─ isFirstUpdate = true
├─ Action: Store metrics as baseline
├─ Set all gauges to 0°
├─ Display: "📌 First update - storing initial values"
└─ Result: User sees 0° (correct - no previous data to compare)

T=4s: SECOND UPDATE (Phase 2+)
├─ Fetch metrics: net_rxbytes=532,042,479, etc.
├─ previousValues[VM1] = HAS data (from T=2s)
├─ isFirstUpdate = false
├─ Action: Calculate rates using previous values
├─ For each metric: rate = (current - previous) / 2 seconds
├─ Display: "✓ Update #2+ - calculating rates"
├─ Result: Gauges show real angles (40°, 32°, 41°, etc.)  ✓

T=6s: THIRD UPDATE (Phase 2+)
├─ Fetch metrics: net_rxbytes=532,055,000, etc.
├─ previousValues[VM1] = HAS data (from T=4s)
├─ isFirstUpdate = false
├─ Action: Calculate NEW rates
├─ Display: Updated angles based on latest delta
└─ Result: Gauges show updated angles  ✓
```

---

## Visual Gauge Display

### Gauge Appearance (180° semicircle)
```
                    0°
                   ╱╲
                  ╱  ╲
                 ╱    ╲
            45° ╱      ╲ 45°
               ╱        ╲
              ╱          ╲
             ╱            ╲
            ╱              ╲
           ╱                ╲
          ╱                  ╲
       90° ─────────────────── 90°
```

### Example Display States

#### T=2s (First Update)
```
Gauge 1: 0°        Gauge 5: 0°
  [═]                 [═]
Gauge 2: 0°        Gauge 6: 0°
  [═]                 [═]
Gauge 3: 0°        Gauge 7: 0°
  [═]                 [═]
Gauge 4: 0°        Gauge 8: 0°
  [═]                 [═]
```

#### T=4s (Second Update - NOW SHOWING RATES!)
```
Gauge 1: 40.87°    Gauge 5: 18.22°
  [════════╱]        [════╱]
Gauge 2: 32.14°    Gauge 6: 31.45°
  [══════╱]          [═══════╱]
Gauge 3: 41.61°    Gauge 7: 15.89°
  [════════╱]        [═══╱]
Gauge 4: 22.35°    Gauge 8: 28.92°
  [═════╱]           [═══════╱]
```

#### T=6s (Third Update - LIVE UPDATES!)
```
Gauge 1: 42.51°    Gauge 5: 19.45°
  [═════════╱]       [═════╱]
Gauge 2: 35.22°    Gauge 6: 33.78°
  [══════════╱]      [████████╱]
Gauge 3: 39.88°    Gauge 7: 14.23°
  [═════════╱]       [═══╱]
Gauge 4: 25.67°    Gauge 8: 31.56°
  [██████╱]          [████████╱]
```

---

## Console Output Visualization

```
┌─ FIRST PAGE LOAD ─────────────────────────────────┐
│                                                     │
│ 🚀 Initializing Main Gauges Dashboard...          │
│ 📊 Creating 8 gauge charts...                     │
│   ✓ Gauge 1 created                              │
│   ... (7 more)                                    │
│ ✓ VM dropdown found, attaching listener          │
│ 🔄 Fetching available VMs...                     │
│ ✓ API Response: 2 VMs received                   │
│ 📋 Updating dropdown with 2 VMs                  │
│   Adding VM: one-82 (ID: 1)                      │
│   Adding VM: one-83 (ID: 2)                      │
│ ✓ Auto-selecting first VM: one-82                │
│ ✓ Selected VM: 1                                 │
│ ✓ Main Gauges Dashboard initialized              │
│ ⏱️  Starting periodic updates every 2 seconds...  │
│                                                     │
└───────────────────────────────────────────────────┘

[2 seconds later - T=2s]

┌─ FIRST UPDATE (PHASE 1) ──────────────────────────┐
│                                                     │
│ 🔄 Periodic update tick...                        │
│ 📊 Fetching telemetry from: /api/telemetry/...   │
│ ✓ Received metrics for VM 1                       │
│   Real data verification - Sample values:         │
│     net_rxbytes: 532042479 (expected: large)     │
│     disk_rd_bytes: 2799755264 (expected: large)  │
│     timeusr: 476076540000 (expected: large)      │
│ 📌 First update for VM 1 - storing initial       │
│    values, gauges will show 0° until next update │
│                                                     │
└───────────────────────────────────────────────────┘

[2 seconds later - T=4s]

┌─ SECOND UPDATE (PHASE 2) ─────────────────────────┐
│                                                     │
│ 🔄 Periodic update tick...                        │
│ 📊 Fetching telemetry from: /api/telemetry/...   │
│ ✓ Received metrics for VM 1                       │
│   Real data verification - Sample values:         │
│     net_rxbytes: 532042479 ← Same as before      │
│     disk_rd_bytes: 2799755264 ← Changed slightly  │
│     timeusr: 476076540000 ← Changed slightly      │
│ ✓ Update #2+ for VM 1 - calculating rates        │
│ Gauge 1 (Network RX Rate): current=532042479,   │
│   previous=532000000, delta=42479, time=2000ms,  │
│   angle=40.87°                                   │
│ Gauge 2 (Network TX Rate): current=9416299,     │
│   previous=9400000, delta=16299, time=2000ms,    │
│   angle=32.14°                                   │
│ Gauge 3 (Disk Read Rate): current=2799755264,   │
│   previous=2799700000, delta=55264, ...         │
│   angle=41.61°                                   │
│ ... (5 more gauges)                              │
│                                                     │
└───────────────────────────────────────────────────┘

[Repeats every 2 seconds with new values]
```

---

## Summary

✓ **First Update**: Establishes baseline (0° display)
✓ **Second+ Updates**: Calculates real rates (non-zero angles)
✓ **Log Formula**: Scales huge values to 0-90° range nicely
✓ **Data**: Real InfluxDB telemetry (millions/billions bytes)
✓ **Display**: Live updating every 2 seconds
