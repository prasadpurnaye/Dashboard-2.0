"""
Memory Dumps API Module
Handles memory dump triggers and InfluxDB3 queries for dump records.
Uses same HTTP-based InfluxDB client as telemetry module for consistency.
"""

import logging
import requests
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks
import os
import subprocess
import json
import csv
import io

from src.telemetry.influx_query import InfluxQuery

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/memory-dumps", tags=["memory-dumps"])

# Global state for tracking active dump operations
active_dumps = {}


def _get_memdump_script_path():
    """Get the path to the memdump.py script"""
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    script_path = os.path.join(base_path, "..", "memdump.py")
    return os.path.abspath(script_path)


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
    """Background task to trigger memory dumps"""
    try:
        script_path = _get_memdump_script_path()

        if not os.path.exists(script_path):
            logger.warning(f"memdump.py script not found at {script_path}, skipping dump")
            return

        # Record start time
        start_time = datetime.now()
        active_dumps['last_trigger'] = {
            'timestamp': start_time.isoformat(),
            'vm_ids': vm_ids,
            'status': 'in_progress'
        }

        logger.info(f"🚀 Starting memory dump for VMs: {vm_ids}")

        # Execute memdump.py script with VM IDs
        try:
            result = subprocess.run(
                ['python3', script_path] + vm_ids,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout per dump
            )

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            if result.returncode == 0:
                logger.info(f"✓ Memory dump completed successfully in {duration:.2f}s")
                active_dumps['last_trigger']['status'] = 'completed'
                active_dumps['last_trigger']['duration'] = duration
            else:
                logger.error(f"Memory dump failed with return code {result.returncode}")
                logger.error(f"stdout: {result.stdout}")
                logger.error(f"stderr: {result.stderr}")
                active_dumps['last_trigger']['status'] = 'failed'
                active_dumps['last_trigger']['error'] = result.stderr

        except subprocess.TimeoutExpired:
            logger.error("Memory dump timed out after 5 minutes")
            active_dumps['last_trigger']['status'] = 'timeout'
        except Exception as e:
            logger.exception(f"Unexpected error during memory dump: {e}")
            active_dumps['last_trigger']['status'] = 'error'
            active_dumps['last_trigger']['error'] = str(e)

    except Exception as e:
        logger.exception(f"Background dump task failed: {e}")


@router.post("/trigger")
async def trigger_dump(
    request_body: Dict[str, List[str]],
    background_tasks: BackgroundTasks
):
    """
    Trigger memory dumps for specified VMs

    Request body:
    {
        "vm_ids": ["vm1", "vm2", ...]
    }
    """
    try:
        vm_ids = request_body.get('vm_ids', [])

        if not vm_ids:
            raise HTTPException(status_code=400, detail="No VM IDs specified")

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
