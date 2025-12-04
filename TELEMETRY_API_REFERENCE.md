# Telemetry API Changes - Quick Reference

## Summary of Changes

### Modified Files

1. **`src/telemetry/kvm_connector.py`**
   - Added device caching
   - Added 5 new methods
   - Modified 1 existing method

2. **`src/telemetry/collector.py`**
   - Added 1 new method
   - Enhanced 1 existing method

### New Public API

#### KVMConnector

```python
# New method: Get devices with caching
get_devices_for_vm(dom: libvirt.virDomain) -> Tuple[List[str], List[str]]
# Returns: (nic_names, disk_names)
# Example: (["eth0"], ["vda"])

# New method: Get network interface stats
get_interface_stats(dom, iface_name: str) -> Dict[str, int]
# Fields: rxbytes, rxpackets, rxerrors, rxdrops, txbytes, txpackets, txerrors, txdrops

# New method: Get block device I/O stats
get_block_stats(dom, block_name: str) -> Dict[str, int]
# Fields: rd_req, rd_bytes, wr_reqs, wr_bytes, errors

# New method: Get extended memory stats
get_memory_stats(dom) -> Dict[str, int]
# Fields: memactual, memrss, memavailable, memusable, memswap_in, memswap_out, memmajor_fault, memminor_fault, memdisk_cache

# New method: Get CPU time breakdown
get_cpu_stats(dom) -> Dict[str, int]
# Fields: timeusr, timesys

# Modified method: Now includes domain object
get_live_vms() -> List[Dict[str, Any]]
# Additional key: "dom" (libvirt.virDomain object)
```

#### TelemetryCollector

```python
# New internal method (called automatically)
_collect_device_metrics(vm, base_tags, ts, lines) -> None
# Collects per-device metrics and aggregates
# Emits: vm_devices, vm_totals measurements
```

### New InfluxDB Measurements

#### `vm_devices` (Per-device)
```
Tags: VMID, name, uuid, devtype, device
Fields (NIC): rxbytes, rxpackets, rxerrors, rxdrops, txbytes, txpackets, txerrors, txdrops
Fields (disk): rd_req, rd_bytes, wr_reqs, wr_bytes, errors
```

#### `vm_totals` (Aggregated)
```
Tags: VMID, name, uuid
Fields: 
  - Network: net_rxbytes, net_rxpackets, net_rxerrors, net_rxdrops, net_txbytes, net_txpackets, net_txerrors, net_txdrops
  - Disk: disk_rd_req, disk_rd_bytes, disk_wr_reqs, disk_wr_bytes, disk_errors
  - Memory: memactual, memrss, memavailable, memusable, memswap_in, memswap_out, memmajor_fault, memminor_fault, memdisk_cache
  - CPU: timeusr, timesys, cpus, cputime, state
```

---

## Usage Examples

### Accessing New Stats in Custom Code

```python
from src.telemetry.kvm_connector import KVMConnector

# Initialize
kvm = KVMConnector("qemu:///system")
kvm.connect()

# Get VMs with domain objects
vms = kvm.get_live_vms()

# For each VM
for vm in vms:
    dom = vm["dom"]
    
    # Get network stats
    nics, disks = kvm.get_devices_for_vm(dom)
    for nic in nics:
        stats = kvm.get_interface_stats(dom, nic)
        print(f"{nic}: RX={stats['rxbytes']} TX={stats['txbytes']}")
    
    # Get disk stats
    for disk in disks:
        stats = kvm.get_block_stats(dom, disk)
        print(f"{disk}: READ={stats['rd_bytes']} WRITE={stats['wr_bytes']}")
    
    # Get memory stats
    mem = kvm.get_memory_stats(dom)
    print(f"Memory: RSS={mem['memrss']} Swap={mem['memswap_in']}")
    
    # Get CPU stats
    cpu = kvm.get_cpu_stats(dom)
    print(f"CPU: User={cpu['timeusr']} System={cpu['timesys']}")
```

### Backward Compatibility

```python
# Existing code still works
vms = kvm.get_live_vms()
for vm in vms:
    print(vm['name'])  # ✅ Works
    print(vm['cpu_count'])  # ✅ Works
    # print(vm['dom'])  # ✅ Optional, new key

# Existing metrics still generated
# vm_metrics: ✅ Still generated
# vm_features: ✅ Still generated
```

---

## Field Mappings

### Network Interface Fields

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| rxbytes | int | dom.interfaceStats()[0] | Received bytes |
| rxpackets | int | dom.interfaceStats()[1] | Received packets |
| rxerrors | int | dom.interfaceStats()[2] | RX errors |
| rxdrops | int | dom.interfaceStats()[3] | RX drops |
| txbytes | int | dom.interfaceStats()[4] | Transmitted bytes |
| txpackets | int | dom.interfaceStats()[5] | TX packets |
| txerrors | int | dom.interfaceStats()[6] | TX errors |
| txdrops | int | dom.interfaceStats()[7] | TX drops |

### Disk I/O Fields

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| rd_req | int | dom.blockStats()[0] | Read requests |
| rd_bytes | int | dom.blockStats()[1] | Bytes read |
| wr_reqs | int | dom.blockStats()[2] | Write requests |
| wr_bytes | int | dom.blockStats()[3] | Bytes written |
| errors | int | dom.blockStats()[4] | I/O errors |

### Memory Fields

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| memactual | int | dom.memoryStats() | Actual memory |
| memrss | int | dom.memoryStats() | Resident set size |
| memavailable | int | dom.memoryStats() | Available memory |
| memusable | int | dom.memoryStats() | Usable memory |
| memswap_in | int | dom.memoryStats() | Swap in events |
| memswap_out | int | dom.memoryStats() | Swap out events |
| memmajor_fault | int | dom.memoryStats() | Major faults |
| memminor_fault | int | dom.memoryStats() | Minor faults |
| memdisk_cache | int | dom.memoryStats() | Disk cache |

### CPU Fields

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| timeusr | int | dom.getCPUStats() | User CPU time (ns) |
| timesys | int | dom.getCPUStats() | System CPU time (ns) |

---

## Migration Checklist

- [ ] Deploy code changes
- [ ] Restart telemetry collector
- [ ] Verify new measurements appear in InfluxDB (wait 1-2 cycles)
- [ ] Confirm no errors in collector logs
- [ ] Query new measurements: `SELECT * FROM vm_devices LIMIT 1`
- [ ] Verify device data accuracy
- [ ] Monitor disk usage (expect ~4x for device metrics)
- [ ] Configure retention policies if needed
- [ ] Update dashboards to use new measurements (optional)

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| No vm_devices data | Collector not running or VMs have no devices | Restart collector, verify `virsh domiflist` |
| vm_totals has zeros | Stats unavailable on this libvirt version | Check logs for warnings, upgrade libvirt |
| Disk space growing fast | ~4x more metrics | Configure shorter retention for device metrics |
| Hot-plugged device not visible | Device cache hasn't expired yet | Wait 5 minutes or restart collector |
| Missing CPU breakdown | libvirt version too old | Upgrade libvirt to 10.0+ |

---

## Performance Tuning

### Device Cache TTL

```python
# In kvm_connector.py
DEVICE_CACHE_TTL = 300  # Default: 5 minutes

# Increase for stable environments (less parsing)
DEVICE_CACHE_TTL = 600  # 10 minutes

# Decrease for frequently changing devices
DEVICE_CACHE_TTL = 120  # 2 minutes
```

### Batch Size

```python
# In config: More metrics = bigger batches
batch_max_lines = 1000  # Increase for device metrics
```

---

## Monitoring the Enhancement

### Metrics to Watch

```python
# In collector status
collector.get_status()
{
    "total_metrics_written": 80,  # Was 20, now 80
    "influx_queue_size": 0,       # Should be small
    ...
}
```

### Sample Queries

```sql
-- Count measurements
SELECT COUNT(*) FROM vm_devices

-- Check device distribution
SELECT DISTINCT devtype, device FROM vm_devices

-- Verify aggregates
SELECT net_rxbytes, net_txbytes FROM vm_totals LIMIT 1
```

---

**Version:** 1.0  
**Date:** November 13, 2025  
**Status:** Ready for Integration
