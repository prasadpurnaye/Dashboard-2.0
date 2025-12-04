# Main Gauges Dashboard - Debug Instructions

## Issue: Dropdown Not Populating & Data Verification

### Step-by-Step Debug Process

#### 1. Check Backend APIs

**Verify VMs are available:**
```bash
curl http://localhost:8000/api/telemetry/live-vms | python3 -m json.tool
```
Expected: Should show 2 VMs with IDs and names

**Verify real telemetry data (not random):**
```bash
# First call - note the values
curl http://localhost:8000/api/telemetry/vm-stats/1 | python3 -m json.tool | grep -E "net_rxbytes|disk_rd_bytes|timeusr"

# Wait 2 seconds, then call again
sleep 2
curl http://localhost:8000/api/telemetry/vm-stats/1 | python3 -m json.tool | grep -E "net_rxbytes|disk_rd_bytes|timeusr"
```
Expected: Values should change slightly (real data), NOT be random 0-90 values

#### 2. Check Frontend (Browser Console)

**Open the Main Gauges page:**
- Navigate to: `http://localhost:8000/`

**Open Browser Developer Tools:**
- Press `F12` (or Cmd+Option+I on Mac)
- Go to "Console" tab

**Look for initialization messages:**
You should see:
```
🚀 Initializing Main Gauges Dashboard...
📊 Creating 8 gauge charts...
  ✓ Gauge 1 created
  ✓ Gauge 2 created
  ... (8 total)
✓ VM dropdown found, attaching change listener
🔄 Fetching available VMs...
📋 Updating dropdown with 2 VMs
  Adding VM: one-82 (ID: 1)
  Adding VM: one-83 (ID: 2)
✓ Auto-selecting first VM: one-82
✓ Selected VM: 1
📊 Fetching telemetry from: /api/telemetry/vm-stats/1
✓ Received metrics for VM 1
  Real data verification - Sample values:
    net_rxbytes: 532042479 (expected: large number)
    disk_rd_bytes: 2799755264 (expected: large number)
    timeusr: 476076540000 (expected: large number)
```

#### 3. If Dropdown Not Showing VMs

**Check 1: Is the element visible?**
```javascript
// Paste in browser console:
document.getElementById('vm-dropdown')
```
Should return the dropdown element, NOT `null`

**Check 2: Are VMs being fetched?**
```javascript
// Paste in browser console:
console.log('STATE.vms:', STATE);
```
Should show:
```
STATE.vms: [
  { id: 1, name: "one-82", ... },
  { id: 2, name: "one-83", ... }
]
```

**Check 3: Is the API accessible?**
```javascript
// Paste in browser console:
fetch('/api/telemetry/live-vms').then(r => r.json()).then(d => console.log('VMs:', d.vms))
```
Should print the VMs list

#### 4. If Data Looks Random

**Check the telemetry values:**
```javascript
// Paste in browser console:
console.log('Current VM metrics:');
fetch('/api/telemetry/vm-stats/1').then(r => r.json()).then(d => {
  console.log('net_rxbytes:', d.metrics.net_rxbytes);
  console.log('disk_rd_bytes:', d.metrics.disk_rd_bytes);
  console.log('timeusr:', d.metrics.timeusr);
});
```

If values are:
- **Large numbers (millions+)**: Data is REAL ✓
- **Numbers between 0-90**: Data is RANDOM ✗

**Real data examples:**
- net_rxbytes: 532,042,479 bytes
- disk_rd_bytes: 2,799,755,264 bytes  
- timeusr: 476,076,540,000 nanoseconds

**Random data would be:** 23, 45, 67, 89 (0-90 range)

### Common Issues & Solutions

#### Issue: "vm-dropdown not found" error

**Solution:** Clear browser cache
1. Press Ctrl+Shift+Delete (or Cmd+Shift+Delete on Mac)
2. Select "Cached images and files"
3. Click "Clear data"
4. Reload the page

#### Issue: VMs loaded but dropdown empty

**Solution:** Check browser console for errors
1. Look for any errors in red
2. Check if `fetchAvailableVms()` is being called
3. Try manual fetch in console:
```javascript
fetch('/api/telemetry/live-vms').then(r => r.json()).then(d => console.log(d))
```

#### Issue: Gauges not updating

**Solution:** Verify periodic updates are running
1. Check console for "🔄 Periodic update tick..." messages (should appear every 2 sec)
2. Check if VM is selected: `console.log(STATE.currentVmId)`
3. Try manual fetch:
```javascript
fetch('/api/telemetry/vm-stats/1').then(r => r.json()).then(d => console.log('Metrics:', d.metrics))
```

#### Issue: Data appears random

**Solution:** Data is NOT random, it's REAL
1. The rate-of-change calculation converts large metric values to small angles (0-90°)
2. Example: net_rxbytes of 532,042,479 → rate-of-change angle ≈ 45°
3. This is correct behavior! The gauges show rates, not absolute values.

To verify data is real:
```javascript
// Check raw metric values (should be large numbers)
fetch('/api/telemetry/vm-stats/1').then(r => r.json()).then(d => {
  console.log('Raw metrics (should be LARGE numbers):');
  console.table(d.metrics);
});
```

### Manual Testing in Console

**Test dropdown population:**
```javascript
// Clear and repopulate
STATE.vms = [];
fetchAvailableVms();
```

**Test gauge update:**
```javascript
// Select a VM and force update
STATE.currentVmId = 1;
initializePreviousValues(1);
fetchAndUpdateGauges();
```

**Test rate calculation:**
```javascript
// Manually test the rate formula
const rate1 = calculateRateOfChange(100, 50, 1000);  // +50 per second
console.log('Rate of +50/sec:', rate1, '°');  // Should be around 3-4°

const rate2 = calculateRateOfChange(1000, 0, 1000);  // +1000 per second
console.log('Rate of +1000/sec:', rate2, '°');  // Should be around 45°

const rate3 = calculateRateOfChange(1000000, 0, 1000);  // +1M per second
console.log('Rate of +1M/sec:', rate3, '°');  // Should be close to 90°
```

### Expected Console Output

When page loads successfully:
```
🚀 Initializing Main Gauges Dashboard...
📊 Creating 8 gauge charts...
  ✓ Gauge 1 created
  ✓ Gauge 2 created
  ✓ Gauge 3 created
  ✓ Gauge 4 created
  ✓ Gauge 5 created
  ✓ Gauge 6 created
  ✓ Gauge 7 created
  ✓ Gauge 8 created
✓ VM dropdown found, attaching change listener
🔄 Fetching available VMs...
🔍 Fetching available VMs from /api/telemetry/live-vms...
✓ API Response: 2 VMs received Array(2)
📋 Updating dropdown with 2 VMs
  Adding VM: one-82 (ID: 1)
  Adding VM: one-83 (ID: 2)
✓ Auto-selecting first VM: one-82
✓ Selected VM: 1
✓ Main Gauges Dashboard initialized
⏱️ Starting periodic updates every 2 seconds...
📊 Fetching telemetry from: /api/telemetry/vm-stats/1
✓ Received metrics for VM 1
  Real data verification - Sample values:
    net_rxbytes: 532042479 (expected: large number)
    disk_rd_bytes: 2799755264 (expected: large number)
    timeusr: 476076540000 (expected: large number)
🔄 Periodic update tick...
📊 Fetching telemetry from: /api/telemetry/vm-stats/1
...
```

### Network Tab Verification

1. Open DevTools → "Network" tab
2. Reload page
3. Filter by "XHR" (XMLHttpRequest)
4. You should see:
   - `live-vms` request → 200 OK
   - `vm-stats/1` requests every 2 seconds → 200 OK
5. Click each request to see response data

### Hard Reset Steps

If everything seems broken:

1. **Hard refresh browser:**
   - Windows/Linux: Ctrl+Shift+R
   - Mac: Cmd+Shift+R

2. **Clear all cache:**
   - DevTools → Application → Clear site data

3. **Restart server:**
   ```bash
   pkill -f uvicorn
   cd /home/r/Dashboard2.0/dashboard-2.0
   source .venv/bin/activate
   INFLUX_TOKEN="apiv3_LNeKzeLNyQqZAFJiVPN96OUVtjeYsdJURAGDXwi3rq5NZCPfpTpbzr0C096s9m9-nyeE60EkjjuPh8lC_lJnpg" \
   python3 -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
   ```

4. **Visit fresh URL:**
   - `http://localhost:8000/?cachebust=` + timestamp

---

## Summary Checklist

- [ ] VMs appear in dropdown
- [ ] First VM is auto-selected
- [ ] Gauges show angles (0-90°)
- [ ] Angles update every 2 seconds
- [ ] Metric values are large numbers (millions+), not small (0-90)
- [ ] Console shows detailed logs with checkmarks
- [ ] No red error messages in console

If all checkmarks are true, the dashboard is working correctly!
