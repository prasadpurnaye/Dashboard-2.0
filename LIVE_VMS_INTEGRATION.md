# 🚀 Live VMs Integration - Complete Implementation

## What Was Added

### 1. InfluxDB Query Module (`src/telemetry/influx_query.py`)
A new module to query metrics from InfluxDB v3 and extract VM information.

**Features:**
- `get_unique_vms()` - Extracts unique VMs by parsing `vm_info` measurements
  - Returns list of VMs with ID, name, UUID from InfluxDB
  - Looks back 24 hours for historical data
  
- `get_latest_collection_time()` - Gets timestamp of latest metrics
  - Queries the MAX(time) from vm_info table
  - Returns ISO format timestamp or "Never" if no data
  
- `get_vm_metrics(vm_id)` - Gets latest metrics for specific VM
  - Queries CPU time, memory, network stats
  - Returns current performance data

**How it works:**
```python
influx_query = InfluxQuery(url, db, token)
unique_vms = influx_query.get_unique_vms()  # Parse Dom values from InfluxDB
latest_time = influx_query.get_latest_collection_time()
```

---

### 2. Three New API Endpoints (`src/api/telemetry.py`)

#### `GET /api/telemetry/live-vms`
**Returns:** List of currently running VMs from libvirt
```bash
curl http://localhost:8000/api/telemetry/live-vms
```

**Response:**
```json
{
  "count": 2,
  "source": "libvirt",
  "vms": [
    {
      "id": "1",
      "name": "ubuntu-vm",
      "uuid": "12345678-abcd-1234-abcd-1234567890ab",
      "state": 1,
      "cpu_count": 4,
      "memory_max": 8388608,
      "memory_used": 4194304
    },
    {
      "id": "2",
      "name": "centos-vm",
      "uuid": "87654321-dcba-4321-dcba-0987654321ba",
      "state": 1,
      "cpu_count": 2,
      "memory_max": 4194304,
      "memory_used": 2097152
    }
  ]
}
```

#### `GET /api/telemetry/monitored-vms`
**Returns:** Unique VMs found in InfluxDB (from monitoring history)
```bash
curl http://localhost:8000/api/telemetry/monitored-vms
```

**Response:**
```json
{
  "count": 2,
  "source": "influxdb",
  "last_collection": "2025-11-11T12:15:45.123456Z",
  "vms": [
    {
      "id": "1",
      "name": "ubuntu-vm",
      "uuid": "12345678-abcd-1234-abcd-1234567890ab",
      "source": "influxdb"
    }
  ]
}
```

#### `GET /api/telemetry/vm-stats/{vm_id}`
**Returns:** Latest metrics for a specific VM
```bash
curl http://localhost:8000/api/telemetry/vm-stats/1
```

**Response:**
```json
{
  "vm_id": "1",
  "metrics": {
    "cpu_time_ns": 123456789,
    "memory_used_kb": 4194304,
    "rx_bytes": 1024000,
    "tx_bytes": 512000
  }
}
```

---

### 3. Updated VM Dashboard (`templates/vms.html` + `static/js/vm-dashboard.js`)

**Key Changes:**
- ✅ No longer uses dummy data
- ✅ Fetches live VMs from `/api/telemetry/live-vms`
- ✅ Displays real VM information:
  - VM Name
  - VM ID (from libvirt)
  - CPU count
  - Memory allocation
- ✅ Shows 3 gauges per VM (CPU, Memory, Disk)
- ✅ Auto-updates every 2 seconds

**Flow:**
```
Page Load
  ↓
fetch('/api/telemetry/live-vms')
  ↓
Get live VMs from KVM
  ↓
Create cards with real VM data
  ↓
Initialize gauges
  ↓
Update metrics every 2 seconds
```

---

### 4. Enhanced CSS (`static/css/style.css`)

Added `.vm-card-info` styles to display VM details:
```css
.vm-card-info {
    margin-bottom: 15px;
    padding-bottom: 15px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    font-size: 0.9em;
}
```

---

## 🔄 Data Flow

### Live VMs (Real-time from KVM)
```
VMs Tab Page
    ↓
fetch('/api/telemetry/live-vms')
    ↓
API calls KVM.get_live_vms()
    ↓
Returns running VMs with libvirt data
    ↓
Display in cards
```

### Monitored VMs (Historical from InfluxDB)
```
Telemetry Status Page
    ↓
fetch('/api/telemetry/monitored-vms')
    ↓
Query InfluxDB for unique vm_info tags
    ↓
Parse unique VMID values (Dom)
    ↓
Extract latest collection timestamp
    ↓
Display statistics
```

---

## 🎯 How to Use

### 1. Start Telemetry Monitoring
```bash
# On Telemetry page
curl -X POST http://localhost:8000/api/telemetry/start
```

### 2. View Live VMs Tab
```
Navigate to http://localhost:8000/vms
```
You'll see:
- Real running VMs from KVM
- VM specifications (CPU, Memory)
- Live gauge metrics
- Auto-updating status

### 3. Get Monitored VM Statistics
```bash
curl http://localhost:8000/api/telemetry/monitored-vms
```
Returns:
- Unique VMs found in InfluxDB
- Last collection timestamp
- Count of monitored VMs

### 4. Get Specific VM Metrics
```bash
curl http://localhost:8000/api/telemetry/vm-stats/1
```

---

## 📊 Database Queries Used

### Get Unique VMs from InfluxDB
```sql
SELECT DISTINCT "name", "VMID", "uuid" 
FROM "vm_info" 
WHERE time > now() - 24h
ORDER BY "VMID"
```

### Get Latest Collection Timestamp
```sql
SELECT MAX(time) as latest_time 
FROM "vm_info"
```

### Get VM Metrics
```sql
SELECT LAST("cpu_time_ns") as cpu_time,
       LAST("memory_used_kb") as memory_used,
       LAST("rx_bytes") as rx_bytes,
       LAST("tx_bytes") as tx_bytes
FROM "vm_cpu", "vm_memory", "vm_network"
WHERE "VMID" = 'vm_id' AND time > now() - 1h
```

---

## ✨ Key Features

✅ **Real-time VM Discovery**
- Uses libvirt API
- Gets current running VMs
- Shows CPU, memory specs

✅ **Historical Analysis**
- Queries InfluxDB for monitored VMs
- Gets unique Dom values
- Identifies collection trends

✅ **Unified Dashboard**
- Live VMs in VMs tab
- Statistics in Telemetry tab
- Consistent data sources

✅ **Error Handling**
- Graceful fallback if no VMs
- Handles missing data
- Logs all operations

---

## 🚦 Testing

### Test Live VMs Endpoint
```bash
curl http://localhost:8000/api/telemetry/live-vms
```

### Test Monitored VMs Endpoint
```bash
curl http://localhost:8000/api/telemetry/monitored-vms
```

### Test VM Stats Endpoint
```bash
# Replace 1 with actual VM ID
curl http://localhost:8000/api/telemetry/vm-stats/1
```

### Browser Test
1. Open `http://localhost:8000/vms`
2. Should see real VMs loaded from your KVM host
3. Gauges should update every 2 seconds

---

## 📝 Files Modified

| File | Changes |
|------|---------|
| `src/telemetry/influx_query.py` | ✨ NEW - Query module |
| `src/api/telemetry.py` | ✅ Added 3 endpoints |
| `static/js/vm-dashboard.js` | ✅ Real VM data loading |
| `static/css/style.css` | ✅ Added `.vm-card-info` |
| `src/main.py` | ✅ Added `load_dotenv()` |
| `src/telemetry/collector.py` | ✅ Fixed thread reuse |
| `src/telemetry/influx_connector.py` | ✅ Enhanced logging |
| `.env` | ✅ Added correct variables |

---

## 🎓 Understanding the Integration

### Why Two Sources?

1. **Live VMs (libvirt)** - For real-time current state
   - What's running RIGHT NOW
   - Used in VMs tab
   - API: `/api/telemetry/live-vms`

2. **Monitored VMs (InfluxDB)** - For historical analysis
   - What HAS BEEN monitored
   - Used in Telemetry status
   - Shows metrics history
   - API: `/api/telemetry/monitored-vms`

### Why Parse Unique Dom Values?

InfluxDB stores metrics with tags like:
```
vm_info,VMID=1,name=ubuntu-vm,uuid=12345 state=1
vm_info,VMID=1,name=ubuntu-vm,uuid=12345 cpu_count=4
...
```

By selecting DISTINCT on VMID, we identify unique VMs that have ever been monitored, not just what's running now.

---

## 🔧 Troubleshooting

### No VMs Showing in VMs Tab
1. Check if telemetry is running: `GET /api/telemetry/status`
2. Verify KVM connection: Check logs for "Connected to libvirt"
3. Ensure environment variables are set

### Monitored VMs Shows "Never"
1. No metrics have been collected yet
2. Start telemetry and wait for first collection
3. Check InfluxDB has data: `curl -X GET http://127.0.0.1:8181/api/v3/query?db=vmstats`

### Metrics Show 0
1. Metrics are being collected but not written yet
2. Check InfluxDB queue size: `GET /api/telemetry/status`
3. Look at console logs for write errors

---

## 🎉 You Now Have

✅ Live VM display from KVM  
✅ Historical VM tracking from InfluxDB  
✅ Real-time metrics collection  
✅ Unique VM identification  
✅ Latest collection timestamp  
✅ Per-VM performance stats  
✅ Beautiful dashboard UI  

**Happy Monitoring!** 📊

