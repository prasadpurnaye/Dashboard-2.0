# 🔧 Troubleshooting - KVM Connection Issues

## Issue: "Not connected to libvirt" Error

When navigating to the VMs tab, you get:
```
KVM error: Not connected to libvirt
```

---

## 🔍 Root Causes & Solutions

### 1. **SSH Key Authentication Issue** (Most Common)

libvirt uses SSH to connect to the remote KVM host. Without proper SSH keys, the connection fails.

**Solution:**

```bash
# 1. Generate SSH key if you don't have one
ssh-keygen -t rsa -f ~/.ssh/id_rsa -N ""

# 2. Copy your SSH key to the remote host
ssh-copy-id -i ~/.ssh/id_rsa oneadmin@10.10.0.94

# 3. Test SSH connection
ssh oneadmin@10.10.0.94 "virsh -c qemu+ssh://oneadmin@10.10.0.94/system list"

# 4. Restart the server
cd /home/r/Dashboard2.0/dashboard-2.0
source .venv/bin/activate
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

---

### 2. **SSH Daemon Not Running**

The SSH daemon might not be running on the KVM host.

**Solution:**

```bash
# Test if SSH is working
ssh -v oneadmin@10.10.0.94

# If fails, check SSH on remote host
ssh-keyscan -t rsa 10.10.0.94
```

---

### 3. **Wrong Credentials in .env**

The LIBVIRT_URI might be incorrect or the user doesn't have permissions.

**Solution:**

```bash
# Check your .env file
cat /home/r/Dashboard2.0/dashboard-2.0/.env

# Verify LIBVIRT_URI format - it should be:
# qemu+ssh://username@hostname/system

# Common issues:
# ❌ qemu+ssh://10.10.0.94/system  (missing username)
# ✅ qemu+ssh://oneadmin@10.10.0.94/system

# Verify user has permissions
ssh oneadmin@10.10.0.94 "groups oneadmin"
# Should include: libvirt, libvirt-qemu, or similar
```

---

### 4. **libvirt-python Not Installed**

The Python libvirt bindings might be missing.

**Solution:**

```bash
# Install libvirt-python
cd /home/r/Dashboard2.0/dashboard-2.0
source .venv/bin/activate
pip install libvirt-python

# Verify installation
python3 -c "import libvirt; print('✓ libvirt available')"
```

---

## 🧪 Diagnostic Endpoint

A new diagnostic endpoint has been added to help troubleshoot:

```bash
curl http://localhost:8000/api/telemetry/diagnostic
```

**Response example:**
```json
{
  "status": "success",
  "config": {
    "libvirt_uri": "***",
    "influx_url": "***",
    ...
  },
  "kvm": {
    "status": "connected",
    "live_vms": 2,
    "error": null
  },
  "influx": {
    "status": "connected",
    "error": null
  },
  "collector": {
    "running": true,
    "vms_monitored": 2
  }
}
```

**Interpretation:**
- `kvm.status: "error"` → Connection failed, check SSH and credentials
- `kvm.status: "connected"` → libvirt connection works
- `kvm.live_vms: 0` → Connected but no VMs found
- `kvm.live_vms: > 0` → Everything working!

---

## 🔍 Step-by-Step Troubleshooting

### Step 1: Verify Environment Variables
```bash
source /home/r/Dashboard2.0/dashboard-2.0/.env
echo "LIBVIRT_URI: $LIBVIRT_URI"
echo "INFLUX_URL: $INFLUX_URL"
```

**Expected Output:**
```
LIBVIRT_URI: qemu+ssh://oneadmin@10.10.0.94/system
INFLUX_URL: http://127.0.0.1:8181
```

### Step 2: Test SSH Connection
```bash
# Extract user from LIBVIRT_URI
ssh oneadmin@10.10.0.94 "echo 'SSH is working'"

# Expected: "SSH is working"
# If fails: SSH key setup issue
```

### Step 3: Test libvirt Connection
```bash
python3 -c "
import libvirt
uri = 'qemu+ssh://oneadmin@10.10.0.94/system'
try:
    conn = libvirt.open(uri)
    print(f'✓ Connected to libvirt')
    print(f'✓ Found {len(conn.listAllDomains())} VMs')
    conn.close()
except Exception as e:
    print(f'✗ Connection failed: {e}')
"
```

### Step 4: Run Diagnostic Endpoint
```bash
curl http://localhost:8000/api/telemetry/diagnostic | jq
```

### Step 5: Check Server Logs
```bash
# Look for error messages in the server logs
# The server output should show:
# - Connection attempts
# - VM count
# - Any libvirt errors
```

---

## 🛠️ Manual Testing

### Test 1: SSH Access
```bash
ssh -i ~/.ssh/id_rsa oneadmin@10.10.0.94 "virsh -c qemu:///system list"
```

### Test 2: Python Libvirt
```python
import libvirt

uri = "qemu+ssh://oneadmin@10.10.0.94/system"
conn = libvirt.open(uri)
vms = conn.listAllDomains()
for vm in vms:
    print(f"VM: {vm.name()}, UUID: {vm.UUIDString()}")
conn.close()
```

### Test 3: FastAPI Endpoint
```bash
# After restarting server:
curl http://localhost:8000/api/telemetry/live-vms | jq

# Should show:
{
  "count": 2,
  "source": "libvirt",
  "vms": [
    {
      "id": 1,
      "name": "ubuntu-vm",
      ...
    }
  ]
}
```

---

## 📋 Checklist for Resolution

- [ ] SSH key exists and is in `~/.ssh/id_rsa`
- [ ] SSH key is copied to remote host: `ssh-copy-id -i ~/.ssh/id_rsa oneadmin@10.10.0.94`
- [ ] SSH connection works: `ssh oneadmin@10.10.0.94 "echo OK"`
- [ ] `.env` has correct `LIBVIRT_URI` format
- [ ] libvirt-python is installed: `pip install libvirt-python`
- [ ] Server is restarted after changes
- [ ] Diagnostic endpoint shows KVM status: `connected`
- [ ] VMs tab displays real VMs (not error)

---

## 🔐 SSH Setup Guide

### If SSH Key Doesn't Exist:

```bash
# Generate key
ssh-keygen -t rsa -f ~/.ssh/id_rsa -N ""

# Copy to remote host
ssh-copy-id -i ~/.ssh/id_rsa oneadmin@10.10.0.94

# Verify
ssh oneadmin@10.10.0.94 "echo 'SSH OK'"
```

### If SSH is Already Set Up:

```bash
# Just verify it works
ssh oneadmin@10.10.0.94 "virsh --version"

# Should output something like: 8.0.0
```

### Set Correct Permissions:

```bash
# SSH directory permissions
chmod 700 ~/.ssh
chmod 600 ~/.ssh/id_rsa
chmod 644 ~/.ssh/id_rsa.pub

# Test again
ssh oneadmin@10.10.0.94 "echo OK"
```

---

## 🎯 Verification

Once fixed, you should see:

1. **VMs Tab Working:**
   - Opens without errors
   - Shows real VMs from KVM
   - Displays VM specs (CPU, Memory)
   - Gauges update in real-time

2. **Diagnostic Endpoint:**
   ```bash
   curl http://localhost:8000/api/telemetry/diagnostic
   ```
   Shows:
   - `"kvm": {"status": "connected", "live_vms": 2}`
   - `"influx": {"status": "connected"}`

3. **Console Logs:**
   - ✓ Retrieved X live VMs from KVM
   - No "Not connected to libvirt" errors

---

## 🆘 Still Having Issues?

1. **Check the diagnostic endpoint:**
   ```bash
   curl http://localhost:8000/api/telemetry/diagnostic | jq .kvm
   ```

2. **Review the error message** from the KVM section

3. **Check SSH keys:**
   ```bash
   # List SSH keys
   ls -la ~/.ssh/
   
   # Verify key is set up on remote
   ssh oneadmin@10.10.0.94 "cat ~/.ssh/authorized_keys | grep $(cat ~/.ssh/id_rsa.pub)"
   ```

4. **Check libvirt version compatibility:**
   ```bash
   python3 -c "import libvirt; print(libvirt.getVersion())"
   ```

5. **Check remote libvirt version:**
   ```bash
   ssh oneadmin@10.10.0.94 "virsh --version"
   ```

---

## 📞 Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `libvirt: QEMU Connection Driver error : authentication unavailable` | SSH key not set up | Run `ssh-copy-id` |
| `Unable to connect to libvirt qemu+ssh` | SSH connection issue | Test SSH manually |
| `No module named libvirt` | libvirt-python not installed | `pip install libvirt-python` |
| `Connection refused` | Remote host not responding | Check if KVM host is up |
| `Permission denied` | User doesn't have permissions | Add user to libvirt group |

---

## 🚀 Quick Reset

If you want to start fresh with SSH setup:

```bash
# Remove old SSH key
rm ~/.ssh/id_rsa*

# Generate new one
ssh-keygen -t rsa -f ~/.ssh/id_rsa -N ""

# Copy to remote
ssh-copy-id -i ~/.ssh/id_rsa oneadmin@10.10.0.94

# Verify
ssh oneadmin@10.10.0.94 "echo SSH OK"

# Restart server
cd /home/r/Dashboard2.0/dashboard-2.0
source .venv/bin/activate
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

---

**After making changes, always restart the server for changes to take effect!** 🚀
