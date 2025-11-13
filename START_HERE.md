# 🚀 Get Started in 5 Minutes

## Step 1: Open Terminal (30 seconds)

```bash
cd /home/r/Dashboard2.0/dashboard-2.0
```

## Step 2: Set Environment Variables (30 seconds)

```bash
export LIBVIRT_URI="qemu+ssh://oneadmin@192.168.0.104/system"
export INFLUX_URL="http://127.0.0.1:8181"
export INFLUX_DB="vmstats"
export INFLUX_TOKEN="apiv3_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

**Need different values?** Check `.env.example` for all available options.

## Step 3: Start the Server (30 seconds)

```bash
python3 -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## Step 4: Open Dashboard (30 seconds)

Open your browser:
```
http://localhost:8000/telemetry
```

## Step 5: Start Monitoring (1 minute)

1. Click the green **"▶ Start Monitoring"** button
2. Watch the activity log update in real-time
3. See status change to **"Running"** (🟢 green)
4. See VMs appear in the list below
5. Watch collections counter increment

---

## 📊 What You'll See

### ✅ If Telemetry Starts
```
Activity Log:
[14:23:43] Starting telemetry collection...
[14:23:44] ✓ Telemetry started successfully
[14:23:44] Connected to LibVirt: 5 VMs discovered
[14:23:44] InfluxDB writer thread started
[14:23:45] Collection cycle 1 complete
[14:23:45] 184 metrics written to InfluxDB

Status:
Status: running 🟢
Collections: 1
VMs Monitored: 5
Total Metrics: 184
```

### ❌ If It Fails
```
Activity Log:
[14:23:43] Starting telemetry collection...
[14:23:44] ✗ Error connecting to LibVirt
Error: Unable to connect to KVM
```

**Fix:** Check environment variables and ensure:
- LibVirt URI is correct
- InfluxDB server is running
- Token/credentials are valid

---

## 🎮 Dashboard Features

| Feature | What It Does |
|---------|-------------|
| **Start Button** | Begin collecting metrics |
| **Stop Button** | Gracefully stop collection |
| **Refresh Button** | Manually update status |
| **Status Card** | Shows real-time statistics |
| **VM List** | Shows discovered VMs |
| **Activity Log** | Real-time timestamped events |
| **Config Display** | Shows current settings |

---

## 🔄 Auto-Features (Running Automatically)

✅ Status refreshes every 2 seconds  
✅ VM list updates automatically  
✅ Metrics counter increments  
✅ Activity log receives real-time updates  
✅ Button states sync with actual state  

**You don't need to do anything - it all happens automatically!**

---

## 🧭 Navigate Between Pages

Once started, you can navigate between pages using the navbar:

- **Main Gauges** (http://localhost:8000/) - Main dashboard
- **VMs** (http://localhost:8000/vms) - VM cards
- **Telemetry** (http://localhost:8000/telemetry) - Control & monitoring

All pages have the navbar to switch between them.

---

## 🐛 Troubleshooting

### Problem: "Telemetry collector not initialized"

**Fix:** Set all environment variables:
```bash
export LIBVIRT_URI="qemu+ssh://oneadmin@192.168.0.104/system"
export INFLUX_URL="http://127.0.0.1:8181"
export INFLUX_DB="vmstats"
export INFLUX_TOKEN="your-token-here"
```

### Problem: "Unable to connect to LibVirt"

**Checklist:**
- ✅ LibVirt URI is correct? (check with `virsh -c <uri> list`)
- ✅ SSH key is set up? (for SSH URIs)
- ✅ Firewall allows connection?
- ✅ oneadmin user has access?

### Problem: Start button won't click

**Fix:** 
- Click "Refresh Status" button
- Or refresh the page (F5)
- Or check browser console for errors (F12)

### Problem: InfluxDB errors

**Checklist:**
- ✅ InfluxDB server running? (check `http://127.0.0.1:8181`)
- ✅ Correct token? (check in InfluxDB UI)
- ✅ Correct database name? (check in InfluxDB UI)

### Problem: No VMs appear

**Checklist:**
- ✅ VMs actually running on KVM host?
- ✅ LibVirt URI connects to correct host?
- ✅ Check activity log for specific errors

---

## 📈 Next Steps

### Watch Metrics in InfluxDB

1. Open InfluxDB UI: http://127.0.0.1:8181
2. Query the `vmstats` database
3. Browse available measurements (vm_cpu, vm_memory, etc.)
4. See real-time metrics flowing in

### Create Grafana Dashboard

1. Connect Grafana to InfluxDB
2. Create panels for VM metrics
3. Use `vmstats` database as source

### Check Logs

View server logs to understand what's happening:
```bash
# In the terminal running the server, you'll see:
INFO: Telemetry collector initialized (ready to start)
INFO: ✓ Telemetry collector started
```

---

## 🎯 Quick Reference

| What | Where | How |
|------|-------|-----|
| Start monitoring | Telemetry page | Green button |
| Stop monitoring | Telemetry page | Red button |
| View metrics | InfluxDB UI | Query vmstats |
| Check logs | Server terminal | Read output |
| View error | Telemetry page | Activity log |
| Change settings | .env file | Set variables |

---

## 🎉 That's It!

You're now monitoring KVM/QEMU VMs with telemetry collection!

```
✅ Dashboard running at http://localhost:8000
✅ Telemetry page at http://localhost:8000/telemetry
✅ Real-time metric collection to InfluxDB
✅ Live VM discovery and monitoring
```

**Happy monitoring!** 📊

---

## 📖 Want More Details?

- **UI Guide:** Read `TELEMETRY_UI_GUIDE.md`
- **API Reference:** Read `TELEMETRY.md`
- **Architecture:** Read `TELEMETRY_IMPLEMENTATION.md`
- **Configuration:** Read `.env.example`

---

**Questions?** Check the activity log on the dashboard for real-time feedback!
