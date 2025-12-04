# Main Gauges - Fix Summary

## Problem
All gauges on Main Gauge Monitoring page were showing 0° because:
1. On first data fetch, there's no previous value to compare against
2. Rate-of-change calculation needs two data points to work
3. All rates were 0 because: `calculateRateOfChange(newValue, undefined, timeDelta)` returns 0

## Solution Implemented

### 1. **Two-Phase Update Logic**
- **Phase 1 (First Update)**: Fetch metrics and store them, show 0° on all gauges
- **Phase 2+ (Subsequent Updates)**: Calculate and display rate-of-change angles

```javascript
const isFirstUpdate = Object.keys(STATE.previousValues[STATE.currentVmId] || {}).length === 0;

if (isFirstUpdate) {
    // Store initial values, don't calculate rates yet
    storePreviousValues(STATE.currentVmId, metrics);
    // Set all gauges to 0° 
    for (let i = 1; i <= 8; i++) {
        updateGaugeChart(i, 0);
    }
} else {
    // Calculate and display rates starting from 2nd update
    // ... rate calculations here ...
    storePreviousValues(STATE.currentVmId, metrics);
}
```

### 2. **Improved Rate Calculation Formula**

**Old formula** (didn't work well with large values):
```javascript
rate = valueDelta / timeDeltaSeconds
angle = atan(rate) * 180 / π  // atan(millions) ≈ 90°
```

**New formula** (log-scaled for better distribution):
```javascript
rate = valueDelta / timeDeltaSeconds              // e.g., 50,000 bytes/sec
logRate = log10(rate)                             // e.g., log10(50000) ≈ 4.7
angle = atan(logRate / 5) * 180 / π              // Gives 30-60° for typical activity
```

**Why log scaling?**
- Network metrics change by thousands/millions per second
- Without scaling, atan(1,000,000) ≈ 90° (stays maxed out)
- With log10 scaling: log10(1,000,000) = 6, then atan(6/5) ≈ 50°
- This gives better visual distribution across 0-90° range

### 3. **Rate Examples** (for 2-second update interval)

| Scenario | Delta | Rate/sec | Log10 | Angle |
|----------|-------|----------|-------|-------|
| Very low (5 bytes) | 5 | 2.5 | 0.40 | 4.6° |
| Low (820 bytes) | 820 | 410 | 2.61 | 27.6° |
| Medium (42KB) | 42,000 | 21,000 | 4.32 | 40.9° |
| High (500MB) | 500M | 250M | 8.40 | 59.2° |
| Very high (1B+) | 1B+ | 500M+ | 8.70+ | 65-90° |

## Expected Behavior After Fix

### First page load (Timeline)
```
T=0s:  Dropdown populates with VMs
       VM 1 auto-selected
       All gauges show 0°

T=2s:  First periodic update
       Metrics fetched
       Still 0° (no previous values to compare)
       Previous values stored for next update

T=4s:  Second periodic update
       Metrics fetched
       Rate-of-change calculated using previous values
       Gauges show real rate angles (e.g., 25°, 41°, 38°, etc.)

T=6s+: Subsequent updates
       Continue updating rates every 2 seconds
       Angles reflect how fast metrics are changing
```

### Console logs

When you open browser console (F12 → Console tab), you'll see:

```
🚀 Initializing Main Gauges Dashboard...
📊 Creating 8 gauge charts...
  ✓ Gauge 1 created
  [... gauges 2-8 ...]
✓ VM dropdown found, attaching change listener
🔄 Fetching available VMs...
✓ API Response: 2 VMs received
📋 Updating dropdown with 2 VMs
  Adding VM: one-82 (ID: 1)
  Adding VM: one-83 (ID: 2)
✓ Auto-selecting first VM: one-82
✓ Selected VM: 1
✓ Main Gauges Dashboard initialized
📊 Fetching telemetry from: /api/telemetry/vm-stats/1
✓ Received metrics for VM 1
  Real data verification - Sample values:
    net_rxbytes: 532042479 (expected: large number)
    disk_rd_bytes: 2799755264 (expected: large number)
    timeusr: 476076540000 (expected: large number)
📌 First update for VM 1 - storing initial values, gauges will show 0° until next update
🔄 Periodic update tick...
📊 Fetching telemetry from: /api/telemetry/vm-stats/1
✓ Received metrics for VM 1
✓ Update #2+ for VM 1 - calculating rates
Gauge 1 (Network RX Rate): current=532042479, previous=532000000, delta=42479, time=2000ms, angle=40.87°
Gauge 2 (Network TX Rate): current=9416299, previous=9400000, delta=16299, time=2000ms, angle=32.14°
... (more gauge updates with angles)
```

## Files Modified

- `/static/js/dashboard.js`
  - Updated `calculateRateOfChange()` with log-scaled formula
  - Updated `fetchAndUpdateGauges()` to handle first vs subsequent updates
  - Enhanced console logging for debugging

## Testing

### Manual Test 1: Verify two-phase behavior
1. Open Main Gauges page
2. Check console - should see "First update" message at T=2s
3. Wait for next update (T=4s)
4. Should see non-zero angles and "Update #2+ for VM" message

### Manual Test 2: Verify rate values
```javascript
// In browser console:
calculateRateOfChange(532042479, 532000000, 2000)  // Should give ~41°
calculateRateOfChange(100, 95, 2000)                // Should give ~5°
calculateRateOfChange(1000000000, 500000000, 2000) // Should give ~59°
```

### Manual Test 3: Verify real data
```javascript
// In browser console - check raw metric values:
fetch('/api/telemetry/vm-stats/1')
  .then(r => r.json())
  .then(d => console.table(d.metrics))
```
Should show large realistic numbers, not small 0-90 values

## Related Files

- Documentation: `/MAIN_GAUGES_REFACTOR.md`
- Debug Guide: `/DEBUG_INSTRUCTIONS.md`

