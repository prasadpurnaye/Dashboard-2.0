# VM Listing Status Report

## Current Status

### VMs Being Reported as Running (3 total)

| VM Name | ID | vCPU | Memory | State |
|---------|----|----|--------|-------|
| one-83  | 3  | 4  | 4 GB   | running |
| one-82  | 2  | 1  | 4 GB   | running |
| one-79  | 1  | 1  | 8 GB   | running |

### Expected Status (According to User)

Only 2 VMs should be live:
- one-83 ✅
- one-82 ✅
- one-79 ❌ (should NOT be listed)

## Root Cause Investigation

### API Implementation
The `/api/telemetry/live-vms` endpoint uses libvirt's `listDomainsID()` call:
```python
for dom_id in self._conn.listDomainsID():
    dom = self._conn.lookupByID(dom_id)
    vm_info = self._extract_vm_info(dom)
    vms.append(vm_info)
```

**Key Point**: `listDomainsID()` returns **only active (running) VMs** according to libvirt.

### Why one-79 is Being Listed

The fact that one-79 appears in the list means libvirt reports it as **active/running** on the remote host.

### Possible Explanations

1. **VM Recently Started**: one-79 was stopped before but has since been started
2. **Remote Host State**: The LIBVIRT_URI points to a host where one-79 is actually running
3. **Stale Data**: Unlikely - libvirt reports current state
4. **Multiple Hosts**: Could be querying different libvirt instances for different VMs

## What The Code Does (Correctly)

✅ Queries the configured LIBVIRT_URI
✅ Gets all running VMs from that host
✅ Returns their current state
✅ Filters out non-running VMs automatically

## Verification Steps

### To Check on Remote Host

If you have access to the remote libvirt host, run:
```bash
virsh list --all
```

This will show which VMs are defined and which are running.

### To Stop one-79

If one-79 should be stopped:
```bash
virsh shutdown one-79
# or
virsh destroy one-79
```

After stopping, it should disappear from the API responses.

### To Verify API Response

```bash
curl http://localhost:8000/api/telemetry/live-vms | jq '.vms | length'
# Should return 2 after one-79 is stopped
```

## Frontend Display

The VM Dashboard displays exactly what the backend reports:
- **live-vms endpoint** = shows running VMs from libvirt
- **vm-telemetry endpoint** = shows same VMs with telemetry data

## Conclusion

The API and frontend are working **correctly** - they're reporting what libvirt says are running VMs. If one-79 shouldn't be listed, it needs to be stopped on the remote libvirt host.

## Action Items

1. **Verify one-79 status** on the remote libvirt host
2. **If it should be stopped**, stop it using virsh
3. **If it should stay running**, update expectations to 3 VMs
4. **Check LIBVIRT_URI configuration** to ensure it's pointing to the right host

---

## Next Iteration

After you clarify the one-79 status, we can proceed with:
- ✅ Rate calculations (when telemetry data arrives)
- ✅ Real-time gauge updates
- ✅ Network metrics display
- ✅ Alerts based on thresholds
