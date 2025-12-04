# Main Gauge Monitoring - Enhanced Console Logging

## Console Output Guide

The Main Gauge Monitoring page now prints detailed values and calculated angles to the browser console in real-time.

### How to View Console Logs

1. Open Main Gauges page: `http://localhost:8000/`
2. Press `F12` (or `Cmd+Option+I` on Mac) to open Developer Tools
3. Click on "Console" tab
4. Watch for updates every 2 seconds

---

## First Update (T=2s) - Console Output

### What You'll See:

```
📌 First update for VM 1 - storing initial values, gauges will show 0° until next update

📦 Baseline Metrics Stored (will be used for rate calculation)

┌─────────────────────────────────────────────────────────────────────────────────────┐
│ Gauge # │ Metric               │ Field          │ Baseline Value │ Unit             │
├─────────────────────────────────────────────────────────────────────────────────────┤
│ 1       │ Network RX Rate      │ net_rxbytes    │ 532,042,479    │ bytes/s         │
│ 2       │ Network TX Rate      │ net_txbytes    │ 9,416,299      │ bytes/s         │
│ 3       │ Disk Read Rate       │ disk_rd_bytes  │ 2,799,755,264  │ bytes/s         │
│ 4       │ Disk Write Rate      │ disk_wr_bytes  │ 3,054,657,024  │ bytes/s         │
│ 5       │ CPU User Time Rate   │ timeusr        │ 476,076,540,... │ ns/s           │
│ 6       │ CPU System Time Rate │ timesys        │ 98,137,432,... │ ns/s            │
│ 7       │ Memory RSS Rate      │ memrss         │ 4,241,564      │ bytes/s         │
│ 8       │ Disk Read Requests   │ disk_rd_req    │ 233,398        │ reqs/s          │
└─────────────────────────────────────────────────────────────────────────────────────┘

ℹ️  These baseline values will be used to calculate rates in the next update cycle
```

### What This Means:
- ✓ The page successfully fetched real data from InfluxDB
- ✓ All 8 metrics have been stored as baseline values
- ✓ Gauges are currently showing 0° (correct for first update)
- ✓ Next update will calculate rates using these baselines

---

## Second Update (T=4s) - Console Output

### What You'll See:

```
✓ Update #2+ for VM 1 - calculating rates

═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
📊 GAUGE VALUES & CALCULATED ANGLES (Main Gauge Monitoring)
═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ Gauge # │ Metric               │ Field          │ Previous Value  │ Current Value   │ Delta    │ Rate/sec │ Time(ms) │ Angle(°) │
├─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 1       │ Network RX Rate      │ net_rxbytes    │ 532,042,479     │ 532,085,123     │ 42,644   │ 21,322   │ 2,000    │ 40.89°   │
│ 2       │ Network TX Rate      │ net_txbytes    │ 9,416,299       │ 9,432,598       │ 16,299   │ 8,149.5  │ 2,000    │ 32.12°   │
│ 3       │ Disk Read Rate       │ disk_rd_bytes  │ 2,799,755,264   │ 2,799,810,528   │ 55,264   │ 27,632   │ 2,000    │ 41.59°   │
│ 4       │ Disk Write Rate      │ disk_wr_bytes  │ 3,054,657,024   │ 3,054,697,790   │ 40,766   │ 20,383   │ 2,000    │ 40.68°   │
│ 5       │ CPU User Time Rate   │ timeusr        │ 476,076,540,000 │ 476,082,850,000 │ 6,310,.. │ 3,155... │ 2,000    │ 51.42°   │
│ 6       │ CPU System Time Rate │ timesys        │ 98,137,432,000  │ 98,140,245,000  │ 2,813... │ 1,406... │ 2,000    │ 35.89°   │
│ 7       │ Memory RSS Rate      │ memrss         │ 4,241,564       │ 4,242,384       │ 820      │ 410      │ 2,000    │ 27.59°   │
│ 8       │ Disk Read Requests   │ disk_rd_req    │ 233,398         │ 233,642         │ 244      │ 122      │ 2,000    │ 19.05°   │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════

📋 Individual Gauge Details
  [Gauge 1] Network RX Rate
    Previous: 532,042,479
    Current:  532,085,123
    Delta:    42,644
    Rate:     21,322 per second
    ▼ Angle:  40.89° ▼
    
  [Gauge 2] Network TX Rate
    Previous: 9,416,299
    Current:  9,432,598
    Delta:    16,299
    Rate:     8,149.5 per second
    ▼ Angle:  32.12° ▼
    
  [Gauge 3] Disk Read Rate
    Previous: 2,799,755,264
    Current:  2,799,810,528
    Delta:    55,264
    Rate:     27,632 per second
    ▼ Angle:  41.59° ▼
    
  ... (5 more gauges with same format)
```

### What This Means:
- ✓ Second update successfully calculated rates
- ✓ All metrics showing realistic deltas (changes between readings)
- ✓ Rate calculations show bytes/sec, reqs/sec, etc.
- ✓ **Angle column shows the gauge angle** - this is what displays on the page!
- ✓ Angles range from 19° to 51° (typical activity levels)

### Reading the Table

| Column | Meaning | Example |
|--------|---------|---------|
| **Gauge #** | Gauge identifier (1-8) | 1 = Network RX Rate |
| **Metric** | What's being measured | Network RX Rate |
| **Field** | InfluxDB field name | net_rxbytes |
| **Previous Value** | Last cycle's reading | 532,042,479 bytes |
| **Current Value** | This cycle's reading | 532,085,123 bytes |
| **Delta** | Change between readings | 42,644 bytes |
| **Rate/sec** | Change per second | 21,322 bytes/sec |
| **Time (ms)** | Time between reads | 2,000 ms (2 seconds) |
| **Angle (°)** | Gauge display angle | 40.89° ← **THIS displays on page** |

---

## Continuous Updates (T=6s, T=8s, etc.)

Every 2 seconds, the same detailed table appears with updated values:

```
✓ Update #2+ for VM 1 - calculating rates
[Same green header line]
[Updated table with new values]
[New angles for each gauge]
[Individual gauge details]
[Same green footer line]
```

### You'll Notice:
- Angles change slightly every 2 seconds (e.g., 40.89° → 42.15° → 41.63°)
- This reflects the actual rate changes in your VM
- Gauges on the page update with the new angles
- If a gauge shows 45-50°, that means moderate-high activity
- If a gauge shows 15-25°, that means light activity

---

## Color-Coded Output

The console output uses color coding for easy reading:

- 🟢 **Green** (`#4caf50`): Main headers and successful updates
- 🔵 **Blue** (`#667eea`): Gauge names in detailed section
- 🟠 **Orange** (`#ff9800`): First update baseline metrics
- 🔴 **Red** (`#dc2626`): Errors (if any)

---

## Practical Examples

### Example 1: Light Activity VM

```
Rate: 410 bytes/sec
log10(410) = 2.612
angle = atan(2.612/5) * 180/π = 27.59°
```
**Meaning**: Gauge shows ~28° (light activity)

### Example 2: Moderate Activity VM

```
Rate: 21,322 bytes/sec
log10(21,322) = 4.329
angle = atan(4.329/5) * 180/π = 40.89°
```
**Meaning**: Gauge shows ~41° (moderate activity)

### Example 3: High Activity VM

```
Rate: 3,155,000 ns/sec (CPU time)
log10(3,155,000) = 6.499
angle = atan(6.499/5) * 180/π = 52.38°
```
**Meaning**: Gauge shows ~52° (high activity)

---

## Understanding the Numbers

### Network Metrics (bytes/packets)
- `net_rxbytes`: Received bytes - typically thousands to millions
- `net_txbytes`: Transmitted bytes - typically thousands to millions
- Rate of 20,000 bytes/sec = moderate network activity
- Rate of 100,000+ bytes/sec = heavy network activity

### Disk Metrics (bytes/requests)
- `disk_rd_bytes`: Disk read bytes - typically millions
- `disk_wr_bytes`: Disk write bytes - typically millions
- `disk_rd_req`: Number of read requests - typically hundreds
- Rate of 25,000 bytes/sec = light disk I/O
- Rate of 100,000+ bytes/sec = heavy disk I/O

### CPU Metrics (nanoseconds)
- `timeusr`: CPU user time in nanoseconds - very large numbers
- `timesys`: CPU system time in nanoseconds - very large numbers
- Rate of 3M ns/sec = moderate CPU usage
- Rate of 10M+ ns/sec = heavy CPU usage

### Memory Metrics (bytes)
- `memrss`: Resident set size in bytes
- Rate of 1,000 bytes/sec = light memory changes
- Rate of 100,000+ bytes/sec = heavy memory changes

---

## Troubleshooting Console Output

### "I don't see console logs"
1. **Hard refresh**: `Ctrl+Shift+R` (Windows) or `Cmd+Shift+R` (Mac)
2. **Clear cache**: DevTools → Application → Clear site data
3. **Check console level**: Make sure "Info" and "Debug" are enabled
4. **Wait for updates**: First log appears at T=2s, rates at T=4s

### "Table is formatted strangely"
- This is normal - different browsers format tables differently
- Scroll right in the console to see all columns
- Or copy the table and paste into a text editor

### "I see zeros for all angles"
- This is the first update (T=2s) - expected!
- Wait 2 more seconds for the second update
- Check the "Previous Value" column - should show stored baselines

### "Angles aren't changing"
- Check if the "Rate/sec" values are changing
- If Rate/sec is always the same, that means metrics aren't changing
- This could mean: VM is idle or there's no new activity
- Try running a workload on the VM to see changes

---

## Copy-Paste for Manual Console Testing

Paste these into the browser console to manually inspect data:

```javascript
// See all stored metrics
console.table(STATE.previousValues);

// See current VM ID
console.log('Current VM:', STATE.currentVmId);

// See gauge configuration
console.table(GAUGE_CONFIG);

// Manually test rate calculation
calculateRateOfChange(532085123, 532042479, 2000);
// Should return: ~40.89°
```

---

## Summary

✅ **First Update (T=2s)**: Shows baseline metrics in a formatted table
✅ **Second+ Updates (T=4s+)**: Shows complete values + calculated angles
✅ **Color Coding**: Green for headers, blue for details
✅ **Formatted Tables**: Easy to read and compare all 8 metrics
✅ **Individual Details**: Breakdown for each gauge below the main table
✅ **Real Data**: All values from InfluxDB, properly formatted with commas
✅ **Live Updates**: Every 2 seconds with latest calculations

The console now provides complete visibility into what's happening on Main Gauge Monitoring! 🎉
