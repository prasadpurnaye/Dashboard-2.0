#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Libvirt -> InfluxDB v3 metrics collector (line protocol, batched)
+ Derived features: dy/dx rates and atan(rate) in degrees per Dom
+ Latency metrics: feature_latency_ms and loop_latency_ms per poll

- Keeps your original libvirt collection flow
- Batches writes with a background thread
- Timezone-aware UTC timestamps, ns precision
"""

import os, sys, time, signal, threading, queue, math
import datetime as dt
from typing import Dict, Any, List, Tuple, Iterable
import xml.etree.ElementTree as ET

import requests
import libvirt

# ------------------------ config ------------------------
URI              = os.environ.get("LIBVIRT_URI", "qemu+ssh://oneadmin@192.168.0.104/system")
INTERVAL         = float(os.environ.get("POLL_INTERVAL", "1.0"))

INFLUX_URL       = os.environ.get("INFLUX_URL", "http://127.0.0.1:8181")
INFLUX_DB        = os.environ.get("INFLUX_DB", "vmstats")

# --- your fixed token here ---
INFLUX_TOKEN     = "apiv3_LNeKzeLNyQqZAFJiVPN96OUVtjeYsdJURAGDXwi3rq5NZCPfpTpbzr0C096s9m9-nyeE60EkjjuPh8lC_lJnpg"

BATCH_MAX_LINES  = int(os.environ.get("BATCH_MAX_LINES", "2000"))
BATCH_MAX_SEC    = float(os.environ.get("BATCH_MAX_SEC", "1.0"))
DEVICE_CACHE_TTL = float(os.environ.get("DEVICE_CACHE_TTL", "300"))  # seconds

WRITE_ENDPOINT   = f"{INFLUX_URL.rstrip('/')}/api/v3/write_lp?db={INFLUX_DB}&precision=ns"

# ------------------------ libvirt compatibility shim ------------------------
def _lv(name: str, default: int = 0) -> int:
    return getattr(libvirt, name, default)

VIR_DOMAIN_STATS_STATE      = _lv('VIR_DOMAIN_STATS_STATE', 1)
VIR_DOMAIN_STATS_CPU_TOTAL  = _lv('VIR_DOMAIN_STATS_CPU_TOTAL', 2)
VIR_DOMAIN_STATS_BALLOON    = _lv('VIR_DOMAIN_STATS_BALLOON', 4)
VIR_DOMAIN_STATS_VCPU       = _lv('VIR_DOMAIN_STATS_VCPU', 8)
VIR_DOMAIN_STATS_NET        = _lv('VIR_DOMAIN_STATS_NET', _lv('VIR_DOMAIN_STATS_INTERFACE', 0))
VIR_DOMAIN_STATS_BLOCK      = _lv('VIR_DOMAIN_STATS_BLOCK', 0)

VIR_CONNECT_GET_ALL_DOMAINS_STATS_ACTIVE  = _lv('VIR_CONNECT_GET_ALL_DOMAINS_STATS_ACTIVE', 0)
VIR_CONNECT_GET_ALL_DOMAINS_STATS_RUNNING = _lv('VIR_CONNECT_GET_ALL_DOMAINS_STATS_RUNNING', 0)

STAT_FLAGS = (
    VIR_CONNECT_GET_ALL_DOMAINS_STATS_ACTIVE |
    VIR_CONNECT_GET_ALL_DOMAINS_STATS_RUNNING
)

DOM_STATS = (
    VIR_DOMAIN_STATS_STATE     |
    VIR_DOMAIN_STATS_CPU_TOTAL |
    VIR_DOMAIN_STATS_BALLOON   |
    VIR_DOMAIN_STATS_NET       |
    VIR_DOMAIN_STATS_BLOCK
)

# ------------------------ signals ------------------------
_stop = False
def _sig_handler(sig, frame):
    global _stop
    _stop = True
signal.signal(signal.SIGINT, _sig_handler)
signal.signal(signal.SIGTERM, _sig_handler)

# ------------------------ device cache ------------------------
_device_cache: Dict[int, Dict[str, Any]] = {}

def _extract_devices_from_xml(dom) -> Tuple[List[str], List[str]]:
    root = ET.fromstring(dom.XMLDesc(0))
    nics, disks = [], []
    for iface in root.findall("./devices/interface"):
        tgt = iface.find("target")
        if tgt is not None and "dev" in tgt.attrib:
            nics.append(tgt.attrib["dev"])
    for d in root.findall("./devices/disk"):
        if d.get("device") != "disk":
            continue
        tgt = d.find("target")
        if tgt is not None and "dev" in tgt.attrib:
            disks.append(tgt.attrib["dev"])
    return nics, disks

def _get_devices(conn, dom, dom_id: int) -> Tuple[List[str], List[str]]:
    now = time.time()
    cached = _device_cache.get(dom_id)
    if cached and now - cached["ts"] < DEVICE_CACHE_TTL:
        return cached["nics"], cached["disks"]
    nics, disks = _extract_devices_from_xml(dom)
    _device_cache[dom_id] = {"ts": now, "nics": nics, "disks": disks}
    return nics, disks

# ------------------------ line protocol helpers ------------------------
def _esc_tag(v: str) -> str:
    return str(v).replace("\\", "\\\\").replace(" ", "\\ ").replace(",", "\\,").replace("=", "\\=")

def _esc_str_field(v: str) -> str:
    return '"' + str(v).replace("\\", "\\\\").replace('"', '\\"') + '"'

def _fmt_field_value(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return f"{v}i"
    if isinstance(v, float):
        if v != v or v == float("inf") or v == float("-inf"):
            return "0"
        return f"{v}"
    return _esc_str_field(v)

def _ts_ns(ts: dt.datetime) -> int:
    return int(ts.timestamp() * 1_000_000_000)

def lp_line(measurement: str, tags: Dict[str, Any], fields: Dict[str, Any], ts: dt.datetime) -> str:
    f = {k: v for k, v in fields.items() if v is not None}
    if not f:
        f = {"noop": 0}
    tag_str = ",".join(f"{k}={_esc_tag(v)}" for k, v in tags.items() if v is not None)
    field_str = ",".join(f"{k}={_fmt_field_value(v)}" for k, v in f.items())
    t_ns = _ts_ns(ts)
    if tag_str:
        return f"{measurement},{tag_str} {field_str} {t_ns}"
    else:
        return f"{measurement} {field_str} {t_ns}"

# ------------------------ Influx writer ------------------------
class InfluxWriter(threading.Thread):
    def __init__(self, endpoint: str, token: str, batch_lines: int, batch_sec: float):
        super().__init__(daemon=True)
        if not token:
            sys.stderr.write("[influx] INFLUX_TOKEN is required\n")
            sys.exit(2)
        self.endpoint = endpoint
        self.headers = {"Authorization": f"Bearer {token}"}
        self.q: "queue.Queue[str]" = queue.Queue(maxsize=20000)
        self.batch_lines = max(1, batch_lines)
        self.batch_sec = max(0.05, batch_sec)
        self._running = True

    def run(self):
        buf: List[str] = []
        last = time.time()
        session = requests.Session()
        while self._running or not self.q.empty():
            timeout = max(0.0, self.batch_sec - (time.time() - last))
            try:
                line = self.q.get(timeout=timeout)
                buf.append(line)
            except queue.Empty:
                pass

            should_flush = (len(buf) >= self.batch_lines) or ((time.time() - last) >= self.batch_sec)
            if should_flush and buf:
                payload = "\n".join(buf)
                try:
                    r = session.post(self.endpoint, headers=self.headers, data=payload, timeout=10)
                    ts_str = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    if r.status_code in (204, 200):
                        print(f"[{ts_str}] [influx] ✅ pushed {len(buf)} lines to InfluxDB ({self.endpoint})")
                    else:
                        sys.stderr.write(f"[{ts_str}] [influx] ❌ write failed {r.status_code}: {r.text[:200]}\n")
                except requests.RequestException as e:
                    ts_str = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    sys.stderr.write(f"[{ts_str}] [influx] ❌ write exception: {e}\n")
                buf.clear()
                last = time.time()

    def enqueue(self, line: str) -> None:
        try:
            self.q.put_nowait(line)
        except queue.Full:
            _ = self.q.get_nowait()
            self.q.put_nowait(line)

    def stop(self):
        self._running = False

# ------------------------ domstats normalization ------------------------
def _bulk_domain_stats(conn, dom_stats: int, stat_flags: int):
    try:
        try:
            return conn.getAllDomainStats(dom_stats, stat_flags)
        except TypeError:
            return conn.getAllDomainStats(None, dom_stats, stat_flags)
    except libvirt.libvirtError:
        return None

def _iter_domstats(domstats) -> Iterable[Tuple[Any, Dict[str, Any]]]:
    for entry in domstats:
        if isinstance(entry, dict):
            dom = entry.get("dom")
            stats = entry.get("stats", {}) or {}
            if dom is not None:
                yield dom, stats
        elif isinstance(entry, tuple):
            if len(entry) >= 2:
                dom, stats = entry[0], entry[1] or {}
                yield dom, stats

# ------------------------ feature state ------------------------
# store previous counters per Dom to compute deltas/rates
_prev_by_dom: Dict[str, Dict[str, Any]] = {}  # key = Dom (name)

# which totals get dy/dx + atan(angle_deg)
FEATURE_KEYS = [
    "net_rxbytes", "net_txbytes", "net_rxpackets", "net_txpackets",
    "disk_rd_req", "disk_rd_bytes", "disk_wr_reqs", "disk_wr_bytes",
]

EPS = 1e-12

def _compute_features_and_enqueue(writer: InfluxWriter, ts: dt.datetime,
                                  dom_tags: Dict[str, Any],
                                  totals_fields: Dict[str, int]) -> None:
    """
    Compute per-Dom dy/dx (rate) and angle_deg = degrees(atan(rate))
    for FEATURE_KEYS using previous counters. Emit vm_features.
    """
    t0 = time.perf_counter()
    dom = str(dom_tags.get("Dom"))
    prev = _prev_by_dom.get(dom)

    # build current snapshot
    snap = {"ts": ts}
    for k in FEATURE_KEYS:
        snap[k] = int(totals_fields.get(k, 0) or 0)

    if prev is not None:
        dt_s = (snap["ts"] - prev["ts"]).total_seconds()
        if dt_s <= 0:
            dt_s = EPS

        fields_rate: Dict[str, float] = {}
        fields_angle: Dict[str, float] = {}

        for k in FEATURE_KEYS:
            curr = float(snap[k])
            old  = float(prev.get(k, 0.0))
            d = curr - old
            if d < 0:  # counter reset protection
                d = 0.0
            rate = d / (dt_s + EPS)
            angle_deg = math.degrees(math.atan(rate))
            fields_rate[f"{k}_rate"] = rate
            fields_angle[f"{k}_angle_deg"] = angle_deg

        # emit single line with both rates and angles
        feature_fields = {**fields_rate, **fields_angle}
        writer.enqueue(lp_line("vm_features", dom_tags, feature_fields, ts))

    # update previous snapshot
    _prev_by_dom[dom] = snap

    # emit latency for features (per loop we also push aggregate)
    t1 = time.perf_counter()
    feature_latency_ms = (t1 - t0) * 1000.0
    # push a per-Dom feature latency line (optional; comment if too chatty)
    writer.enqueue(lp_line(
        "collector_latency",
        {"Dom": dom},
        {"feature_latency_ms": feature_latency_ms},
        ts
    ))

# ------------------------ collection logic ------------------------
def collect_once(conn, writer: InfluxWriter) -> float:
    """
    Collect and enqueue all metrics ONCE.
    Returns: feature computation latency (ms) aggregated across doms for this loop.
    """
    loop_feature_ms = 0.0
    ts = dt.datetime.now(dt.timezone.utc)

    domstats = _bulk_domain_stats(conn, DOM_STATS, STAT_FLAGS)
    if domstats:
        for dom, data in _iter_domstats(domstats):
            try:
                dom_id = dom.ID()
            except libvirt.libvirtError:
                continue
            name = dom.name()
            uuid = dom.UUIDString()

            net_prefix = "net" if "net.count" in data else "interface" if "interface.count" in data else None
            net_count = int(data.get(f"{net_prefix}.count", 0)) if net_prefix else 0
            block_count = int(data.get("block.count", 0))

            # accumulate totals
            tot_rxB=tot_rxP=tot_rxE=tot_rxD=0
            tot_txB=tot_txP=tot_txE=tot_txD=0
            tot_rd_req=tot_rd_bytes=tot_wr_reqs=tot_wr_bytes=0

            try:
                nics, disks = _get_devices(conn, dom, dom_id)
            except Exception:
                nics, disks = [], []

            # per-NIC
            for i in range(net_count):
                rxB = int(data.get(f"{net_prefix}.{i}.rx.bytes", 0) or 0)
                rxP = int(data.get(f"{net_prefix}.{i}.rx.pkts", 0)  or 0)
                rxE = int(data.get(f"{net_prefix}.{i}.rx.errs", 0)  or 0)
                rxD = int(data.get(f"{net_prefix}.{i}.rx.drop", 0)  or 0)
                txB = int(data.get(f"{net_prefix}.{i}.tx.bytes", 0) or 0)
                txP = int(data.get(f"{net_prefix}.{i}.tx.pkts", 0)  or 0)
                txE = int(data.get(f"{net_prefix}.{i}.tx.errs", 0)  or 0)
                txD = int(data.get(f"{net_prefix}.{i}.tx.drop", 0)  or 0)

                tot_rxB+=rxB; tot_rxP+=rxP; tot_rxE+=rxE; tot_rxD+=rxD
                tot_txB+=txB; tot_txP+=txP; tot_txE+=txE; tot_txD+=txD

                devname = nics[i] if i < len(nics) else f"net{i}"
                tags = {"VMID": dom_id, "UUID": uuid, "Dom": name, "devtype": "nic", "device": devname}
                fields = {
                    "rxbytes": rxB, "rxpackets": rxP, "rxerrors": rxE, "rxdrops": rxD,
                    "txbytes": txB, "txpackets": txP, "txerrors": txE, "txdrops": txD
                }
                writer.enqueue(lp_line("vm_devices", tags, fields, ts))

            # per-disk
            for i in range(block_count):
                rd_req   = int(data.get(f"block.{i}.rd.reqs", 0)  or 0)
                rd_bytes = int(data.get(f"block.{i}.rd.bytes", 0) or 0)
                wr_req   = int(data.get(f"block.{i}.wr.reqs", 0)  or 0)
                wr_bytes = int(data.get(f"block.{i}.wr.bytes", 0) or 0)
                errs     = int(data.get(f"block.{i}.errs", 0)      or 0)

                tot_rd_req   += rd_req
                tot_rd_bytes += rd_bytes
                tot_wr_reqs  += wr_req
                tot_wr_bytes += wr_bytes

                devname = disks[i] if i < len(disks) else f"vd{i}"
                tags = {"VMID": dom_id, "UUID": uuid, "Dom": name, "devtype": "disk", "device": devname}
                fields = {"rd_req": rd_req, "rd_bytes": rd_bytes, "wr_reqs": wr_req, "wr_bytes": wr_bytes, "errors": errs}
                writer.enqueue(lp_line("vm_devices", tags, fields, ts))

            # totals
            totals_fields = {
                # network totals
                "net_rxbytes":   tot_rxB, "net_rxpackets": tot_rxP, "net_rxerrors": tot_rxE, "net_rxdrops": tot_rxD,
                "net_txbytes":   tot_txB, "net_txpackets": tot_txP, "net_txerrors": tot_txE, "net_txdrops": tot_txD,
                # disk totals (added for features)
                "disk_rd_req":   tot_rd_req,
                "disk_rd_bytes": tot_rd_bytes,
                "disk_wr_reqs":  tot_wr_reqs,
                "disk_wr_bytes": tot_wr_bytes,
                # cpu/mem state
                "state":   int(data.get("state.state", 0) or 0),
                "cpus":    int(data.get("vcpu.current", 0) or 0),
                "cputime": int(data.get("cpu.time", 0) or 0),
                "timeusr": int(data.get("cpu.user", 0) or 0),
                "timesys": int(data.get("cpu.system", 0) or 0),
                "memactual":      int(data.get("balloon.current", 0) or 0),
                "memrss":         int(data.get("balloon.rss", 0) or 0),
                "memavailable":   int(data.get("balloon.max", 0) or 0),
                "memusable":      int(data.get("balloon.usable", 0) or 0),
                "memswap_in":     int(data.get("balloon.swap_in", 0) or 0),
                "memswap_out":    int(data.get("balloon.swap_out", 0) or 0),
                "memmajor_fault": int(data.get("balloon.major_fault", 0) or 0),
                "memminor_fault": int(data.get("balloon.minor_fault", 0) or 0),
                "memdisk_cache":  int(data.get("balloon.disk_caches", 0) or 0),
            }
            tags_totals = {"VMID": dom_id, "UUID": uuid, "Dom": name}
            writer.enqueue(lp_line("vm_totals", tags_totals, totals_fields, ts))

            # ---- feature compute (timed) ----
            ft0 = time.perf_counter()
            _compute_features_and_enqueue(writer, ts, tags_totals, totals_fields)
            ft1 = time.perf_counter()
            loop_feature_ms += (ft1 - ft0) * 1000.0

        return loop_feature_ms

    # ---------- Fallback path ----------
    for dom_id in conn.listDomainsID():
        dom = conn.lookupByID(dom_id)
        name = dom.name()
        uuid = dom.UUIDString()

        try:
            state, memmax, mem, cpus, cputime = dom.info()
        except libvirt.libvirtError:
            state=memmax=mem=cpus=cputime=0

        mem_fields: Dict[str, int] = {}
        try:
            mem_fields = dom.memoryStats()
        except libvirt.libvirtError:
            pass

        nic_rxB=nic_rxP=nic_rxE=nic_rxD=0
        nic_txB=nic_txP=nic_txE=nic_txD=0
        rd_req_sum=rd_bytes_sum=wr_req_sum=wr_bytes_sum=0

        try:
            nics, disks = _get_devices(conn, dom, dom_id)
        except Exception:
            nics, disks = [], []

        for nic in nics:
            try:
                rxB, rxP, rxE, rxD, txB, txP, txE, txD = dom.interfaceStats(nic)
            except libvirt.libvirtError:
                rxB=rxP=rxE=rxD=txB=txP=txE=txD=0
            nic_rxB+=rxB; nic_rxP+=rxP; nic_rxE+=rxE; nic_rxD+=rxD
            nic_txB+=txB; nic_txP+=txP; nic_txE+=txE; nic_txD+=txD

            tags = {"VMID": dom_id, "UUID": uuid, "Dom": name, "devtype": "nic", "device": nic}
            fields = {
                "rxbytes": rxB, "rxpackets": rxP, "rxerrors": rxE, "rxdrops": rxD,
                "txbytes": txB, "txpackets": txP, "txerrors": txE, "txdrops": txD
            }
            writer.enqueue(lp_line("vm_devices", tags, fields, ts))

        for disk in disks:
            try:
                rd_req, rd_bytes, wr_req, wr_bytes, errs = dom.blockStats(disk)
            except libvirt.libvirtError:
                rd_req=rd_bytes=wr_req=wr_bytes=errs=0
            rd_req_sum+=rd_req; rd_bytes_sum+=rd_bytes; wr_req_sum+=wr_req; wr_bytes_sum+=wr_bytes
            tags = {"VMID": dom_id, "UUID": uuid, "Dom": name, "devtype": "disk", "device": disk}
            fields = {"rd_req": rd_req, "rd_bytes": rd_bytes, "wr_reqs": wr_req, "wr_bytes": wr_bytes, "errors": errs}
            writer.enqueue(lp_line("vm_devices", tags, fields, ts))

        totals_fields = {
            "net_rxbytes": nic_rxB, "net_rxpackets": nic_rxP, "net_rxerrors": nic_rxE, "net_rxdrops": nic_rxD,
            "net_txbytes": nic_txB, "net_txpackets": nic_txP, "net_txerrors": nic_txE, "net_txdrops": nic_txD,
            "disk_rd_req": rd_req_sum, "disk_rd_bytes": rd_bytes_sum, "disk_wr_reqs": wr_req_sum, "disk_wr_bytes": wr_bytes_sum,
            "state": state, "cpus": cpus, "cputime": cputime,
            "timeusr": 0, "timesys": 0,
            "memactual":      mem_fields.get("actual", 0),
            "memrss":         mem_fields.get("rss", 0),
            "memavailable":   mem_fields.get("available", 0),
            "memusable":      mem_fields.get("usable", 0),
            "memswap_in":     mem_fields.get("swap_in", 0),
            "memswap_out":    mem_fields.get("swap_out", 0),
            "memmajor_fault": mem_fields.get("major_fault", 0),
            "memminor_fault": mem_fields.get("minor_fault", 0),
            "memdisk_cache":  mem_fields.get("disk_caches", 0),
        }
        tags_totals = {"VMID": dom_id, "UUID": uuid, "Dom": name}
        writer.enqueue(lp_line("vm_totals", tags_totals, totals_fields, ts))

        ft0 = time.perf_counter()
        _compute_features_and_enqueue(writer, ts, tags_totals, totals_fields)
        ft1 = time.perf_counter()
        loop_feature_ms += (ft1 - ft0) * 1000.0

    return loop_feature_ms

# ------------------------ main ------------------------
def main():
    if not INFLUX_TOKEN:
        sys.stderr.write("Set INFLUX_TOKEN env var (Bearer token for InfluxDB v3)\n")
        sys.exit(2)

    conn = None
    try:
        conn = libvirt.openReadOnly(URI)
    except libvirt.libvirtError:
        conn = libvirt.open(URI)
    if conn is None:
        sys.stderr.write(f"Failed to connect libvirt: {URI}\n")
        sys.exit(2)

    writer = InfluxWriter(WRITE_ENDPOINT, INFLUX_TOKEN, BATCH_MAX_LINES, BATCH_MAX_SEC)
    writer.start()
    print(f"[libvirt->influx] Connected to {URI}. Poll every {INTERVAL}s. Ctrl+C to stop.")
    try:
        while not _stop:
            loop_t0 = time.perf_counter()
            feature_ms = collect_once(conn, writer)
            loop_t1 = time.perf_counter()
            loop_ms = (loop_t1 - loop_t0) * 1000.0

            # one consolidated latency point per loop (no Dom tag)
            ts = dt.datetime.now(dt.timezone.utc)
            writer.enqueue(lp_line(
                "collector_latency",
                {},  # no Dom tag for the aggregate
                {"feature_latency_ms": feature_ms, "loop_latency_ms": loop_ms},
                ts
            ))

            # sleep remaining interval
            remaining = INTERVAL - (time.perf_counter() - loop_t0)
            if remaining > 0:
                time.sleep(remaining)
    finally:
        writer.stop()
        writer.join(timeout=5)
        try:
            conn.close()
        except Exception:
            pass
        print("\n[libvirt->influx] Stopped.")

if __name__ == "__main__":
    main()

