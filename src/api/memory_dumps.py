"""
Memory Dumps API Module
Handles memory dump triggers and InfluxDB3 queries for dump records.
Uses same HTTP-based InfluxDB client as telemetry module for consistency.
Integrates with memdump_service running at 10.10.0.94:5001 for remote dumps.
"""

import logging
import requests
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks
import os
import json
import csv
import io

from src.telemetry.influx_query import InfluxQuery

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/memory-dumps", tags=["memory-dumps"])

# Configuration for memdump_service
MEMDUMP_SERVICE_URL = os.environ.get("MEMDUMP_SERVICE_URL", "http://10.10.0.94:5001")
MEMDUMP_SERVICE_TIMEOUT = float(os.environ.get("MEMDUMP_SERVICE_TIMEOUT", "30"))

# Global state for tracking active dump operations
active_dumps = {}


def _get_influx_query_client() -> Optional[InfluxQuery]:
    """
    Get InfluxDB query client - uses same HTTP-based approach as telemetry module.
    This ensures consistency across the entire project.
    """
    try:
        url = os.environ.get("INFLUX_URL", "http://localhost:8181")
        db = os.environ.get("INFLUX_DB", "vmstats")
        token = os.environ.get("INFLUX_TOKEN")

        if not token:
            logger.warning("INFLUX_TOKEN not set, InfluxDB queries may fail")
            return None

        return InfluxQuery(url=url, db=db, token=token)
    except Exception as e:
        logger.error(f"Failed to initialize InfluxDB query client: {e}")
        return None


# ---------------- InfluxDB v3 helpers (CSV over HTTP) ----------------

def _resolve_influx(client: InfluxQuery) -> Dict[str, Any]:
    """
    Normalize host/db/headers from your InfluxQuery wrapper.
    """
    host = getattr(client, "host", None) or getattr(client, "url", None) or ""
    host = host.rstrip("/")
    if not host:
        # last resort: peel base from any known endpoint inside the client (if present)
        qp = getattr(client, "query_endpoint", "") or ""
        host = qp.rstrip("/")
        for suf in ("/api/v3/query_sql", "/api/v3/query_influxql", "/query"):
            if host.endswith(suf):
                host = host[:-len(suf)]
                break
    if not host:
        raise RuntimeError("Cannot resolve Influx host from client")

    db = getattr(client, "db", None) or getattr(client, "database", None) or "vmstats"
    headers = dict(getattr(client, "headers", {}) or {})
    headers.setdefault("Accept", "text/csv")
    return {"host": host, "db": db, "headers": headers}


def _query_v3_csv(host: str, db: str, headers: Dict[str, str], sql: str, *,
                  use_influxql: bool = False, timeout: int = 15) -> str:
    """
    Run a CSV query against InfluxDB 3.x.
    - SQL endpoint:       /api/v3/query_sql   (default)
    - InfluxQL endpoint:  /api/v3/query_influxql (when use_influxql=True)
    Returns raw CSV text (may include commented meta lines starting with '#').
    """
    path = "/api/v3/query_influxql" if use_influxql else "/api/v3/query_sql"
    url = f"{host}{path}"
    resp = requests.get(url, params={"db": db, "q": sql}, headers=headers, timeout=timeout)
    if resp.status_code != 200:
        raise RuntimeError(f"{path} returned {resp.status_code}: {resp.text[:200]}")
    return resp.text


def _csv_to_dicts(csv_text: str) -> List[Dict[str, Any]]:
    """
    Convert v3 CSV response (possibly with leading '#' lines) into list of dicts.
    """
    # Drop comments/metadata
    lines = [ln for ln in csv_text.splitlines() if ln and not ln.startswith("#")]
    if not lines:
        return []
    reader = csv.DictReader(io.StringIO("\n".join(lines)))
    return [dict(row) for row in reader]


def _normalize_numeric(record: Dict[str, Any], numeric_int: List[str], numeric_float: List[str]) -> Dict[str, Any]:
    for k in numeric_int:
        if k in record and record[k] not in (None, ""):
            try:
                # values can come as '1854182509.0' → cast via float then int
                record[k] = int(float(record[k]))
            except Exception:
                pass
    for k in numeric_float:
        if k in record and record[k] not in (None, ""):
            try:
                record[k] = float(record[k])
            except Exception:
                pass
    return record


# ---------------- Background dump trigger ----------------

async def _trigger_dump_background(vm_ids: List[str]):
    """
    Background task to trigger memory dumps via memdump_service HTTP API.
    Polls the service for status until completion.
    """
    try:
        service_url = MEMDUMP_SERVICE_URL.rstrip("/")
        
        logger.info(f"🚀 Triggering memory dump for VMs: {vm_ids}")
        logger.info(f"   Service URL: {service_url}/api/dumps")

        # Step 1: POST request to trigger dumps
        payload = {"vms": vm_ids}
        response = requests.post(
            f"{service_url}/api/dumps",
            json=payload,
            timeout=MEMDUMP_SERVICE_TIMEOUT
        )
        
        if response.status_code != 200:
            error_msg = f"memdump_service returned {response.status_code}: {response.text[:200]}"
            logger.error(f"❌ {error_msg}")
            active_dumps['last_trigger'] = {
                'timestamp': datetime.now().isoformat(),
                'vm_ids': vm_ids,
                'status': 'failed',
                'error': error_msg
            }
            return
        
        trigger_response = response.json()
        logger.info(f"✓ Dump trigger accepted: {trigger_response}")
        
        # Record start time
        start_time = datetime.now()
        active_dumps['last_trigger'] = {
            'timestamp': start_time.isoformat(),
            'vm_ids': vm_ids,
            'status': 'in_progress',
            'trigger_response': trigger_response
        }
        
        # Step 2: Poll for status of each VM
        import time
        max_wait_sec = 3600  # 1 hour max wait
        poll_interval_sec = 5
        elapsed = 0
        
        all_completed = False
        while elapsed < max_wait_sec:
            try:
                # Get status for all VMs
                status_response = requests.get(
                    f"{service_url}/api/dumps",
                    timeout=MEMDUMP_SERVICE_TIMEOUT
                )
                
                if status_response.status_code != 200:
                    logger.warning(f"Status poll returned {status_response.status_code}")
                    time.sleep(poll_interval_sec)
                    elapsed += poll_interval_sec
                    continue
                
                dump_statuses = status_response.json()
                
                # Check if all requested VMs are done
                all_completed = True
                for vm_id in vm_ids:
                    vm_status = dump_statuses.get(vm_id)
                    if not vm_status:
                        logger.debug(f"  {vm_id}: no status yet")
                        all_completed = False
                    elif vm_status.get('state') in ('running', 'queued'):
                        logger.debug(f"  {vm_id}: {vm_status.get('state')} ({vm_status.get('progress', 0):.1f}%)")
                        all_completed = False
                    elif vm_status.get('state') == 'completed':
                        logger.info(f"  ✓ {vm_id}: completed in {vm_status.get('duration_sec', 0):.2f}s")
                    elif vm_status.get('state') == 'failed':
                        logger.error(f"  ✗ {vm_id}: failed - {vm_status.get('message', 'unknown error')}")
                
                if all_completed:
                    logger.info("✓ All dumps completed!")
                    end_time = datetime.now()
                    duration = (end_time - start_time).total_seconds()
                    active_dumps['last_trigger']['status'] = 'completed'
                    active_dumps['last_trigger']['duration'] = duration
                    active_dumps['last_trigger']['dump_statuses'] = dump_statuses
                    return
                
                time.sleep(poll_interval_sec)
                elapsed += poll_interval_sec
                
            except Exception as e:
                logger.warning(f"Error polling dump status: {e}")
                time.sleep(poll_interval_sec)
                elapsed += poll_interval_sec
        
        # Timeout reached
        logger.error(f"Dump monitoring timed out after {max_wait_sec}s")
        active_dumps['last_trigger']['status'] = 'timeout'
        
    except requests.ConnectionError as e:
        error_msg = f"Cannot connect to memdump_service at {MEMDUMP_SERVICE_URL}: {e}"
        logger.error(f"❌ {error_msg}")
        active_dumps['last_trigger'] = {
            'timestamp': datetime.now().isoformat(),
            'vm_ids': vm_ids,
            'status': 'error',
            'error': error_msg
        }
    except Exception as e:
        logger.exception(f"Background dump task failed: {e}")
        active_dumps['last_trigger'] = {
            'timestamp': datetime.now().isoformat(),
            'vm_ids': vm_ids,
            'status': 'error',
            'error': str(e)
        }


@router.post("/trigger")
async def trigger_dump(
    request_body: Dict[str, List[str]],
    background_tasks: BackgroundTasks
):
    """
    Trigger memory dumps for specified VMs via memdump_service.
    
    Forwards dump request to memdump_service running at MEMDUMP_SERVICE_URL.

    Request body (either format accepted):
    {
        "vm_ids": ["vm1", "vm2", ...]
    }
    OR
    {
        "vms": ["vm1", "vm2", ...]
    }
    """
    try:
        # Accept both 'vm_ids' and 'vms' parameter names
        vm_ids = request_body.get('vm_ids') or request_body.get('vms') or []

        if not vm_ids:
            raise HTTPException(status_code=400, detail="No VMs specified. Use 'vm_ids' or 'vms' parameter")

        logger.info(f"📋 Dump request received for {len(vm_ids)} VMs: {vm_ids}")

        # Add background task to trigger dumps
        background_tasks.add_task(_trigger_dump_background, vm_ids)

        return {
            "status": "scheduled",
            "message": f"Memory dump scheduled for {len(vm_ids)} VM(s)",
            "vm_ids": vm_ids,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error in trigger_dump: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_dump_status():
    """
    Get status of active dump operations from memdump_service.
    
    Returns status from the remote memdump_service for all VMs that have active dumps.
    """
    try:
        service_url = MEMDUMP_SERVICE_URL.rstrip("/")
        
        # Query memdump_service for all dump statuses
        response = requests.get(
            f"{service_url}/api/dumps",
            timeout=MEMDUMP_SERVICE_TIMEOUT
        )
        
        if response.status_code != 200:
            logger.warning(f"memdump_service /api/dumps returned {response.status_code}")
            return {
                "service": service_url,
                "status": "unavailable",
                "error": f"Service returned {response.status_code}"
            }
        
        dump_statuses = response.json()
        
        return {
            "service": service_url,
            "status": "ok",
            "active_dumps": dump_statuses,
            "last_trigger": active_dumps.get('last_trigger'),
            "timestamp": datetime.now().isoformat()
        }
        
    except requests.ConnectionError as e:
        logger.warning(f"Cannot reach memdump_service: {e}")
        return {
            "service": MEMDUMP_SERVICE_URL,
            "status": "unavailable",
            "error": f"Connection failed: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.exception(f"Error checking dump status: {e}")
        raise HTTPException(status_code=500, detail=f"Error checking dump status: {str(e)}")


@router.get("/status/{vm_id}")
async def get_dump_status_for_vm(vm_id: str):
    """
    Get status of a specific VM's dump from memdump_service.
    
    Returns:
    - dump_id: unique identifier for this dump operation
    - state: "queued", "running", "completed", or "failed"
    - progress: 0-100 percentage (for running dumps)
    - message: status message
    - started_at: timestamp when dump started
    - finished_at: timestamp when dump completed/failed
    - dump_path: path to the memory dump file
    - duration_sec: how long the dump took
    """
    try:
        service_url = MEMDUMP_SERVICE_URL.rstrip("/")
        
        # Query memdump_service for specific VM status
        response = requests.get(
            f"{service_url}/api/dumps/{vm_id}",
            timeout=MEMDUMP_SERVICE_TIMEOUT
        )
        
        if response.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail=f"No dump status for VM '{vm_id}'"
            )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"memdump_service error: {response.text[:200]}"
            )
        
        return response.json()
        
    except requests.ConnectionError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Cannot connect to memdump_service: {str(e)}"
        )
    except Exception as e:
        logger.exception(f"Error getting dump status for VM {vm_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------- Records API ----------------

@router.get("/records")
async def get_dump_records(limit: int = 1000, offset: int = 0):
    """
    Fetch memory dump records written by the memory-dump module.

    Tries InfluxDB 3.x SQL first (/api/v3/query_sql, CSV),
    then falls back to InfluxQL (/api/v3/query_influxql, CSV).
    """
    if limit <= 0:
        limit = 1000
    if offset < 0:
        offset = 0

    expected_cols = [
        "time", "dom", "vmid", "sha256", "duration_sec",
        "gzip_size_bytes", "ctime", "mtime", "atime", "dump_path"
    ]

    query_sql = (
        "SELECT time, dom, vmid, sha256, duration_sec, gzip_size_bytes, "
        "ctime, mtime, atime, dump_path "
        "FROM mem_dumps "
        "ORDER BY time DESC "
        f"LIMIT {int(limit)} OFFSET {int(offset)}"
    )

    try:
        client = _get_influx_query_client()
        if not client:
            return {"records": [], "count": 0, "limit": limit, "offset": offset,
                    "error": "InfluxDB query client not available"}

        cfg = _resolve_influx(client)
        host, db, headers = cfg["host"], cfg["db"], cfg["headers"]

        logger.info(f"🔍 Query mem_dumps (limit={limit}, offset={offset})")

        # 1) Try SQL
        try:
            csv_text = _query_v3_csv(host, db, headers, query_sql, use_influxql=False)
            rows = _csv_to_dicts(csv_text)
            if rows:
                # normalize numeric types
                records = []
                for row in rows:
                    rec = {k: row.get(k) for k in expected_cols}
                    rec = _normalize_numeric(rec,
                                             numeric_int=["gzip_size_bytes", "ctime", "mtime", "atime"],
                                             numeric_float=["duration_sec"])
                    records.append(rec)
                logger.info(f"✓ Retrieved {len(records)} (v3 SQL CSV)")
                return {"records": records, "count": len(records), "limit": limit, "offset": offset}
            logger.warning("v3 SQL returned 200 but no rows parsed")
        except Exception as e:
            logger.warning(f"v3 SQL request error: {e}")

        # 2) Fallback: InfluxQL
        try:
            csv_text = _query_v3_csv(host, db, headers, query_sql, use_influxql=True)
            rows = _csv_to_dicts(csv_text)
            records = []
            for row in rows:
                rec = {k: row.get(k) for k in expected_cols}
                rec = _normalize_numeric(rec,
                                         numeric_int=["gzip_size_bytes", "ctime", "mtime", "atime"],
                                         numeric_float=["duration_sec"])
                records.append(rec)
            logger.info(f"✓ Retrieved {len(records)} (v3 InfluxQL CSV)")
            return {"records": records, "count": len(records), "limit": limit, "offset": offset}
        except Exception as e:
            logger.error(f"v3 InfluxQL request error: {e}")
            return {"records": [], "count": 0, "limit": limit, "offset": offset,
                    "error": "InfluxQL request failed"}

    except Exception as e:
        logger.exception(f"Error fetching dump records: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching records: {str(e)}")


# ---------------- Stats API ----------------

@router.get("/stats")
async def get_dump_stats():
    """
    Get statistics about memory dumps from InfluxDB3 (v3 SQL, CSV).
    """
    try:
        client = _get_influx_query_client()
        if not client:
            return {
                "error": "InfluxDB query client not available",
                "total_dumps": 0,
                "total_vms": 0,
                "total_size_bytes": 0,
                "avg_duration_sec": 0.0,
                "last_dump": None
            }

        cfg = _resolve_influx(client)
        host, db, headers = cfg["host"], cfg["db"], cfg["headers"]

        logger.info("📊 Querying dump statistics from InfluxDB3 (SQL/CSV)")

        stats = {
            "total_dumps": 0,
            "total_vms": 0,
            "total_size_bytes": 0,
            "avg_duration_sec": 0.0,
            "last_dump": None
        }

        # COUNT(*)
        try:
            q = "SELECT COUNT(*) AS count FROM mem_dumps"
            rows = _csv_to_dicts(_query_v3_csv(host, db, headers, q))
            if rows and "count" in rows[0]:
                stats["total_dumps"] = int(float(rows[0]["count"]))
        except Exception as e:
            logger.warning(f"COUNT(*) failed: {e}")

        # COUNT(DISTINCT vmid)
        try:
            q = "SELECT COUNT(DISTINCT vmid) AS unique_vms FROM mem_dumps"
            rows = _csv_to_dicts(_query_v3_csv(host, db, headers, q))
            if rows and "unique_vms" in rows[0]:
                stats["total_vms"] = int(float(rows[0]["unique_vms"]))
        except Exception as e:
            logger.warning(f"COUNT DISTINCT vmid failed: {e}")

        # SUM(gzip_size_bytes)
        try:
            q = "SELECT SUM(gzip_size_bytes) AS total_size FROM mem_dumps"
            rows = _csv_to_dicts(_query_v3_csv(host, db, headers, q))
            if rows and "total_size" in rows[0] and rows[0]["total_size"] not in (None, ""):
                stats["total_size_bytes"] = int(float(rows[0]["total_size"]))
        except Exception as e:
            logger.warning(f"SUM(gzip_size_bytes) failed: {e}")

        # MEAN(duration_sec)
        try:
            q = "SELECT MEAN(duration_sec) AS avg_duration FROM mem_dumps"
            rows = _csv_to_dicts(_query_v3_csv(host, db, headers, q))
            if rows and "avg_duration" in rows[0] and rows[0]["avg_duration"] not in (None, ""):
                stats["avg_duration_sec"] = float(rows[0]["avg_duration"])
        except Exception as e:
            logger.warning(f"MEAN(duration_sec) failed: {e}")

        # Latest time
        try:
            q = "SELECT time FROM mem_dumps ORDER BY time DESC LIMIT 1"
            rows = _csv_to_dicts(_query_v3_csv(host, db, headers, q))
            if rows and "time" in rows[0]:
                stats["last_dump"] = rows[0]["time"]
        except Exception as e:
            logger.warning(f"Latest time fetch failed: {e}")

        logger.info(
            f"✓ Stats: dumps={stats['total_dumps']}, vms={stats['total_vms']}, "
            f"bytes={stats['total_size_bytes']}, avg_s={stats['avg_duration_sec']}, "
            f"last={stats['last_dump']}"
        )
        return stats

    except Exception as e:
        logger.exception(f"Error getting dump stats: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting dump stats: {str(e)}")
