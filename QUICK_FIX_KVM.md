# 🧪 Quick Test - KVM Connection

## Immediate Solution

The error "Not connected to libvirt" typically means SSH authentication is failing. Here's the quickest fix:

### 1. Set Up SSH Keys (Run These Commands)

```bash
# Generate SSH key if needed
ssh-keygen -t rsa -f ~/.ssh/id_rsa -N ""

# Copy key to KVM host
ssh-copy-id -i ~/.ssh/id_rsa oneadmin@10.10.0.94

# Verify it works
ssh oneadmin@10.10.0.94 "echo SSH OK"
# Should output: SSH OK
```

### 2. Verify Environment Variables

```bash
cd /home/r/Dashboard2.0/dashboard-2.0
cat .env | grep LIBVIRT

# Should show:
# LIBVIRT_URI=qemu+ssh://oneadmin@10.10.0.94/system
```

### 3. Install libvirt (if needed)

```bash
source .venv/bin/activate
pip install libvirt-python

# Verify
python3 -c "import libvirt; print('✓ OK')"
```

### 4. Restart Server

```bash
cd /home/r/Dashboard2.0/dashboard-2.0
source .venv/bin/activate
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Test the New Diagnostic Endpoint

```bash
# In another terminal
curl http://localhost:8000/api/telemetry/diagnostic | jq
```

**Look for in response:**
```json
{
  "kvm": {
    "status": "connected",
    "live_vms": 2,
    "error": null
  }
}
```

If `status` is `"error"`, check the `error` field for the actual problem.

---

## Verify It Works

1. Navigate to `http://localhost:8000/vms` in browser
2. Should now see real VMs instead of error
3. Check console logs for "✓ Retrieved X live VMs from KVM"

---

## Still Not Working?

Run this Python test:

```python
import libvirt

uri = "qemu+ssh://oneadmin@10.10.0.94/system"
print(f"Testing connection to: {uri}")

try:
    conn = libvirt.open(uri)
    vms = conn.listAllDomains()
    print(f"✓ Connected successfully")
    print(f"✓ Found {len(vms)} VMs:")
    for vm in vms:
        print(f"  - {vm.name()}")
    conn.close()
except Exception as e:
    print(f"✗ Connection failed: {e}")
    print(f"Make sure:")
    print(f"  1. SSH key is set up: ssh-copy-id -i ~/.ssh/id_rsa oneadmin@10.10.0.94")
    print(f"  2. SSH works: ssh oneadmin@10.10.0.94 'echo OK'")
    print(f"  3. libvirt is installed: pip install libvirt-python")
```

---

**Most common fix: Setup SSH key with `ssh-copy-id`** ✅
