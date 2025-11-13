# Memory Dumps Module - Quick Start Guide

## 🚀 5-Minute Setup

### Step 1: Verify Prerequisites

```bash
# Check InfluxDB3 is running
curl http://localhost:8181/healthz

# Check memdump.py exists
ls -la ~/Dashboard2.0/dashboard-2.0/memdump.py

# Check libvirt tools
virsh --version
```

### Step 2: Environment Variables

Update your `.env` file (or create/update it):

```bash
# InfluxDB3 Configuration
INFLUX_URL=http://localhost:8181
INFLUX_DB=vmstats
INFLUX_TOKEN=your-token-from-influxdb3

# Memory Dump Configuration
DUMP_DIR=/var/dumps
MEMDUMP_LOG_DIR=/var/log

# Libvirt Configuration (same as telemetry)
LIBVIRT_URI=qemu+ssh://oneadmin@10.10.0.94/system
LIBVIRT_TIMEOUT=30.0
```

### Step 3: Verify Directories

```bash
# Create dump directory if needed
sudo mkdir -p /var/dumps
sudo chmod 755 /var/dumps

# Create log directory if needed
sudo mkdir -p /var/log
sudo chmod 755 /var/log
```

### Step 4: Start the Dashboard

```bash
# From the dashboard directory
cd ~/Dashboard2.0/dashboard-2.0

# Activate virtual environment
source .venv/bin/activate

# Start the server
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 5: Access the Module

Open browser to: **http://localhost:8000/memory-dumps**

## 🎯 First Test

1. Click the **Memory Dumps** navbar link
2. Verify VM list populates in the dropdown
3. Select a test VM
4. Click **"Dump Selected VM"** button
5. Check the **Activity Log** for progress
6. Wait 2-5 seconds and click **"Refresh"** button
7. New dump should appear in the table

## 🔧 Common Tasks

### View Dump Details
```
Click the "👁️ View" button on any row
Modal opens with full information
```

### Copy SHA256 Hash
```
Option 1: Click "📋 Copy" button in table
Option 2: View details, then click "Copy Hash"
```

### Export All Records
```
Click "📥 Export CSV" button
CSV file downloads with all visible records
```

### Search Records
```
Type VM name or hash in search box
Table auto-filters
```

### Filter by Date
```
Enter YYYY-MM-DD in date filter
Press Enter or click outside
```

### Enable Auto-Refresh
```
Check the "Auto-refresh (5s)" checkbox
Table updates automatically every 5 seconds
```

## 🐛 Troubleshooting

### Issue: "No VMs available"

**Solution:**
```bash
# Check libvirt connection
virsh -c qemu+ssh://oneadmin@10.10.0.94/system list

# Check SSH keys
ssh-copy-id -i ~/.ssh/id_rsa oneadmin@10.10.0.94

# Restart dashboard
```

### Issue: Empty table despite triggering dumps

**Solution:**
```bash
# Verify memdump.py can run
python3 memdump.py 101

# Check InfluxDB writes
curl -X POST http://localhost:8181/api/v1/write \
  -H "Authorization: Token YOUR_TOKEN" \
  -d 'mem_dumps,dom=test,vmid=1 sha256="test",duration_sec=1.0'

# View logs
tail -f /var/log/memdump_to_influx.log
```

### Issue: "InfluxDB3 client not available"

**Solution:**
```bash
# Install influxdb3 client
pip install influxdb3-python

# Verify credentials
echo $INFLUX_URL
echo $INFLUX_DB
echo $INFLUX_TOKEN
```

### Issue: Auto-refresh not working

**Solution:**
```bash
# Check browser console (F12 > Console)
# Look for fetch errors

# Manually test endpoint
curl http://localhost:8000/api/memory-dumps/records

# Verify server logs show requests
```

## 📊 Example Workflow

```
Monday Morning - Weekly Memory Dump Cycle
├─ Open Dashboard → Memory Dumps tab
├─ Check "Auto-refresh" checkbox (5s updates)
├─ Click "Dump All VMs" button
├─ Monitor Activity Log for progress
├─ Wait 10-30 seconds (depends on VM count & sizes)
├─ Verify dumps appear in table
├─ Filter by Monday date
├─ Export CSV for record-keeping
├─ Review compressed sizes and durations
└─ Schedule alerts if any failed
```

## 💡 Tips & Best Practices

1. **Enable Auto-Refresh While Dumping**
   - Provides real-time progress visibility

2. **Use Date Filter for Organization**
   - Filter by specific dates for analysis

3. **Export Regularly**
   - Keep CSVs for audit trails
   - Helps with retention planning

4. **Monitor Disk Space**
   - Dumps are compressed but still large
   - Set retention policies in InfluxDB

5. **Schedule Large Operations Off-Peak**
   - Dump all VMs during maintenance windows
   - Monitor system load during dumps

## 🔗 Related Documentation

- **Full Module Guide**: `MEMORY_DUMPS_MODULE.md`
- **Telemetry Module**: `TELEMETRY_QUICKSTART.md`
- **API Documentation**: `MEMORY_DUMPS_MODULE.md` → API Usage Examples
- **Troubleshooting**: `KVM_TROUBLESHOOTING.md` (libvirt issues)

## 🆘 Need Help?

Check these resources in order:

1. This document (Quick Start Guide)
2. `MEMORY_DUMPS_MODULE.md` (Full documentation)
3. Browser console (F12) for client-side errors
4. Server logs: `tail -f ~/.uvicorn.log`
5. InfluxDB logs: `/var/log/influxdb/`
6. Libvirt logs: `/var/log/libvirt/`

## ✅ Success Checklist

- [ ] Environment variables configured
- [ ] Directories created and permissions set
- [ ] Dashboard starts without errors
- [ ] Memory Dumps page loads
- [ ] VM dropdown populated from libvirt
- [ ] Single dump triggers successfully
- [ ] Dump appears in table after 2-5 seconds
- [ ] Auto-refresh works (updates every 5s)
- [ ] Can search and filter records
- [ ] Can export to CSV
- [ ] Modal details display correctly
- [ ] SHA256 hash copies to clipboard

---

**Last Updated**: November 11, 2025  
**Module Version**: 1.0.0  
**Status**: Production Ready ✅
