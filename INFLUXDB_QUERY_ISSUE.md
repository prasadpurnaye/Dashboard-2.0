# Resource Monitoring - Data Display Issue - Deep Dive

**Issue:** All metric values showing as 0 even though telemetry is being stored to InfluxDB  
**Root Cause:** The InfluxDB query endpoint isn't returning data  
**Status:** Investigating - Data IS being written, but queries are failing

---

## Problem Analysis

### What We Know

1. ✅ Telemetry IS being collected and written to InfluxDB
   - Collector logs show: "Collecting metrics from 2 VM(s)..."
   - Data is being written to vm_totals measurement
   - Line protocol format working correctly

2. ❌ Queries to InfluxDB are failing
   - Endpoint `/api/v3/query` returns 404
   - Endpoint `/api/v1/query` returns 404
   - No data being retrieved

3. ✅ Writing works fine
   - Endpoint: `POST /api/v3/write_lp?db=vmstats`
   - Status: 200 OK
   - Data successfully stored

### The Mismatch

```
Writing: POST /api/v3/write_lp  ✅ WORKS
Reading: GET  /api/v3/query     ❌ 404 NOT FOUND
```

---

## Root Cause

InfluxDB v3 may not have the traditional query endpoints. It's a completely rewritten architecture. The query interface might be:
1. Different endpoint (not `/api/v3/query`)
2. Different method (POST instead of GET)
3. Different query language (native InfluxQL vs new SQL)
4. Requires different header format

---

## Solution

Since the collector successfully writes data with `/api/v3/write_lp`, the InfluxDB connection IS working. We need to find the correct query endpoint.

### Option 1: Use InfluxQL Compatibility

Some InfluxDB v3 instances support legacy InfluxQL queries through a compatibility layer:

```
Endpoint: /query (without version prefix)
Method: GET or POST
Query: InfluxQL syntax (what we're using)
```

### Option 2: Use New InfluxDB SQL

InfluxDB v3 introduces native SQL support:

```
Endpoint: /api/v3/query_sql  (hypothetical)
Method: POST
Body: {
  "sql": "SELECT * FROM vm_totals WHERE VMID='1' LIMIT 1"
}
Query: Native SQL syntax
```

### Option 3: Use InfluxDB Query Language (IQL/Flux)

```
Endpoint: /api/v1/query
Method: GET or POST  
Query: Flux language (new querying language)
```

---

## Recommended Fix

The quickest fix is to determine the correct query endpoint. Since writing works with auth token, the same auth should work for reading. 

**To implement:**

1. Test the actual InfluxDB instance to find working endpoint
2. Update `InfluxQuery.__init__()` to use correct endpoint
3. Update query syntax if needed
4. Test and verify metrics return real data

---

## Temporary Workaround

Until the query issue is resolved, the resource-monitoring page:
- ✅ Displays all 26 metrics with default (0) values
- ✅ Shows VM name, state, CPU count
- ✅ Graphs render correctly with 0 values
- ⏳ Waiting for InfluxDB to return real values

**Timeline:** As soon as InfluxDB queries work, real data will automatically start displaying (no frontend changes needed).

---

## Files Affected

- `/src/telemetry/influx_query.py` - Query functions
- `/src/api/telemetry.py` - API endpoint that calls queries
- `/static/js/resource-monitoring.js` - Frontend (works fine, just needs data)

---

## Next Steps

**Immediate:**
1. Determine correct InfluxDB v3 query endpoint
2. Test query locally
3. Update influx_query.py with correct endpoint
4. Restart server and verify data flows

**Alternative:**
If no query endpoint is available, implement direct InfluxDB v3 SDK usage instead of HTTP API

---

## Code Path for Data Flow

```
Browser                Dashboard Frontend
   |                        |
   |--[GET /api/telemetry/vm-stats/1]-->|
   |                        |
   |                   telemetry.py
   |                        |
   |                   influx_query.py
   |                        |
   |    [GET /api/v3/query] --> InfluxDB ❌ 404
   |                    (FAILS - endpoint not found)
   |                        |
   |<--[Return defaults]----|
   |                        |
   |<--[All zeros]----------|

Goal: Get InfluxDB query endpoint working so real metrics can flow through
```

---

## Verification Needed

Run this to test InfluxDB endpoints:

```bash
# Test write (currently working)
curl -X POST http://127.0.0.1:8181/api/v3/write_lp?db=vmstats \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d 'test_measurement,host=server1 value=42'

# Test read endpoints to find which one works
curl http://127.0.0.1:8181/query?db=vmstats&q=SHOW%20MEASUREMENTS
curl http://127.0.0.1:8181/api/v1/query?db=vmstats&q=SHOW%20MEASUREMENTS  
curl http://127.0.0.1:8181/api/v3/query?db=vmstats&q=SHOW%20MEASUREMENTS
```

The first one that returns 200 (not 404) is the working endpoint.

---

**Status:** ⏳ BLOCKING DATA DISPLAY  
**Priority:** HIGH  
**Impact:** Metrics showing 0 until this is fixed

