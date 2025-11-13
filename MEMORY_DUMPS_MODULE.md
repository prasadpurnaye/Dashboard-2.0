# Memory Dump Management Module - Complete Documentation

## Overview

The Memory Dump Management module provides a comprehensive interface for managing memory dumps of virtual machines. It integrates with InfluxDB3 to store and retrieve dump metadata, and uses the `memdump.py` script to trigger actual memory dumps through the KVM/QEMU infrastructure.

## Features

### 🎯 Core Capabilities

1. **Responsive Navbar Navigation**
   - Fixed navigation bar across all pages
   - Active page indicator
   - Mobile-responsive design
   - Quick access to all dashboard modules

2. **Dump Trigger Controls**
   - Trigger dumps for individual VMs
   - Trigger dumps for all VMs simultaneously
   - Background task management
   - Real-time status feedback

3. **VM Management**
   - Dynamic VM selection from libvirt
   - Live VM list fetching
   - VM ID and name display
   - Status tracking

4. **InfluxDB3 Integration**
   - Query dump records from InfluxDB3
   - Display comprehensive dump metadata
   - Real-time data updates
   - Advanced filtering and search

5. **Data Management**
   - Tabular display of dump records
   - Pagination support
   - Search and filter capabilities
   - CSV export functionality
   - Date-based filtering

6. **Activity Monitoring**
   - Real-time activity log
   - Success/error/info notifications
   - Auto-refresh option
   - Toast notifications for feedback

7. **Modal Details View**
   - Detailed dump information popup
   - SHA256 hash copying
   - Full metadata display
   - Professional presentation

## Architecture

### Frontend Structure

#### HTML (`templates/memory-dumps.html`)
- Responsive navbar matching existing dashboard
- Control panel for dump triggers
- Status information display
- Activity log section
- Data table with metadata
- Modal for detailed views
- Toast notification container

#### CSS (`static/css/memory-dumps.css`)
- ~850 lines of comprehensive styling
- Responsive grid layouts
- Mobile-first design approach
- Accessibility features
- Professional color scheme
- Smooth animations and transitions
- Reduced motion support

#### JavaScript (`static/js/memory-dumps.js`)
- `MemoryDumpManager` class for state management
- Real-time data fetching and updates
- Filter and search functionality
- Pagination logic
- CSV export capability
- Activity logging
- Toast notifications

### Backend API Routes

#### Core Endpoints

**1. POST `/api/memory-dumps/trigger`**
```
Purpose: Trigger memory dumps for specified VMs
Request:
{
    "vm_ids": ["vm1", "vm2", ...]
}
Response:
{
    "status": "scheduled",
    "message": "Memory dump scheduled for X VM(s)",
    "vm_ids": [...],
    "timestamp": "2025-11-11T10:30:00.000000"
}
```

**2. GET `/api/memory-dumps/records`**
```
Purpose: Fetch dump records from InfluxDB3
Query Parameters:
- limit (int): Max records to return (default: 1000)
- offset (int): Pagination offset (default: 0)
Response:
{
    "records": [
        {
            "timestamp": "2025-11-11T10:30:00.000000",
            "dom": "vm-name",
            "vmid": "101",
            "sha256": "abc123...",
            "duration_sec": 5.23,
            "gzip_size_bytes": 2147483648,
            "ctime": 1699520400,
            "mtime": 1699520405,
            "atime": 1699520410,
            "dump_path": "/var/dumps/101_1699520400.mem.gz"
        }
    ],
    "count": 1,
    "limit": 1000,
    "offset": 0
}
```

**3. GET `/api/memory-dumps/status`**
```
Purpose: Get status of last dump operation
Response:
{
    "status": "completed",
    "vm_ids": ["101", "102"],
    "timestamp": "2025-11-11T10:30:00.000000",
    "duration": 5.23,
    "error": null
}
```

**4. GET `/api/memory-dumps/stats`**
```
Purpose: Get aggregate statistics from InfluxDB3
Response:
{
    "total_dumps": 42,
    "total_vms": 5,
    "total_size_bytes": 107374182400,
    "avg_duration_sec": 4.56,
    "last_dump": "2025-11-11T10:30:00.000000"
}
```

## Data Flow

### Dump Trigger Flow

```
User Action
    ↓
JavaScript: dumpSelectedVM() / dumpAllVMs()
    ↓
POST /api/memory-dumps/trigger
    ↓
Backend: Background Task (_trigger_dump_background)
    ↓
Execute: python3 memdump.py <vm_ids>
    ↓
memdump.py: Connect to libvirt
    ↓
memdump.py: Core dump each VM
    ↓
memdump.py: Calculate SHA256 and compress
    ↓
memdump.py: Write to InfluxDB3 line protocol
    ↓
InfluxDB3: Store mem_dumps measurement
```

### Data Display Flow

```
User: Auto-refresh enabled (5s interval)
    ↓
JavaScript: setInterval -> loadDumpsFromInfluxDB()
    ↓
GET /api/memory-dumps/records
    ↓
Backend: Query InfluxDB3 mem_dumps table
    ↓
Response: Array of dump records
    ↓
JavaScript: applyFilters()
    ↓
JavaScript: renderTable() with pagination
    ↓
DOM: Update table display
```

## UI Components

### Control Panel
- **Dump Trigger Section**
  - VM selector dropdown (dynamically populated)
  - "Dump Selected VM" button (disabled until selection)
  - "Dump All VMs" button

- **Status Information Section**
  - Total VMs counter
  - Total dumps counter
  - Last dump timestamp

- **Filters & Options Section**
  - Text search box (searches VM name or hash)
  - Date filter (YYYY-MM-DD format)
  - Reset filters button
  - Auto-refresh toggle (5-second interval)
  - Show compressed size toggle

### Activity Log
- Real-time updates
- Color-coded by type (success, error, info)
- Auto-scrolling
- Last 20 items retained
- Activity count badge

### Data Table
- 8 columns: VM ID, VM Name, Timestamp, Duration, SHA256, Path, Size, Actions
- Sortable by timestamp (descending)
- Hover effects
- Responsive design
- Zebra striping for readability

### Actions Column
- **View Button**: Opens modal with full details
- **Copy Button**: Copies SHA256 hash to clipboard

### Pagination
- Previous/Next buttons
- Page indicator
- Record count
- Disabled state when at boundaries

### Modal
- Full dump details display
- Copy hash button
- Professional styling
- Keyboard support (ESC to close)
- Click-outside to close

### Notifications
- Toast notifications (success, error, warning, info)
- 3-second auto-dismiss
- Stacked display
- Slide-in/out animation

## Environment Configuration

Required environment variables:

```bash
# InfluxDB3 Configuration
INFLUX_URL=http://localhost:8181
INFLUX_DB=vmstats
INFLUX_TOKEN=your-token-here

# Memory Dump Configuration
DUMP_DIR=/var/dumps
MEMDUMP_LOG_DIR=/var/log

# Libvirt Configuration
LIBVIRT_URI=qemu+ssh://oneadmin@192.168.0.104/system
```

## InfluxDB3 Schema

### Measurement: `mem_dumps`

#### Tags:
- `dom`: Virtual machine domain name
- `vmid`: Virtual machine ID

#### Fields:
- `sha256` (string): SHA256 hash of dump file
- `duration_sec` (float): Dump operation duration in seconds
- `gzip_size_bytes` (integer): Compressed dump size
- `ctime` (integer): File creation timestamp
- `mtime` (integer): File modification timestamp
- `atime` (integer): File access timestamp
- `dump_path` (string): Full path to compressed dump file

#### Example Record:
```
mem_dumps,dom=vm-web-01,vmid=101 \
    sha256="a1b2c3d4e5f6...",\
    duration_sec=5.23,\
    gzip_size_bytes=2147483648,\
    ctime=1699520400,\
    mtime=1699520405,\
    atime=1699520410,\
    dump_path="/var/dumps/101_1699520400.mem.gz" \
    1699520400000000000
```

## API Usage Examples

### JavaScript - Trigger Single VM Dump
```javascript
const vm_ids = ['101'];
const response = await fetch('/api/memory-dumps/trigger', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ vm_ids })
});
const result = await response.json();
console.log(result.message); // "Memory dump scheduled for 1 VM(s)"
```

### JavaScript - Fetch Dump Records
```javascript
const response = await fetch('/api/memory-dumps/records?limit=50&offset=0');
const data = await response.json();
console.log(`Total dumps: ${data.count}`);
data.records.forEach(dump => {
    console.log(`${dump.dom}: ${dump.gzip_size_bytes} bytes`);
});
```

### cURL - Get Statistics
```bash
curl -X GET http://localhost:8000/api/memory-dumps/stats
```

### Python - Query via Script
```python
import requests

# Get dump records
response = requests.get('http://localhost:8000/api/memory-dumps/records?limit=100')
dumps = response.json()['records']

# Get statistics
stats = requests.get('http://localhost:8000/api/memory-dumps/stats').json()
print(f"Total: {stats['total_dumps']} dumps, {stats['total_size_bytes']} bytes")
```

## Responsive Design

### Breakpoints

- **Desktop (1024px+)**
  - Multi-column grid layouts
  - Full action button set
  - Expanded table display

- **Tablet (768px-1023px)**
  - 2-column grids adjusting to single
  - Reduced padding
  - Optimized button sizing

- **Mobile (480px-767px)**
  - Single-column layout
  - Stacked buttons
  - Compact table
  - Reduced font sizes

- **Small Mobile (<480px)**
  - Extra padding reduction
  - Minimal element sizing
  - Touch-friendly spacing

## Accessibility Features

- ✅ ARIA labels on interactive elements
- ✅ Keyboard navigation (Tab, Enter, ESC)
- ✅ Focus states on all buttons
- ✅ Color contrast compliance
- ✅ Reduced motion support
- ✅ Semantic HTML structure
- ✅ Screen reader friendly
- ✅ Form input accessibility

## Performance Considerations

1. **Pagination**: Limits default records to 1000 per query
2. **Auto-refresh**: 5-second interval (user-configurable)
3. **Filter Debouncing**: Applied on input change
4. **Lazy Loading**: Modal details loaded on demand
5. **CSV Export**: Handles large datasets efficiently
6. **Activity Log**: Limited to 20 recent items

## Error Handling

### Frontend Error Handling
- Try-catch blocks on all async operations
- User-friendly error messages
- Toast notifications for feedback
- Detailed console logging for debugging
- Graceful degradation on failures

### Backend Error Handling
- InfluxDB connection validation
- Query error fallback mechanisms
- Subprocess timeout handling (5 minutes)
- Process return code validation
- Comprehensive logging

### User Feedback
- Toast notifications (4 types)
- Activity log entries
- Status displays
- Error messages in modals
- Disabled state on buttons during operations

## Security Considerations

1. **Input Validation**
   - VM IDs validated before execution
   - Search/filter inputs sanitized
   - HTML escaping on all user-generated content

2. **Command Injection Prevention**
   - Subprocess arguments as list (not shell command)
   - No shell=True in subprocess calls
   - Environment variable validation

3. **Data Protection**
   - SHA256 hashes displayed (not full file access)
   - Paths displayed for reference (no file operations from UI)
   - Read-only operations on InfluxDB queries

4. **Access Control**
   - Coordinate with overall dashboard authentication
   - Environment variables for sensitive data
   - No hardcoded credentials

## Troubleshooting

### Dumps Not Appearing in Table
1. Verify InfluxDB3 is running: `curl http://localhost:8181/healthz`
2. Check INFLUX_TOKEN is valid
3. Verify memdump.py script exists and is executable
4. Check server logs: `tail -f /var/log/memdump_to_influx.log`

### Auto-refresh Not Working
1. Verify checkbox is checked
2. Check browser console for errors
3. Check network tab for failed requests
4. Verify `/api/memory-dumps/records` endpoint is responding

### VM Selector Empty
1. Verify libvirt is running on configured host
2. Check LIBVIRT_URI is correct
3. Verify SSH keys configured for authentication
4. Check `/api/telemetry/live-vms` endpoint

### CSV Export Empty
1. Verify table has records (not filtered out)
2. Check browser console for errors
3. Verify browser allows downloads
4. Try refreshing data first

## Future Enhancements

- [ ] Schedule recurring dumps
- [ ] Retention policy management
- [ ] Dump comparison tool
- [ ] Advanced InfluxDB queries (aggregations, time ranges)
- [ ] Dump file download (direct from dashboard)
- [ ] Concurrent dump limits
- [ ] Dump compression algorithm selection
- [ ] Email notifications on completion
- [ ] Webhook integration
- [ ] Multi-tenant support

## File Structure

```
dashboard-2.0/
├── templates/
│   └── memory-dumps.html          # Main HTML template
├── static/
│   ├── css/
│   │   └── memory-dumps.css       # Module-specific styles (~850 lines)
│   └── js/
│       └── memory-dumps.js        # Frontend logic (~500 lines)
├── src/
│   ├── api/
│   │   └── memory_dumps.py        # Backend API routes (~300 lines)
│   └── main.py                    # Updated with new route
└── memdump.py                     # Dump trigger script (provided)
```

## Summary Statistics

- **HTML Lines**: 180
- **CSS Lines**: 850
- **JavaScript Lines**: 500
- **Python API Lines**: 300
- **Total New Code**: ~1,830 lines
- **API Endpoints**: 4
- **UI Sections**: 6 (navbar, controls, status, filters, activity, table)
- **Responsive Breakpoints**: 4
- **Accessibility Features**: 8+

## Conclusion

The Memory Dump Management module provides enterprise-grade memory dump management with a modern, responsive UI and robust backend integration with InfluxDB3. It seamlessly integrates into the existing Dashboard 2.0 framework while maintaining design consistency and usability standards.
