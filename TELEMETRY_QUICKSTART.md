# Telemetry Monitoring - Quick Start Guide

## 🚀 5-Minute Setup

### Prerequisites
- Python 3.8+
- Access to KVM/QEMU hypervisor (SSH credentials)
- InfluxDB v3 instance running
- InfluxDB API token

### Step 1: Install Dependencies

```bash
cd /home/r/Dashboard2.0/dashboard-2.0

# Install all dependencies
pip install -r requirements.txt

# Optional: Install libvirt Python bindings (for telemetry)
pip install libvirt-python
```

### Step 2: Configure Environment

```bash
# Copy the example configuration
cp .env.example .env

# Edit with your actual credentials
nano .env
```

**Update these required fields:**
```bash
LIBVIRT_URI="qemu+ssh://oneadmin@192.168.0.104/system"
INFLUX_URL="http://127.0.0.1:8181"
INFLUX_DB="vmstats"
INFLUX_TOKEN="apiv3_YOUR_TOKEN_HERE"
```

### Step 3: Load Environment & Start Server

```bash
# Load environment variables
source .env

# Start the FastAPI server
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 4: Start Telemetry via API

```bash
# In another terminal, start collection
curl -X POST http://localhost:8000/api/telemetry/start

# Check status
curl http://localhost:8000/api/telemetry/status

# List VMs being monitored
curl http://localhost:8000/api/telemetry/vms
```

## 🎮 Using from Web Interface (Optional)

Add this button to your HTML template to control telemetry:

```html
<div class="telemetry-controls">
    <button onclick="startTelemetry()" class="btn-success">Start Monitoring</button>
    <button onclick="stopTelemetry()" class="btn-danger">Stop Monitoring</button>
    <div id="telemetry-status"></div>
</div>

<script>
async function startTelemetry() {
    const res = await fetch('/api/telemetry/start', {method: 'POST'});
    const data = await res.json();
    alert('Telemetry ' + data.status);
}

async function stopTelemetry() {
    const res = await fetch('/api/telemetry/stop', {method: 'POST'});
    const data = await res.json();
    alert('Telemetry ' + data.status);
}
</script>
```

## 📊 What Gets Monitored

Each VM:
- CPU usage and time
- Memory usage (current, max, RSS)
- Network stats (RX/TX bytes, packets, errors)
- Disk I/O (read/write requests, bytes)
- Derived metrics (rates, angles)

## ✅ Verification

### Check telemetry is running
```bash
curl http://localhost:8000/api/telemetry/status | jq .
```

### Verify InfluxDB received data
```bash
# Query InfluxDB
curl "http://127.0.0.1:8181/api/v3/query?db=vmstats" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d 'SELECT * FROM vm_metrics'
```

### Check logs
```bash
# Look for telemetry startup messages
# Should see: "✓ Telemetry collector initialized"
# And: "✓ Connected to libvirt"
```

## 🛑 Stopping Collection

```bash
# Stop via API
curl -X POST http://localhost:8000/api/telemetry/stop

# Or: Press Ctrl+C to stop the entire server (auto-cleanup)
```

## 🔧 Troubleshooting

### "LIBVIRT_URI not set"
```bash
# Verify environment loaded
echo $LIBVIRT_URI

# If empty, source the file
source .env

# Try again
```

### "Failed to connect to libvirt"
```bash
# Test libvirt connection directly
virsh -c qemu+ssh://oneadmin@192.168.0.104/system list

# Check SSH key permissions
chmod 600 ~/.ssh/id_rsa
```

### "InfluxDB write failed 401"
```bash
# Token might be invalid/expired
# Generate new token in InfluxDB UI
# Update .env and restart server
```

### No VMs showing
```bash
# Check VMs are running
virsh -c qemu+ssh://oneadmin@192.168.0.104/system list --running

# Verify you have read permissions on libvirt
```

## 📚 More Info

- **Full documentation**: See `TELEMETRY.md`
- **Implementation details**: See `TELEMETRY_IMPLEMENTATION.md`
- **API reference**: See `TELEMETRY.md` → "API Endpoints"

## 🎯 Next Steps

1. ✅ Set environment variables
2. ✅ Start telemetry collection
3. ✅ Verify data in InfluxDB
4. ✅ (Optional) Add UI controls to dashboard
5. ✅ (Optional) Create Grafana dashboards

## 💡 Tips

- **Performance**: Start with POLL_INTERVAL="2.0" to reduce load
- **Testing**: Use localhost libvirt first to test setup
- **Monitoring**: Check influx queue size in status endpoint
- **Logs**: Run with `--log-level debug` for verbose output

---

**Need help?** Check the full documentation in `TELEMETRY.md`
