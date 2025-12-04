# Telemetry Module Enhancement - Missing Parameters Analysis

**Date:** November 13, 2025  
**Comparison:** `getStats6remoteWithInflux.py` vs Current `src/telemetry/collector.py`  
**Status:** Enhancement Recommended

---

## Executive Summary

The `getStats6remoteWithInflux.py` reference script captures **additional measurements and parameters** not currently collected by the Dashboard 2.0 telemetry module. This document details the gaps and provides implementation guidance.

---

## Missing InfluxDB3 Measurements

### Current Measurements (Dashboard 2.0)
1. ✅ `vm_metrics` - Basic VM state
2. ✅ `vm_features` - Derived metrics (memory rate, angle)

### Additional Measurements in Reference Script
3. ❌ `vm_devices` - Per-device network and disk I/O statistics
4. ❌ `vm_totals` - Comprehensive VM totals with extended memory metrics

---

## Detailed Comparison

### Measurement 1: vm_metrics (CURRENT ✅)

**Current Implementation:**
```python
Fields captured:
  - state: VM state
  - cpu_count: vCPU count
  - memory_max_kb: Max memory
  - memory_used_kb: Used memory
  - cputime_ns: CPU time
```

**Status:** ✅ Exists

---

### Measurement 2: vm_features (CURRENT ✅)

**Current Implementation:**
```python
Fields captured:
  - memory_rate_kb_per_sec: Memory change rate
  - memory_angle_deg: Memory trend angle
```

**Status:** ✅ Exists

---

### Measurement 3: vm_devices (MISSING ❌)

**Tags:**
- `VMID` - VM ID
- `UUID` - VM UUID
- `Dom` - VM name
- `devtype` - Device type ("nic" or "disk")
- `device` - Device name (eth0, vda, etc.)

**Fields - Network Interface (devtype=nic):**
```
rxbytes      (integer) - Received bytes
rxpackets    (integer) - Received packets
rxerrors     (integer) - Receive errors
rxdrops      (integer) - Dropped packets (RX)
txbytes      (integer) - Transmitted bytes
txpackets    (integer) - Transmitted packets
txerrors     (integer) - Transmit errors
txdrops      (integer) - Dropped packets (TX)
```

**Fields - Block Device (devtype=disk):**
```
rd_req       (integer) - Read requests
rd_bytes     (integer) - Bytes read
wr_reqs      (integer) - Write requests
wr_bytes     (integer) - Bytes written
errors       (integer) - I/O errors
```

**Example Data Points:**
- One line per NIC (includes totals aggregated separately)
- One line per disk
- Separate aggregated totals in `vm_totals`

**Status:** ❌ **MISSING** - Needs implementation

---

### Measurement 4: vm_totals (MISSING ❌)

**Tags:**
- `VMID` - VM ID
- `UUID` - VM UUID
- `Dom` - VM name

**Fields - Network Aggregates:**
```
net_rxbytes      (integer) - Total received bytes
net_rxpackets    (integer) - Total received packets
net_rxerrors     (integer) - Total receive errors
net_rxdrops      (integer) - Total dropped RX packets
net_txbytes      (integer) - Total transmitted bytes
net_txpackets    (integer) - Total transmitted packets
net_txerrors     (integer) - Total transmit errors
net_txdrops      (integer) - Total dropped TX packets
```

**Fields - CPU/Core Metrics:**
```
state        (integer) - VM state code (1=running, 2=paused, etc.)
cpus         (integer) - Number of vCPUs
cputime      (integer) - Total CPU time (ns)
timeusr      (integer) - CPU time in user mode (ns)
timesys      (integer) - CPU time in system mode (ns)
```

**Fields - Memory Extended:**
```
memactual      (integer) - Actual memory in use (KB)
memrss         (integer) - RSS (Resident Set Size)
memavailable   (integer) - Available memory (KB)
memusable      (integer) - Usable memory (KB)
memswap_in     (integer) - Memory swapped in
memswap_out    (integer) - Memory swapped out
memmajor_fault (integer) - Major page faults
memminor_fault (integer) - Minor page faults
memdisk_cache  (integer) - Disk cache memory (KB)
```

**Status:** ❌ **MISSING** - Needs implementation

---

## Key Differences Summary

| Feature | Current | Reference | Status |
|---------|---------|-----------|--------|
| **Basic VM Metrics** | ✅ | ✅ | Aligned |
| **Per-Device Metrics** | ❌ | ✅ | Gap |
| **Aggregated Totals** | ✅ | ✅ | Aligned |
| **Network I/O Details** | ❌ | ✅ | Gap |
| **Disk I/O Details** | ❌ | ✅ | Gap |
| **Extended Memory** | ⚠️ Partial | ✅ | Gap |
| **CPU Breakdown** | ✅ | ✅ | Aligned |
| **Device Caching** | ❌ | ✅ | Gap |

---

## Data Collection Flow Comparison

### Current Flow (Simplified)
```
KVM Connector
    ↓
VM Metrics (basic state)
    ↓
vm_metrics measurement
    ↓
vm_features (derived)
```

### Enhanced Flow (Reference Script)
```
KVM Connector
    ↓
    ├─→ VM Basic Metrics → vm_metrics
    │
    ├─→ Network Stats (per-device) → vm_devices (nic)
    │
    ├─→ Disk I/O Stats (per-device) → vm_devices (disk)
    │
    └─→ Aggregated Totals → vm_totals
         (includes extended memory, CPU breakdown)
    
    ↓
vm_features (derived from totals)
```

---

## Missing Implementation Details

### 1. Device Discovery

**Current Gap:** No per-device metrics collection

**Reference Approach:**
```python
# XML-based device extraction
def _extract_devices_from_xml(dom) -> Tuple[List[str], List[str]]:
    root = ET.fromstring(dom.XMLDesc(0))
    nics, disks = [], []
    # Parse XML for interface and disk device names
    return nics, disks

# Device caching (300 seconds)
_device_cache: Dict[int, Dict[str, Any]] = {}
```

**Recommendation:** Implement device discovery + caching

---

### 2. Network Interface Statistics

**Current Gap:** No per-interface metrics

**Reference Data:**
```python
For each NIC interface:
  - rx.bytes, rx.packets, rx.errors, rx.drops
  - tx.bytes, tx.packets, tx.errors, tx.drops
  
Collected via:
  dom.interfaceStats(nic_name)
```

**Recommendation:** Add per-NIC metrics collection

---

### 3. Block Device (Disk) Statistics

**Current Gap:** No per-disk metrics

**Reference Data:**
```python
For each block device:
  - rd.requests, rd.bytes
  - wr.requests, wr.bytes
  - errors
  
Collected via:
  dom.blockStats(disk_name)
```

**Recommendation:** Add per-disk I/O collection

---

### 4. Extended Memory Metrics

**Current Gap:** Limited memory data

**Missing Memory Fields:**
- `balloon.actual` - Actual memory usage
- `balloon.rss` - Resident set size
- `balloon.available` - Available memory
- `balloon.usable` - Usable memory
- `balloon.swap_in/out` - Swap activity
- `balloon.major_fault/minor_fault` - Page faults
- `balloon.disk_caches` - Disk cache

**Reference Collection:**
```python
mem_fields = dom.memoryStats()
# Returns dict with all above keys
```

**Recommendation:** Expand memory field collection

---

### 5. CPU Mode Breakdown

**Current Gap:** No user vs system time separation

**Missing CPU Fields:**
- `cpu.user` - Time in user mode
- `cpu.system` - Time in system mode

**Reference Collection:**
```python
Via memoryStats() and domstats:
  - timeusr = data.get("cpu.user", 0)
  - timesys = data.get("cpu.system", 0)
```

**Recommendation:** Add CPU mode breakdown

---

## Implementation Roadmap

### Phase 1: Device Infrastructure (Priority: HIGH)

**Tasks:**
1. ✅ Create XML device parser
2. ✅ Implement device cache with TTL
3. ✅ Add device discovery to KVM connector

**Estimated Lines:** ~50-80 LOC

**Impact:** Enables per-device metrics

---

### Phase 2: Network Metrics (Priority: HIGH)

**Tasks:**
1. ✅ Extract per-device interface stats
2. ✅ Aggregate network totals
3. ✅ Create `vm_devices` measurement (nic)

**Estimated Lines:** ~100-150 LOC

**Impact:** Detailed network I/O visibility

---

### Phase 3: Disk Metrics (Priority: HIGH)

**Tasks:**
1. ✅ Extract per-device block stats
2. ✅ Aggregate disk totals
3. ✅ Create `vm_devices` measurement (disk)

**Estimated Lines:** ~80-120 LOC

**Impact:** Detailed storage I/O visibility

---

### Phase 4: Extended Memory (Priority: MEDIUM)

**Tasks:**
1. ✅ Expand memory field collection
2. ✅ Add to `vm_totals` measurement

**Estimated Lines:** ~20-30 LOC

**Impact:** Better memory analysis

---

### Phase 5: CPU Breakdown (Priority: MEDIUM)

**Tasks:**
1. ✅ Extract user/system CPU time
2. ✅ Add to `vm_totals` measurement

**Estimated Lines:** ~10-20 LOC

**Impact:** CPU mode visibility

---

## Data Volume Impact

### Current Collection (10 VMs)
```
Per cycle (5 sec):
  - vm_metrics: 10 lines
  - vm_features: 10 lines
  Total: ~20 lines
  
Daily: ~345,600 lines
Monthly: ~10.4M lines
Daily Storage: ~12-25 MB
```

### Enhanced Collection (10 VMs, 2 NICs, 3 disks each)
```
Per cycle (5 sec):
  - vm_metrics: 10 lines (unchanged)
  - vm_devices (NICs): 20 lines (2 per VM)
  - vm_devices (disks): 30 lines (3 per VM)
  - vm_totals: 10 lines (aggregates)
  - vm_features: 10 lines (unchanged)
  Total: ~80 lines per cycle
  
Daily: ~1.38M lines (~4x increase)
Monthly: ~41.5M lines (~4x increase)
Daily Storage: ~50-100 MB (~4x increase)
```

### Storage Considerations
- **4x increase in data volume** but still manageable
- **Recommended:** Configure retention policy
- **Indexing:** Use tags wisely (VMID, devtype most useful)
- **Compression:** InfluxDB3 handles automatically

---

## Backward Compatibility

✅ **Fully Backward Compatible**

- Existing `vm_metrics` measurement unchanged
- Existing `vm_features` measurement unchanged
- New measurements (`vm_devices`, `vm_totals`) are additive
- No breaking changes to API or queries
- Dashboard can ignore new measurements initially

---

## Implementation Considerations

### 1. Fallback Handling

Reference script includes fallback path when domstats unavailable:
```python
# Try modern domstats first
domstats = conn.getAllDomainStats(DOM_STATS, STAT_FLAGS)

# Fallback to legacy API if needed
if not domstats:
    # Use legacy dom.info(), dom.interfaceStats(), dom.blockStats()
```

**Recommendation:** Implement similar fallback

---

### 2. Device Caching

Reference uses 300-second TTL for device lists:
```python
DEVICE_CACHE_TTL = 300  # seconds
_device_cache: Dict[int, Dict[str, Any]] = {}
```

**Benefit:** Avoids expensive XML parsing on every cycle

**Recommendation:** Implement caching

---

### 3. Error Handling

Reference handles per-device failures gracefully:
```python
try:
    rxB, rxP, rxE, rxD, txB, txP, txE, txD = dom.interfaceStats(nic)
except libvirt.libvirtError:
    rxB=rxP=rxE=rxD=txB=txP=txE=txD=0
```

**Benefit:** Single device failure doesn't stop collection

**Recommendation:** Add per-device error handling

---

### 4. Field Defaults

All numeric fields default to 0 to avoid None values:
```python
int(data.get("block.0.rd.reqs", 0) or 0)
```

**Benefit:** InfluxDB requires at least one field per line

**Recommendation:** Continue this pattern

---

## Summary Table

| Feature | Current | Enhancement | Benefit |
|---------|---------|-------------|---------|
| Basic VM Metrics | ✅ | Keep | Stability |
| Derived Features | ✅ | Keep | Visualization |
| **Per-NIC Stats** | ❌ | **Add** | Network monitoring |
| **Per-Disk Stats** | ❌ | **Add** | Storage monitoring |
| **Extended Memory** | Partial | **Expand** | Memory analysis |
| **CPU Breakdown** | ❌ | **Add** | Performance analysis |
| **Device Discovery** | ❌ | **Add** | Infrastructure |
| **Device Caching** | ❌ | **Add** | Performance |

---

## Recommendations

### Priority 1 (Implement First)
1. ✅ Device discovery + caching infrastructure
2. ✅ Per-NIC network statistics (`vm_devices`)
3. ✅ Per-disk I/O statistics (`vm_devices`)

### Priority 2 (Implement Next)
4. ✅ Extended memory metrics
5. ✅ CPU mode breakdown

### Priority 3 (Optional)
6. ✅ Advanced aggregations
7. ✅ Anomaly detection prep

---

## Migration Plan

### Step 1: Add Device Infrastructure
- Modify `KVMConnector` to discover and cache devices
- Add device extraction functions

### Step 2: Add Device Metrics
- Expand `_collect_vm_metrics()` to per-device
- Create `vm_devices` measurement output

### Step 3: Add Extended Totals
- Expand `vm_totals` with additional fields
- Add memory and CPU breakdown

### Step 4: Testing & Validation
- Verify data accuracy
- Monitor performance impact
- Validate InfluxDB storage

---

## Estimated Effort

- **Device Infrastructure:** 2-3 hours
- **Network Metrics:** 2-3 hours
- **Disk Metrics:** 2-3 hours
- **Extended Fields:** 1-2 hours
- **Testing & Documentation:** 2-3 hours

**Total:** 9-14 hours development

---

## Questions for Implementation

1. Should device names be tag or field?
   - **Current Decision:** Tag (better for filtering)

2. How often should device list refresh?
   - **Recommended:** 300 seconds (detects hot-plugging)

3. Should we aggregate per-VM totals separately?
   - **Recommended:** Yes, in `vm_totals` measurement

4. Error handling: Stop collection or continue?
   - **Recommended:** Continue (per-device failures shouldn't block)

5. Retention policy for extended metrics?
   - **Recommended:** Shorter TTL for device metrics (7 days vs 30)

---

**Document Version:** 1.0  
**Date:** November 13, 2025  
**Status:** Analysis Complete - Ready for Implementation
