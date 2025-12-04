"""
Telemetry Collector Service
Main module coordinating KVM monitoring and InfluxDB writing
"""

import time
import math
import threading
import logging
import datetime as dt
from typing import Dict, Any, Optional, Iterable, Tuple
from collections import defaultdict

from src.config.telemetry_config import TelemetryConfig
from src.telemetry.kvm_connector import KVMConnector, KVMConnectorError
from src.telemetry.influx_connector import InfluxConnector

logger = logging.getLogger(__name__)


class TelemetryCollectorError(Exception):
    """Raised when collector operations fail"""
    pass


class TelemetryCollector:
    """
    Coordinates KVM monitoring and InfluxDB writing.
    Runs as a background service with start/stop controls.
    """
    
    def __init__(self, config: TelemetryConfig):
        """Initialize telemetry collector"""
        self.config = config
        self.kvm = KVMConnector(config.libvirt_uri, config.libvirt_timeout)
        self.influx: Optional[InfluxConnector] = None
        
        self._collector_thread: Optional[threading.Thread] = None
        self._running = False
        self._stop_event = threading.Event()
        
        # Metrics for monitoring
        self.stats = {
            "started_at": None,
            "total_collections": 0,
            "total_errors": 0,
            "last_collection_time": None,
            "vms_monitored": 0,
            "total_metrics_written": 0,
        }
        
        logger.info("Telemetry collector initialized")
    
    def start(self) -> bool:
        """
        Start telemetry collection in background.
        
        Returns:
            True if started successfully, False otherwise
        """
        if self._running:
            logger.warning("Collector already running")
            return False
        
        try:
            # Connect to KVM
            if not self.kvm.connect():
                raise TelemetryCollectorError("Failed to connect to KVM")
            
            # Get live VMs to verify connectivity
            vms = self.kvm.get_live_vms()
            logger.info(f"Found {len(vms)} live VMs")
            
            # Create fresh InfluxDB connector (must be new thread instance)
            self.influx = InfluxConnector(
                self.config.influx_url,
                self.config.influx_db,
                self.config.influx_token,
                self.config.batch_max_lines,
                self.config.batch_max_sec
            )
            
            # Start InfluxDB writer
            self.influx.start_writing()
            
            # Start collector thread
            self._running = True
            self._stop_event.clear()
            self.stats["started_at"] = dt.datetime.now()
            self.stats["total_collections"] = 0
            
            self._collector_thread = threading.Thread(
                target=self._collection_loop,
                daemon=True,
                name="TelemetryCollector"
            )
            self._collector_thread.start()
            
            logger.info("✓ Telemetry collector started")
            return True
        
        except Exception as e:
            logger.error(f"Failed to start collector: {str(e)}")
            self.stats["total_errors"] += 1
            self._cleanup()
            return False
    
    def stop(self) -> None:
        """Stop telemetry collection gracefully"""
        if not self._running:
            logger.warning("Collector not running")
            return
        
        logger.info("Stopping telemetry collector...")
        self._running = False
        self._stop_event.set()
        
        # Wait for collector thread
        if self._collector_thread and self._collector_thread.is_alive():
            self._collector_thread.join(timeout=5)
        
        self._cleanup()
        logger.info("✓ Telemetry collector stopped")
    
    def _cleanup(self) -> None:
        """Cleanup resources"""
        try:
            if self.influx:
                self.influx.stop_writing()
        except Exception as e:
            logger.error(f"Error stopping InfluxDB: {str(e)}")
        
        try:
            self.kvm.disconnect()
        except Exception as e:
            logger.error(f"Error disconnecting KVM: {str(e)}")
    
    def _collection_loop(self) -> None:
        """Main collection loop (runs in background thread)"""
        logger.info("Collection loop started")
        
        while self._running and not self._stop_event.is_set():
            try:
                loop_start = time.perf_counter()
                
                # Collect metrics from all VMs
                self._collect_metrics()
                
                # Update stats
                self.stats["total_collections"] += 1
                self.stats["last_collection_time"] = dt.datetime.now()
                
                # Sleep for remaining interval
                loop_elapsed = time.perf_counter() - loop_start
                remaining = self.config.poll_interval - loop_elapsed
                if remaining > 0:
                    time.sleep(remaining)
            
            except Exception as e:
                self.stats["total_errors"] += 1
                logger.error(f"Error in collection loop: {str(e)}")
                time.sleep(self.config.poll_interval)
        
        logger.info("Collection loop stopped")
    
    def _collect_metrics(self) -> None:
        """Collect metrics from all VMs and write to InfluxDB"""
        try:
            vms = self.kvm.get_live_vms()
            self.stats["vms_monitored"] = len(vms)
            
            ts = dt.datetime.now(dt.timezone.utc)
            logger.info(f"📊 Collecting metrics from {len(vms)} VM(s)...")
            
            for vm in vms:
                try:
                    self._collect_vm_metrics(vm, ts)
                except Exception as e:
                    logger.warning(f"Error collecting VM {vm['name']}: {str(e)}")
        
        except KVMConnectorError as e:
            logger.error(f"KVM error: {str(e)}")
    
    def _collect_vm_metrics(self, vm: Dict[str, Any], ts: dt.datetime) -> None:
        """Collect metrics for a single VM"""
        lines = []
        
        # Base tags for all measurements
        base_tags = {
            "VMID": str(vm["id"]),
            "name": vm["name"],
            "uuid": vm["uuid"],
        }
        
        # Collect device metrics (vm_devices and vm_totals)
        if "dom" in vm:
            try:
                self._collect_device_metrics(vm, base_tags, ts, lines)
            except Exception as e:
                logger.warning(f"Error collecting device metrics for {vm['name']}: {str(e)}")
        
        # Enqueue all lines to InfluxDB
        if self.influx:
            for line in lines:
                self.influx.enqueue(line)
            # Track metrics written
            self.stats["total_metrics_written"] += len(lines)
    
    def _collect_device_metrics(
        self,
        vm: Dict[str, Any],
        base_tags: Dict[str, str],
        ts: dt.datetime,
        lines: list
    ) -> None:
        """
        Collect per-device metrics (network interfaces and disk devices).
        Adds vm_devices and vm_totals measurements.
        """
        dom = vm.get("dom")
        if not dom:
            return
        
        try:
            # Get devices
            nics, disks = self.kvm.get_devices_for_vm(dom)
            
            # Network interface metrics
            net_totals = {
                "net_rxbytes": 0,
                "net_rxpackets": 0,
                "net_rxerrors": 0,
                "net_rxdrops": 0,
                "net_txbytes": 0,
                "net_txpackets": 0,
                "net_txerrors": 0,
                "net_txdrops": 0,
            }
            
            for nic in nics:
                try:
                    nic_stats = self.kvm.get_interface_stats(dom, nic)
                    
                    # Create per-device line
                    dev_tags = base_tags.copy()
                    dev_tags["devtype"] = "nic"
                    dev_tags["device"] = nic
                    
                    lines.append(self._line_protocol(
                        "vm_devices",
                        dev_tags,
                        nic_stats,
                        ts
                    ))
                    
                    # Accumulate totals
                    for key in net_totals:
                        short_key = key.replace("net_", "")
                        net_totals[key] += nic_stats.get(short_key, 0)
                
                except Exception as e:
                    logger.warning(f"Error collecting stats for NIC {nic}: {str(e)}")
            
            # Block device metrics
            disk_totals = {
                "disk_rd_req": 0,
                "disk_rd_bytes": 0,
                "disk_wr_reqs": 0,
                "disk_wr_bytes": 0,
                "disk_errors": 0,
            }
            
            for disk in disks:
                try:
                    disk_stats = self.kvm.get_block_stats(dom, disk)
                    
                    # Create per-device line
                    dev_tags = base_tags.copy()
                    dev_tags["devtype"] = "disk"
                    dev_tags["device"] = disk
                    
                    lines.append(self._line_protocol(
                        "vm_devices",
                        dev_tags,
                        disk_stats,
                        ts
                    ))
                    
                    # Accumulate totals
                    disk_totals["disk_rd_req"] += disk_stats.get("rd_req", 0)
                    disk_totals["disk_rd_bytes"] += disk_stats.get("rd_bytes", 0)
                    disk_totals["disk_wr_reqs"] += disk_stats.get("wr_reqs", 0)
                    disk_totals["disk_wr_bytes"] += disk_stats.get("wr_bytes", 0)
                    disk_totals["disk_errors"] += disk_stats.get("errors", 0)
                
                except Exception as e:
                    logger.warning(f"Error collecting stats for disk {disk}: {str(e)}")
            
            # Get extended memory stats
            mem_stats = self.kvm.get_memory_stats(dom)
            
            # Get CPU time breakdown
            cpu_stats = self.kvm.get_cpu_stats(dom)
            
            # Build vm_totals line with all aggregated data
            totals_fields = {
                # Network totals
                **net_totals,
                # Disk totals
                **disk_totals,
                # Memory extended metrics
                **mem_stats,
                # CPU breakdown
                **cpu_stats,
                # State and basic info
                "state": vm["state"] if isinstance(vm["state"], int) else (1 if vm["state"] == "running" else 0),
                "cpus": vm["cpu_count"],
                "cputime": vm["cputime"],
            }
            
            lines.append(self._line_protocol(
                "vm_totals",
                base_tags,
                totals_fields,
                ts
            ))
        
        except Exception as e:
            logger.warning(f"Error in _collect_device_metrics: {str(e)}")
    
    def _line_protocol(
        self,
        measurement: str,
        tags: Dict[str, Any],
        fields: Dict[str, Any],
        ts: dt.datetime
    ) -> str:
        """
        Format a InfluxDB line protocol line.
        
        Returns:
            Line protocol formatted string
        """
        # Filter None values from fields
        fields = {k: v for k, v in fields.items() if v is not None}
        if not fields:
            fields = {"noop": 0}
        
        # Format tags
        tag_str = ",".join(
            f"{k}={self._escape_tag(v)}"
            for k, v in tags.items()
            if v is not None
        )
        
        # Format fields
        field_str = ",".join(
            f"{k}={self._format_field_value(v)}"
            for k, v in fields.items()
        )
        
        # Timestamp in nanoseconds
        ts_ns = int(ts.timestamp() * 1_000_000_000)
        
        # Build line
        if tag_str:
            return f"{measurement},{tag_str} {field_str} {ts_ns}"
        else:
            return f"{measurement} {field_str} {ts_ns}"
    
    @staticmethod
    def _escape_tag(value: Any) -> str:
        """Escape tag value for line protocol"""
        s = str(value)
        return (s
            .replace("\\", "\\\\")
            .replace(" ", "\\ ")
            .replace(",", "\\,")
            .replace("=", "\\="))
    
    @staticmethod
    def _format_field_value(value: Any) -> str:
        """Format field value for line protocol"""
        if isinstance(value, bool):
            return "true" if value else "false"
        elif isinstance(value, int):
            return f"{value}i"
        elif isinstance(value, float):
            if math.isnan(value) or math.isinf(value):
                return "0"
            return str(value)
        else:
            # String field
            escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
            return f'"{escaped}"'
    
    def is_running(self) -> bool:
        """Check if collector is running"""
        return self._running and (self._collector_thread and self._collector_thread.is_alive())
    
    def get_status(self) -> Dict[str, Any]:
        """Get collector status and statistics"""
        return {
            "running": self.is_running(),
            "started_at": self.stats["started_at"].isoformat() if self.stats["started_at"] else None,
            "total_collections": self.stats["total_collections"],
            "total_errors": self.stats["total_errors"],
            "last_collection_time": self.stats["last_collection_time"].isoformat() if self.stats["last_collection_time"] else None,
            "vms_monitored": self.stats["vms_monitored"],
            "total_metrics_written": self.stats["total_metrics_written"],
            "influx_queue_size": self.influx.get_queue_size() if self.influx else 0,
            "config": self.config.to_safe_dict(),
        }
    
    def get_vms(self) -> list:
        """Get list of currently monitored VMs"""
        try:
            return self.kvm.get_live_vms() if self.kvm.is_connected() else []
        except Exception as e:
            logger.error(f"Error getting VMs: {str(e)}")
            return []
