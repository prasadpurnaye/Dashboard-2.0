#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTTP-based memory dump service for KVM/libvirt VMs.

Features:
- Remote trigger: POST /api/dumps to request dumps for one/more VMs
- Progress tracking per VM (approximate via growing .mem size vs maxMemory)
- Threaded execution with a cap on concurrent dumps (MAX_PARALLEL_DUMPS)
- Per-VM exclusion: at most one active dump per VM
- InfluxDB3 metadata logging with backlog file on failure (like memdump_continuousVer2_FIXED.py)

Start:
  uvicorn memdump_service:app --host 0.0.0.0 --port 5001

ENV:
  LIBVIRT_URI          default "qemu:///system"
  DUMP_DIR             default "/home/r/Desktop/"
  INFLUX_HOST          default "http://10.10.0.90:8181"
  INFLUX_DATABASE      default "vmstats"
  INFLUX_TOKEN         (optional)
  INFLUX_TIMEOUT_S     default "10"
  INFLUX_ORG           default "influxdata"
  INFLUX_BUCKET        default "vmstats"
  INFLUX_BACKLOG_PATH  default "<DUMP_DIR>/memdump_influx_backlog.lp"
  MAX_PARALLEL_DUMPS   default "2"   # max concurrent dumps
"""

import os
import sys
import time
import math
import stat
import uuid
import hashlib
import logging
import threading
from datetime import datetime
from typing import Dict, Any, Optional

import libvirt
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# ----------------------------- config ------------------------------

LIBVIRT_URI      = os.environ.get("LIBVIRT_URI", "qemu:///system")
DUMP_DIR         = os.environ.get("DUMP_DIR", "/home/r/Desktop/")

INFLUX_HOST      = os.environ.get("INFLUX_HOST", "http://10.10.0.90:8181").rstrip("/")
INFLUX_DATABASE  = os.environ.get("INFLUX_DATABASE", "vmstats")
INFLUX_TOKEN     = os.environ.get("INFLUX_TOKEN", "")
INFLUX_TIMEOUT_S = float(os.environ.get("INFLUX_TIMEOUT_S", "10"))

INFLUX_ORG       = os.environ.get("INFLUX_ORG", "influxdata")
INFLUX_BUCKET    = os.environ.get("INFLUX_BUCKET", "vmstats")

INFLUX_BACKLOG_PATH = os.environ.get(
    "INFLUX_BACKLOG_PATH",
    os.path.join(DUMP_DIR, "memdump_influx_backlog.lp")
)

MAX_PARALLEL_DUMPS = int(os.environ.get("MAX_PARALLEL_DUMPS", "2"))

# ----------------------------- logging -----------------------------

log = logging.getLogger("memdump-service")
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
log.addHandler(_handler)
log.setLevel(logging.INFO)

# ------------------------------ FastAPI ----------------------------

app = FastAPI(title="VM Memory Dump Service", version="1.0.0")

# ------------------------------ Models -----------------------------

class DumpRequest(BaseModel):
    """
    Request body to trigger dumps.

    VMs can be domain names or IDs (as strings).
    """
    vms: list[str]


class DumpStatus(BaseModel):
    dump_id: str
    vm: str
    state: str          # "queued", "running", "completed", "failed"
    progress: float     # 0..100
    message: str | None
    started_at: str | None
    finished_at: str | None
    dump_path: str | None
    duration_sec: float | None


# ------------------------ Global state & locks ---------------------

# Active dump status per VM (key = vm identifier string)
_active_dumps: Dict[str, DumpStatus] = {}
_active_lock = threading.Lock()

# Semaphore to cap concurrent dumps
_concurrency_sem = threading.Semaphore(MAX_PARALLEL_DUMPS)

# For signalling worker to stop progress monitor
_progress_flags: Dict[str, threading.Event] = {}

# Single libvirt connection (thread-safe for read-only ops; dumps are serialized by semaphore)
_libvirt_conn_lock = threading.Lock()
_libvirt_conn: Optional[libvirt.virConnect] = None

# --------------------- Small filesystem helpers -------------------

def ensure_dump_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return os.path.abspath(path)


def sha256_file(path: str, bufsize: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(bufsize)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

# ------------------------ Influx helpers ---------------------------

def _escape_tag(s: str) -> str:
    return s.replace(",", r"\,").replace(" ", r"\ ").replace("=", r"\=")


def _escape_str_field(s: str) -> str:
    return '"' + s.replace("\\", r"\\").replace('"', r'\"') + '"'


def to_line_protocol(measurement: str, tags: Dict[str, str], fields: Dict[str, Any], ts_ns: int) -> str:
    tag_str = ""
    if tags:
        tag_parts = [f"{_escape_tag(k)}={_escape_tag(str(v))}" for k, v in sorted(tags.items())]
        tag_str = "," + ",".join(tag_parts)

    fld_parts = []
    for k, v in sorted(fields.items()):
        if isinstance(v, bool):
            fld_parts.append(f"{k}={str(v).lower()}")
        elif isinstance(v, int):
            fld_parts.append(f"{k}={v}")
        elif isinstance(v, float):
            val = 0.0 if math.isnan(v) or math.isinf(v) else v
            fld_parts.append(f"{k}={val}")
        else:
            fld_parts.append(f"{k}={_escape_str_field(str(v))}")
    field_str = ",".join(fld_parts)
    return f"{measurement}{tag_str} {field_str} {ts_ns}"


def write_influx_v3(lines: str) -> None:
    url = f"{INFLUX_HOST}/api/v3/write"
    params = {"database": INFLUX_DATABASE, "precision": "ns"}
    headers = {"Content-Type": "text/plain; charset=utf-8"}
    if INFLUX_TOKEN:
        headers["Authorization"] = f"Bearer {INFLUX_TOKEN}"
    resp = requests.post(url, params=params, data=lines.encode("utf-8"), headers=headers, timeout=INFLUX_TIMEOUT_S)
    if resp.status_code >= 300:
        raise RuntimeError(f"v3 write failed: {resp.status_code} {resp.text.strip()}")


def write_influx_v2_fallback(lines: str) -> None:
    url = f"{INFLUX_HOST}/api/v2/write"
    params = {"org": INFLUX_ORG, "bucket": INFLUX_BUCKET, "precision": "ns"}
    headers = {"Content-Type": "text/plain; charset=utf-8"}
    if INFLUX_TOKEN:
        headers["Authorization"] = f"Token {INFLUX_TOKEN}"
    resp = requests.post(url, params=params, data=lines.encode("utf-8"), headers=headers, timeout=INFLUX_TIMEOUT_S)
    if resp.status_code >= 300:
        raise RuntimeError(f"v2 write failed: {resp.status_code} {resp.text.strip()}")


def _write_backlog_line(line: str, error_msg: str) -> None:
    ts = datetime.utcnow().isoformat() + "Z"
    header = f"# {ts} | influx_write_failed | {error_msg}\n"
    try:
        backlog_dir = os.path.dirname(INFLUX_BACKLOG_PATH) or "."
        os.makedirs(backlog_dir, exist_ok=True)
        with open(INFLUX_BACKLOG_PATH, "a", encoding="utf-8") as f:
            f.write(header)
            f.write(line)
            if not line.endswith("\n"):
                f.write("\n")
    except Exception as e:
        log.error("Failed to write Influx backlog file %s: %s", INFLUX_BACKLOG_PATH, e)


def write_influx_point(measurement: str, tags: Dict[str, str], fields: Dict[str, Any], ts_ns: int) -> None:
    line = to_line_protocol(measurement, tags, fields, ts_ns)
    payload = line + "\n"

    try:
        write_influx_v3(payload)
        log.info("[influx] v3 write OK: %s", measurement)
        return
    except Exception as e_v3:
        msg_v3 = str(e_v3).split("\n")[0]
        log.warning("[influx] v3 write failed: %s. Trying v2 fallback...", msg_v3)

        try:
            write_influx_v2_fallback(payload)
            log.info("[influx] v2 write OK: %s", measurement)
            return
        except Exception as e_v2:
            msg_v2 = str(e_v2).split("\n")[0]
            combined_err = f"v3: {msg_v3} ; v2: {msg_v2}"
            log.error("[influx] v3+v2 write failed, logging to backlog: %s", combined_err)
            _write_backlog_line(line, combined_err)

# --------------------------- libvirt utils -------------------------

def get_conn() -> libvirt.virConnect:
    global _libvirt_conn
    with _libvirt_conn_lock:
        if _libvirt_conn is not None:
            return _libvirt_conn
        conn = libvirt.open(LIBVIRT_URI)
        if conn is None:
            raise RuntimeError(f"Failed to open libvirt connection: {LIBVIRT_URI}")
        _libvirt_conn = conn
        return conn


def lookup_domain(vm: str) -> libvirt.virDomain:
    conn = get_conn()
    # Try interpret as integer ID
    try:
        vmid = int(vm)
        return conn.lookupByID(vmid)
    except Exception:
        # Fallback: treat as name
        return conn.lookupByName(vm)


# ---------------------- progress monitoring ------------------------

def start_progress_monitor(vm: str, dump_path: str, expected_bytes: int) -> threading.Event:
    """
    Periodically checks the file size and updates progress in _active_dumps[vm].
    Stops when the returned event is set.
    """
    stop_event = threading.Event()
    _progress_flags[vm] = stop_event

    def _monitor():
        while not stop_event.is_set():
            try:
                size = os.path.getsize(dump_path)
            except FileNotFoundError:
                size = 0
            progress = 0.0
            if expected_bytes > 0:
                progress = min(100.0, (size / expected_bytes) * 100.0)
            with _active_lock:
                st = _active_dumps.get(vm)
                if st and st.state == "running":
                    _active_dumps[vm] = DumpStatus(
                        **{
                            **st.dict(),
                            "progress": float(progress),
                            "message": f"Dump in progress ({progress:.1f}%)",
                        }
                    )
            time.sleep(1.0)

    t = threading.Thread(target=_monitor, name=f"progress-{vm}", daemon=True)
    t.start()
    return stop_event

# -------------------------- dump worker ----------------------------

def _dump_worker(vm: str, dump_id: str):
    """
    Worker that performs the actual libvirt dump, updates Influx and status.
    Runs in a separate thread.
    """
    global _active_dumps

    log.info("[worker %s] Starting dump for VM '%s'", dump_id, vm)

    # Acquire concurrency slot
    _concurrency_sem.acquire()

    started = datetime.utcnow()
    started_str = started.isoformat() + "Z"

    # Update status to running
    with _active_lock:
        st = _active_dumps.get(vm)
        if not st:
            # Should not happen, but guard
            st = DumpStatus(
                dump_id=dump_id, vm=vm, state="running", progress=0.0,
                message="Starting dump", started_at=started_str,
                finished_at=None, dump_path=None, duration_sec=None
            )
        else:
            st = DumpStatus(
                **{
                    **st.dict(),
                    "state": "running",
                    "started_at": started_str,
                    "message": "Starting dump",
                }
            )
        _active_dumps[vm] = st

    dump_path = None
    duration_sec = None
    expected_bytes = 0
    progress_flag: Optional[threading.Event] = None

    try:
        dom = lookup_domain(vm)
        dom_name = dom.name()
        try:
            vmid = dom.ID()
        except Exception:
            vmid = -1
        vmid_str = str(vmid if vmid != -1 else dom_name)

        # Expected size from maxMemory (kB -> bytes)
        try:
            max_kb = dom.maxMemory()
            expected_bytes = max_kb * 1024
        except Exception:
            expected_bytes = 0

        # Dump file path
        ensure_dump_dir(DUMP_DIR)
        now_s = int(time.time())
        dump_path = os.path.join(DUMP_DIR, f"{vmid_str}_{now_s}.mem")

        # Start progress monitor (approximate)
        if expected_bytes > 0:
            progress_flag = start_progress_monitor(vm, dump_path, expected_bytes)

        log.info("[worker %s] Live dump -> %s", dump_id, dump_path)

        dump_start = time.time()
        start_ns = int(dump_start * 1e9)

        flags = libvirt.VIR_DUMP_MEMORY_ONLY | libvirt.VIR_DUMP_LIVE
        fmt = libvirt.VIR_DOMAIN_CORE_DUMP_FORMAT_RAW
        dom.coreDumpWithFormat(dump_path, fmt, flags)
        os.chmod(dump_path, stat.S_IRUSR | stat.S_IWUSR)
        duration_sec = time.time() - dump_start

        # Stop progress monitor, set 100%
        if progress_flag is not None:
            progress_flag.set()

        # Hash + metadata
        file_hash = sha256_file(dump_path)
        st_stat = os.stat(dump_path)

        tags = {"dom": dom_name, "vmid": vmid_str, "host": os.uname().nodename}
        fields = {
            "ok": True,
            "sha256": file_hash,
            "dump_path": dump_path,
            "raw_size_bytes": st_stat.st_size,
            "ctime": int(st_stat.st_ctime),
            "mtime": int(st_stat.st_mtime),
            "atime": int(st_stat.st_atime),
            "duration_sec": float(duration_sec),
            "dump_duration_sec": float(duration_sec),
            "loop": 0,          # single-shot
            "every_sec": 0,
        }
        write_influx_point("mem_dumps", tags, fields, ts_ns=start_ns)

        finished = datetime.utcnow()
        finished_str = finished.isoformat() + "Z"
        with _active_lock:
            _active_dumps[vm] = DumpStatus(
                dump_id=dump_id,
                vm=vm,
                state="completed",
                progress=100.0,
                message=f"Dump completed in {duration_sec:.2f} s",
                started_at=started_str,
                finished_at=finished_str,
                dump_path=dump_path,
                duration_sec=duration_sec,
            )
        log.info("[worker %s] Dump completed for VM '%s' in %.2fs", dump_id, vm, duration_sec)

    except Exception as e:
        log.exception("[worker %s] Dump failed for VM '%s': %s", dump_id, vm, e)
        if progress_flag is not None:
            progress_flag.set()
        finished = datetime.utcnow()
        finished_str = finished.isoformat() + "Z"
        with _active_lock:
            st = _active_dumps.get(vm)
            msg = f"Dump failed: {e}"
            if st:
                _active_dumps[vm] = DumpStatus(
                    **{
                        **st.dict(),
                        "state": "failed",
                        "progress": 0.0,
                        "message": msg,
                        "finished_at": finished_str,
                        "dump_path": dump_path,
                        "duration_sec": duration_sec,
                    }
                )
            else:
                _active_dumps[vm] = DumpStatus(
                    dump_id=dump_id,
                    vm=vm,
                    state="failed",
                    progress=0.0,
                    message=msg,
                    started_at=started_str,
                    finished_at=finished_str,
                    dump_path=dump_path,
                    duration_sec=duration_sec,
                )
    finally:
        # Release concurrency slot
        _concurrency_sem.release()
        # Note: we intentionally keep entry in _active_dumps so that
        # remote side can query completed/failed status later.


# ---------------------------- API routes ---------------------------

@app.post("/api/dumps", response_model=dict)
def trigger_dumps(req: DumpRequest):
    """
    Trigger dump(s) for one or more VMs.

    - If VM already has an active dump (state == queued or running), it will not start another.
    - Returns a dict of { vm: DumpStatus }
    """
    ensure_dump_dir(DUMP_DIR)

    result: Dict[str, DumpStatus] = {}
    for vm in req.vms:
        vm_key = str(vm)

        with _active_lock:
            existing = _active_dumps.get(vm_key)
            if existing and existing.state in ("queued", "running"):
                # Do not start another dump for same VM
                result[vm_key] = existing
                continue

            # Create new status, queued
            dump_id = str(uuid.uuid4())
            st = DumpStatus(
                dump_id=dump_id,
                vm=vm_key,
                state="queued",
                progress=0.0,
                message="Queued for dumping",
                started_at=None,
                finished_at=None,
                dump_path=None,
                duration_sec=None,
            )
            _active_dumps[vm_key] = st
            result[vm_key] = st

        # Start worker thread
        t = threading.Thread(
            target=_dump_worker,
            args=(vm_key, st.dump_id),
            name=f"dump-{vm_key}",
            daemon=True,
        )
        t.start()

    return {vm: st.dict() for vm, st in result.items()}


@app.get("/api/dumps/{vm}", response_model=DumpStatus)
def get_dump_status(vm: str):
    """
    Get status for a single VM (running/queued/completed/failed).
    """
    vm_key = str(vm)
    with _active_lock:
        st = _active_dumps.get(vm_key)
        if not st:
            raise HTTPException(status_code=404, detail=f"No dump status for VM '{vm_key}'")
        return st


@app.get("/api/dumps", response_model=dict)
def list_all_dumps():
    """
    List status for all VMs that ever had a dump triggered (in this process lifetime).
    """
    with _active_lock:
        return {vm: st.dict() for vm, st in _active_dumps.items()}

