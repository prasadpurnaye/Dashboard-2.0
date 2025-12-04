# Memory Dump Service Integration - Code Examples

## Python Client Library

Here's a helper class to interact with the memory dump API:

```python
import requests
import time
from typing import Dict, List, Optional

class MemoryDumpClient:
    """Client for interacting with Dashboard memory dump API"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.api_prefix = "/api/memory-dumps"
    
    def trigger_dumps(self, vm_names: List[str]) -> Dict:
        """Trigger memory dumps for specified VMs"""
        url = f"{self.base_url}{self.api_prefix}/trigger"
        payload = {"vms": vm_names}
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    
    def get_status(self) -> Dict:
        """Get status of all active dumps"""
        url = f"{self.base_url}{self.api_prefix}/status"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    
    def get_vm_status(self, vm_id: str) -> Dict:
        """Get status of specific VM dump"""
        url = f"{self.base_url}{self.api_prefix}/status/{vm_id}"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    
    def get_records(self, limit: int = 100, offset: int = 0) -> Dict:
        """Get historical dump records"""
        url = f"{self.base_url}{self.api_prefix}/records"
        params = {"limit": limit, "offset": offset}
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def get_stats(self) -> Dict:
        """Get dump statistics"""
        url = f"{self.base_url}{self.api_prefix}/stats"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    
    def wait_for_completion(self, vm_names: List[str], timeout: int = 3600, poll_interval: int = 5) -> Dict:
        """
        Trigger dumps and wait for completion
        
        Args:
            vm_names: List of VM names
            timeout: Maximum seconds to wait
            poll_interval: Seconds between status checks
        
        Returns:
            Dictionary with final status of all dumps
        """
        # Trigger dumps
        trigger_result = self.trigger_dumps(vm_names)
        print(f"✓ Triggered dumps: {trigger_result['message']}")
        
        # Poll for completion
        elapsed = 0
        while elapsed < timeout:
            status_data = self.get_status()
            active_dumps = status_data.get('active_dumps', {})
            
            # Check if all VMs are done
            all_done = True
            for vm in vm_names:
                if vm in active_dumps:
                    dump_status = active_dumps[vm]
                    state = dump_status['state']
                    
                    if state == 'running':
                        progress = dump_status.get('progress', 0)
                        print(f"  {vm}: {progress:.1f}% complete")
                        all_done = False
                    elif state == 'queued':
                        print(f"  {vm}: queued")
                        all_done = False
                    elif state == 'completed':
                        print(f"  ✓ {vm}: completed in {dump_status.get('duration_sec', 0):.2f}s")
                        print(f"     Path: {dump_status.get('dump_path', 'N/A')}")
                    elif state == 'failed':
                        print(f"  ✗ {vm}: failed - {dump_status.get('message', 'unknown error')}")
            
            if all_done:
                print("✓ All dumps completed!")
                return status_data
            
            time.sleep(poll_interval)
            elapsed += poll_interval
        
        raise TimeoutError(f"Dump operation timed out after {timeout} seconds")

# Usage Example
if __name__ == "__main__":
    client = MemoryDumpClient("http://localhost:8000")
    
    # Trigger and wait for completion
    try:
        result = client.wait_for_completion(["web-vm-1", "db-vm-1"], timeout=600)
        print("\nFinal result:")
        print(result)
    except TimeoutError as e:
        print(f"ERROR: {e}")
    
    # Get statistics
    stats = client.get_stats()
    print(f"\nDump Statistics:")
    print(f"  Total dumps: {stats['total_dumps']}")
    print(f"  Total VMs: {stats['total_vms']}")
    print(f"  Total size: {stats['total_size_bytes'] / 1024 / 1024 / 1024:.2f} GB")
    print(f"  Avg duration: {stats['avg_duration_sec']:.2f} seconds")
```

## JavaScript/Frontend Example

### Vue.js Component for Dump Management

```vue
<template>
  <div class="memory-dumps">
    <div class="dump-trigger">
      <h3>Memory Dumps</h3>
      <div class="vm-selector">
        <label>
          <input type="checkbox" v-model="selectedVMs" value="vm1"> VM1
        </label>
        <label>
          <input type="checkbox" v-model="selectedVMs" value="vm2"> VM2
        </label>
      </div>
      <button @click="triggerDump" :disabled="selectedVMs.length === 0 || isLoading">
        {{ isLoading ? 'Dumping...' : 'Trigger Dump' }}
      </button>
    </div>

    <!-- Active Dumps -->
    <div class="active-dumps" v-if="activeDumps.length > 0">
      <h4>Active Dumps</h4>
      <div v-for="dump in activeDumps" :key="dump.vm" class="dump-card">
        <div class="dump-header">
          <span class="vm-name">{{ dump.vm }}</span>
          <span :class="['status', dump.state]">{{ dump.state }}</span>
        </div>
        <div class="dump-body" v-if="dump.state === 'running'">
          <div class="progress-bar">
            <div class="progress-fill" :style="{width: dump.progress + '%'}"></div>
          </div>
          <span class="progress-text">{{ dump.progress.toFixed(1) }}%</span>
        </div>
        <div class="dump-footer" v-if="dump.state === 'completed'">
          <span class="duration">{{ dump.duration_sec.toFixed(2) }}s</span>
          <a :href="dump.dump_path" download>Download</a>
        </div>
      </div>
    </div>

    <!-- Historical Records -->
    <div class="dump-records">
      <h4>Recent Dumps</h4>
      <table v-if="records.length > 0">
        <thead>
          <tr>
            <th>VM</th>
            <th>Time</th>
            <th>Size</th>
            <th>Duration</th>
            <th>SHA256</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="record in records" :key="record.time">
            <td>{{ record.dom }}</td>
            <td>{{ formatDate(record.time) }}</td>
            <td>{{ formatBytes(record.gzip_size_bytes) }}</td>
            <td>{{ record.duration_sec.toFixed(2) }}s</td>
            <td class="hash">{{ record.sha256.substring(0, 16) }}...</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Statistics -->
    <div class="dump-stats" v-if="stats">
      <h4>Statistics</h4>
      <div class="stats-grid">
        <div class="stat">
          <span class="label">Total Dumps</span>
          <span class="value">{{ stats.total_dumps }}</span>
        </div>
        <div class="stat">
          <span class="label">Total VMs</span>
          <span class="value">{{ stats.total_vms }}</span>
        </div>
        <div class="stat">
          <span class="label">Total Size</span>
          <span class="value">{{ formatBytes(stats.total_size_bytes) }}</span>
        </div>
        <div class="stat">
          <span class="label">Avg Duration</span>
          <span class="value">{{ stats.avg_duration_sec.toFixed(2) }}s</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'MemoryDumps',
  data() {
    return {
      selectedVMs: [],
      isLoading: false,
      activeDumps: [],
      records: [],
      stats: null,
      pollInterval: null
    };
  },
  mounted() {
    this.loadInitialData();
    this.startPolling();
  },
  beforeUnmount() {
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
    }
  },
  methods: {
    async triggerDump() {
      if (this.selectedVMs.length === 0) return;
      
      this.isLoading = true;
      try {
        const response = await fetch('/api/memory-dumps/trigger', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ vms: this.selectedVMs })
        });
        
        if (!response.ok) throw new Error('Failed to trigger dumps');
        
        console.log('✓ Dumps triggered successfully');
        this.selectedVMs = [];
        await this.updateStatus();
      } catch (error) {
        console.error('Error triggering dumps:', error);
      } finally {
        this.isLoading = false;
      }
    },
    
    async loadInitialData() {
      await this.updateStatus();
      await this.loadRecords();
      await this.loadStats();
    },
    
    async updateStatus() {
      try {
        const response = await fetch('/api/memory-dumps/status');
        if (!response.ok) throw new Error('Failed to fetch status');
        
        const data = await response.json();
        this.activeDumps = Object.values(data.active_dumps || {});
      } catch (error) {
        console.error('Error updating status:', error);
      }
    },
    
    async loadRecords() {
      try {
        const response = await fetch('/api/memory-dumps/records?limit=10');
        if (!response.ok) throw new Error('Failed to fetch records');
        
        const data = await response.json();
        this.records = data.records || [];
      } catch (error) {
        console.error('Error loading records:', error);
      }
    },
    
    async loadStats() {
      try {
        const response = await fetch('/api/memory-dumps/stats');
        if (!response.ok) throw new Error('Failed to fetch stats');
        
        this.stats = await response.json();
      } catch (error) {
        console.error('Error loading stats:', error);
      }
    },
    
    startPolling() {
      this.pollInterval = setInterval(() => {
        this.updateStatus();
      }, 5000); // Update every 5 seconds
    },
    
    formatDate(dateString) {
      return new Date(dateString).toLocaleString();
    },
    
    formatBytes(bytes) {
      if (bytes === 0) return '0 B';
      const k = 1024;
      const sizes = ['B', 'KB', 'MB', 'GB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }
  }
};
</script>

<style scoped>
.memory-dumps {
  padding: 20px;
}

.dump-trigger {
  margin-bottom: 30px;
  padding: 15px;
  background: #f5f5f5;
  border-radius: 8px;
}

.vm-selector {
  margin: 15px 0;
}

.vm-selector label {
  margin-right: 20px;
  display: inline-block;
}

button {
  padding: 10px 20px;
  background: #4caf50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

button:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.dump-card {
  background: white;
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 15px;
  margin-bottom: 10px;
}

.dump-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
}

.status {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.9em;
}

.status.running {
  background: #fff3cd;
  color: #856404;
}

.status.completed {
  background: #d4edda;
  color: #155724;
}

.status.failed {
  background: #f8d7da;
  color: #721c24;
}

.progress-bar {
  width: 100%;
  height: 20px;
  background: #e9ecef;
  border-radius: 4px;
  overflow: hidden;
  margin: 10px 0;
}

.progress-fill {
  height: 100%;
  background: #4caf50;
  transition: width 0.3s ease;
}

.dump-records table {
  width: 100%;
  border-collapse: collapse;
}

.dump-records th,
.dump-records td {
  padding: 10px;
  text-align: left;
  border-bottom: 1px solid #ddd;
}

.dump-records th {
  background: #f5f5f5;
  font-weight: bold;
}

.hash {
  font-family: monospace;
  font-size: 0.9em;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
  margin-top: 15px;
}

.stat {
  background: #f9f9f9;
  padding: 15px;
  border-radius: 4px;
  border-left: 4px solid #4caf50;
}

.stat .label {
  display: block;
  color: #666;
  font-size: 0.9em;
  margin-bottom: 5px;
}

.stat .value {
  display: block;
  font-size: 1.5em;
  font-weight: bold;
  color: #333;
}
</style>
```

## Bash Script for Automation

```bash
#!/bin/bash
# Script to trigger and monitor memory dumps

DASHBOARD_API="http://localhost:8000"
DUMP_API="${DASHBOARD_API}/api/memory-dumps"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse arguments
if [ $# -eq 0 ]; then
    echo "Usage: $0 <vm1> <vm2> ... [--timeout SECONDS]"
    exit 1
fi

# Extract timeout if provided
TIMEOUT=3600
LAST_ARG="${@: -1}"
if [[ $LAST_ARG == --timeout ]]; then
    TIMEOUT="${@: -1}"
    set -- "${@:1:$#-2}"
fi

VMS=("$@")

echo -e "${GREEN}Triggering memory dumps for: ${VMS[@]}${NC}"

# Trigger dumps
RESPONSE=$(curl -s -X POST "${DUMP_API}/trigger" \
  -H "Content-Type: application/json" \
  -d "{\"vms\": [$(printf '"%s",' "${VMS[@]}" | sed 's/,$/')]}")

echo "Response: $RESPONSE"

# Poll for completion
START_TIME=$(date +%s)
while true; do
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - START_TIME))
    
    if [ $ELAPSED -gt $TIMEOUT ]; then
        echo -e "${RED}✗ Timeout after ${TIMEOUT} seconds${NC}"
        exit 1
    fi
    
    STATUS=$(curl -s "${DUMP_API}/status")
    
    # Parse and display status for each VM
    ALL_DONE=true
    for vm in "${VMS[@]}"; do
        VM_STATUS=$(echo "$STATUS" | grep -A5 "\"vm\": \"$vm\"" | head -5)
        
        if echo "$VM_STATUS" | grep -q '"state": "running"'; then
            PROGRESS=$(echo "$VM_STATUS" | grep -o '"progress": [0-9.]*' | cut -d' ' -f2)
            echo -e "${YELLOW}  $vm: running (${PROGRESS}%)${NC}"
            ALL_DONE=false
        elif echo "$VM_STATUS" | grep -q '"state": "queued"'; then
            echo -e "${YELLOW}  $vm: queued${NC}"
            ALL_DONE=false
        elif echo "$VM_STATUS" | grep -q '"state": "completed"'; then
            echo -e "${GREEN}  ✓ $vm: completed${NC}"
        elif echo "$VM_STATUS" | grep -q '"state": "failed"'; then
            MSG=$(echo "$VM_STATUS" | grep -o '"message": "[^"]*"' | cut -d'"' -f4)
            echo -e "${RED}  ✗ $vm: failed - $MSG${NC}"
        fi
    done
    
    if [ "$ALL_DONE" = true ]; then
        echo -e "${GREEN}✓ All dumps completed!${NC}"
        break
    fi
    
    sleep 5
done

# Get final records
echo -e "\n${GREEN}Recent dumps:${NC}"
curl -s "${DUMP_API}/records?limit=5" | python3 -m json.tool
```

## Docker Compose Example

```yaml
version: '3.8'

services:
  dashboard-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      MEMDUMP_SERVICE_URL: http://memdump-service:5001
      MEMDUMP_SERVICE_TIMEOUT: 30
      INFLUX_URL: http://influxdb:8181
      INFLUX_DB: vmstats
      INFLUX_TOKEN: ${INFLUX_TOKEN}
      LIBVIRT_URI: qemu:///system
    volumes:
      - /var/run/libvirt:/var/run/libvirt
    depends_on:
      - memdump-service
      - influxdb

  memdump-service:
    image: memdump-service:latest
    ports:
      - "5001:5001"
    environment:
      LIBVIRT_URI: qemu+ssh://user@remote-host/system
      DUMP_DIR: /dumps
      INFLUX_HOST: http://influxdb:8181
      INFLUX_DATABASE: vmstats
      INFLUX_TOKEN: ${INFLUX_TOKEN}
    volumes:
      - dump-storage:/dumps

  influxdb:
    image: influxdb:2.7-alpine
    ports:
      - "8181:8086"
    environment:
      INFLUXDB_ADMIN_TOKEN: ${INFLUX_TOKEN}
    volumes:
      - influxdb-storage:/var/lib/influxdb2

volumes:
  dump-storage:
  influxdb-storage:
```

## Testing with curl

```bash
# Trigger dumps
curl -X POST http://localhost:8000/api/memory-dumps/trigger \
  -H "Content-Type: application/json" \
  -d '{"vms": ["vm1", "vm2"]}'

# Get status
curl http://localhost:8000/api/memory-dumps/status

# Get specific VM status
curl http://localhost:8000/api/memory-dumps/status/vm1

# Get records
curl http://localhost:8000/api/memory-dumps/records?limit=10

# Get statistics
curl http://localhost:8000/api/memory-dumps/stats
```

These examples provide complete implementations for integrating the memory dump service in various contexts.
