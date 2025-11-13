# 🚀 Quick Start - Live VMs Integration

## What's New

You can now see **real VMs from your KVM host** in the VMs tab and track **monitored VMs from InfluxDB**.

---

## 📋 Quick API Reference

### 1. Get Live VMs (Real-time from KVM)
```bash
curl http://localhost:8000/api/telemetry/live-vms
```
**Shows:** VMs currently running on your KVM host
**Use:** Display in VMs Tab

### 2. Get Monitored VMs (Historical from InfluxDB)
```bash
curl http://localhost:8000/api/telemetry/monitored-vms
```
**Shows:** Unique VMs that have been monitored + last collection time
**Use:** Telemetry statistics and history

### 3. Get VM Metrics (Latest stats for one VM)
```bash
curl http://localhost:8000/api/telemetry/vm-stats/1
```
**Shows:** CPU, memory, network metrics for VM with ID=1
**Use:** Detailed VM performance tracking

---

## 🎬 Try It Now

### Step 1: Restart Server
```bash
cd /home/r/Dashboard2.0/dashboard-2.0
source .venv/bin/activate
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 2: Start Telemetry
Visit `http://localhost:8000/telemetry` and click **"Start Monitoring"**

### Step 3: View Live VMs
Visit `http://localhost:8000/vms`

You should see:
- ✅ Real VMs from your KVM host (10.10.0.94)
- ✅ VM specs (CPU, Memory)
- ✅ Live gauges updating
- ✅ Status indicators

### Step 4: Check Monitored VMs
```bash
curl http://localhost:8000/api/telemetry/monitored-vms
```

You should see:
- ✅ Unique VMs found in InfluxDB
- ✅ Latest collection timestamp
- ✅ Count of monitored VMs

---

## 📊 Data Sources

| Endpoint | Source | Purpose |
|----------|--------|---------|
| `/api/telemetry/live-vms` | libvirt | Current running VMs |
| `/api/telemetry/monitored-vms` | InfluxDB | Historical monitoring |
| `/api/telemetry/vm-stats/{id}` | InfluxDB | Specific VM metrics |

---

## 🔍 Understanding the Data

### Live VMs Response
```json
{
  "count": 2,
  "source": "libvirt",
  "vms": [
    {
      "id": "1",
      "name": "ubuntu-vm",
      "uuid": "...",
      "state": 1,
      "cpu_count": 4,
      "memory_max": 8388608,
      "memory_used": 4194304
    }
  ]
}
```

### Monitored VMs Response
```json
{
  "count": 2,
  "source": "influxdb",
  "last_collection": "2025-11-11T12:15:45Z",  ← Latest timestamp from InfluxDB
  "vms": [
    {
      "id": "1",        ← Unique Dom value from InfluxDB
      "name": "ubuntu-vm",
      "uuid": "...",
      "source": "influxdb"
    }
  ]
}
```

---

## 🎨 What You'll See in VMs Tab

Each VM card shows:
```
┌─────────────────────────────┐
│ ubuntu-vm          ● Online │
├─────────────────────────────┤
│ ID: 1                       │
│ CPU: 4 vCPU                 │
│ Memory: 8 GB                │
├─────────────────────────────┤
│ CPU: 45.3%  Mem: 62.1%      │
│ Disk: 28.5%                 │
└─────────────────────────────┘
```

---

## 🔧 Files Changed

**New:**
- `src/telemetry/influx_query.py` - Query InfluxDB for VMs

**Updated:**
- `src/api/telemetry.py` - Added 3 new endpoints
- `static/js/vm-dashboard.js` - Fetch real VMs from API
- `static/css/style.css` - VM info styling
- `src/telemetry/collector.py` - Fixed thread reuse bug
- `src/telemetry/influx_connector.py` - Better logging

---

## ✅ Verification Checklist

- [ ] Server is running
- [ ] Telemetry monitoring is started
- [ ] VMs tab shows real VMs (not dummy data)
- [ ] Each card shows correct CPU/Memory specs
- [ ] Gauges update every 2 seconds
- [ ] `/api/telemetry/monitored-vms` returns data
- [ ] Last collection timestamp is recent
- [ ] Metrics are being written to InfluxDB

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| No VMs in VMs tab | Ensure telemetry is running, check console logs |
| "Never" in last collection | Start telemetry and wait for first cycle |
| Wrong VM count | Check both libvirt and InfluxDB connectivity |
| Gauges not updating | Check browser console for errors |

---

## 📚 Full Documentation

See `LIVE_VMS_INTEGRATION.md` for detailed documentation.

**Next Steps:**
1. ✅ View real VMs
2. ✅ Monitor metrics in InfluxDB
3. ✅ Create Grafana dashboards
4. ✅ Set up alerting

**Happy Monitoring!** 🎉
