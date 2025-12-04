"""
KVM/QEMU Connector Module
Handles libvirt connections and VM management
"""

import libvirt
import xml.etree.ElementTree as ET
import time
from typing import List, Dict, Any, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class KVMConnectorError(Exception):
    """Raised when KVM connection operations fail"""
    pass


class KVMConnector:
    """Manages connections to libvirt and retrieves VM information"""
    
    # Device cache for per-VM interface and disk device lists
    DEVICE_CACHE_TTL = 300  # seconds
    
    def __init__(self, uri: str, timeout: float = 30.0):
        """
        Initialize KVM connector.
        
        Args:
            uri: Libvirt URI (e.g., qemu+ssh://user@host/system)
            timeout: Connection timeout in seconds
        """
        self.uri = uri
        self.timeout = timeout
        self._conn: Optional[libvirt.virConnect] = None
        self._libvirt_compat = self._setup_libvirt_compat()
        # Device cache: {vm_id: {"ts": time, "nics": [...], "disks": [...]}}
        self._device_cache: Dict[int, Dict[str, Any]] = {}
    
    def _setup_libvirt_compat(self) -> Dict[str, int]:
        """Setup libvirt compatibility shim for different versions"""
        def _lv(name: str, default: int = 0) -> int:
            return getattr(libvirt, name, default)
        
        return {
            "VIR_DOMAIN_STATS_STATE": _lv('VIR_DOMAIN_STATS_STATE', 1),
            "VIR_DOMAIN_STATS_CPU_TOTAL": _lv('VIR_DOMAIN_STATS_CPU_TOTAL', 2),
            "VIR_DOMAIN_STATS_BALLOON": _lv('VIR_DOMAIN_STATS_BALLOON', 4),
            "VIR_DOMAIN_STATS_VCPU": _lv('VIR_DOMAIN_STATS_VCPU', 8),
            "VIR_DOMAIN_STATS_NET": _lv('VIR_DOMAIN_STATS_NET', 
                                        _lv('VIR_DOMAIN_STATS_INTERFACE', 0)),
            "VIR_DOMAIN_STATS_BLOCK": _lv('VIR_DOMAIN_STATS_BLOCK', 0),
            "VIR_CONNECT_GET_ALL_DOMAINS_STATS_ACTIVE": _lv(
                'VIR_CONNECT_GET_ALL_DOMAINS_STATS_ACTIVE', 0),
            "VIR_CONNECT_GET_ALL_DOMAINS_STATS_RUNNING": _lv(
                'VIR_CONNECT_GET_ALL_DOMAINS_STATS_RUNNING', 0),
        }
    
    def connect(self) -> bool:
        """
        Establish connection to libvirt.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Connecting to libvirt: {self.uri}")
            try:
                self._conn = libvirt.openReadOnly(self.uri)
            except libvirt.libvirtError:
                # If read-only fails, try with write access
                self._conn = libvirt.open(self.uri)
            
            if self._conn:
                logger.info("✓ Connected to libvirt")
                return True
            return False
        except libvirt.libvirtError as e:
            logger.error(f"Failed to connect to libvirt: {str(e)}")
            raise KVMConnectorError(f"Libvirt connection failed: {str(e)}")
    
    def disconnect(self) -> None:
        """Close libvirt connection"""
        if self._conn:
            try:
                self._conn.close()
                logger.info("Disconnected from libvirt")
            except Exception as e:
                logger.error(f"Error disconnecting: {str(e)}")
            finally:
                self._conn = None
    
    def is_connected(self) -> bool:
        """Check if connection is active"""
        if not self._conn:
            return False
        try:
            self._conn.getCapabilities()
            return True
        except Exception:
            return False
    
    def get_live_vms(self) -> List[Dict[str, Any]]:
        """
        Get list of live VMs with basic information.
        
        Returns:
            List of VM info dicts with keys: id, name, uuid, state, cpu_count, memory, dom
        """
        if not self.is_connected():
            raise KVMConnectorError("Not connected to libvirt")
        
        vms = []
        try:
            for dom_id in self._conn.listDomainsID():
                try:
                    dom = self._conn.lookupByID(dom_id)
                    vm_info = self._extract_vm_info(dom)
                    vm_info["dom"] = dom  # Include domain object for extended stats
                    vms.append(vm_info)
                except libvirt.libvirtError as e:
                    logger.warning(f"Error getting VM {dom_id}: {str(e)}")
                    continue
        except libvirt.libvirtError as e:
            logger.error(f"Failed to list domains: {str(e)}")
            raise KVMConnectorError(f"Failed to list domains: {str(e)}")
        
        return vms
    
    def _extract_vm_info(self, dom: libvirt.virDomain) -> Dict[str, Any]:
        """Extract VM information from domain object"""
        try:
            name = dom.name()
            uuid = dom.UUIDString()
            dom_id = dom.ID()
            state, max_mem, mem, cpus, cputime = dom.info()
            
            state_map = {
                0: "no state",
                1: "running",
                2: "blocked",
                3: "paused",
                4: "shutdown",
                5: "shutoff",
                6: "crashed",
                7: "suspended"
            }
            
            return {
                "id": dom_id,
                "name": name,
                "uuid": uuid,
                "state": state_map.get(state, "unknown"),
                "cpu_count": cpus,
                "memory_max": max_mem,  # in KiB
                "memory_used": mem,     # in KiB
                "cputime": cputime,     # in ns
            }
        except Exception as e:
            logger.error(f"Error extracting VM info: {str(e)}")
            raise
    
    def get_domain_stats(self) -> Optional[Any]:
        """
        Get detailed domain statistics using getAllDomainStats.
        
        Returns:
            Domain stats or None if not available
        """
        if not self.is_connected():
            raise KVMConnectorError("Not connected to libvirt")
        
        try:
            dom_stats = (
                self._libvirt_compat["VIR_DOMAIN_STATS_STATE"] |
                self._libvirt_compat["VIR_DOMAIN_STATS_CPU_TOTAL"] |
                self._libvirt_compat["VIR_DOMAIN_STATS_BALLOON"] |
                self._libvirt_compat["VIR_DOMAIN_STATS_NET"] |
                self._libvirt_compat["VIR_DOMAIN_STATS_BLOCK"]
            )
            
            stat_flags = (
                self._libvirt_compat["VIR_CONNECT_GET_ALL_DOMAINS_STATS_ACTIVE"] |
                self._libvirt_compat["VIR_CONNECT_GET_ALL_DOMAINS_STATS_RUNNING"]
            )
            
            try:
                return self._conn.getAllDomainStats(dom_stats, stat_flags)
            except TypeError:
                # Fallback for older libvirt versions
                return self._conn.getAllDomainStats(None, dom_stats, stat_flags)
        except libvirt.libvirtError as e:
            logger.warning(f"getAllDomainStats not available: {str(e)}")
            return None
    
    def get_devices_for_vm(self, dom: libvirt.virDomain) -> Tuple[List[str], List[str]]:
        """
        Extract network interfaces and disk devices from VM XML definition.
        Uses caching to avoid repeated XML parsing.
        
        Returns:
            Tuple of (network_interfaces, disk_devices)
        """
        try:
            dom_id = dom.ID()
            now = time.time()
            
            # Check cache
            cached = self._device_cache.get(dom_id)
            if cached and now - cached["ts"] < self.DEVICE_CACHE_TTL:
                return cached["nics"], cached["disks"]
            
            # Parse devices from XML
            root = ET.fromstring(dom.XMLDesc(0))
            nics, disks = [], []
            
            # Extract NICs
            for iface in root.findall("./devices/interface"):
                tgt = iface.find("target")
                if tgt is not None and "dev" in tgt.attrib:
                    nics.append(tgt.attrib["dev"])
            
            # Extract disks
            for d in root.findall("./devices/disk"):
                if d.get("device") != "disk":
                    continue
                tgt = d.find("target")
                if tgt is not None and "dev" in tgt.attrib:
                    disks.append(tgt.attrib["dev"])
            
            # Cache the result
            self._device_cache[dom_id] = {
                "ts": now,
                "nics": nics,
                "disks": disks
            }
            
            return nics, disks
        except Exception as e:
            logger.error(f"Error extracting devices: {str(e)}")
            return [], []
    
    def get_interface_stats(self, dom: libvirt.virDomain, iface_name: str) -> Dict[str, int]:
        """
        Get network interface statistics for a single interface.
        
        Returns:
            Dict with keys: rxbytes, rxpackets, rxerrors, rxdrops, txbytes, txpackets, txerrors, txdrops
        """
        try:
            stats = dom.interfaceStats(iface_name)
            # Returns: (rxbytes, rxpackets, rxerrors, rxdrops, txbytes, txpackets, txerrors, txdrops)
            return {
                "rxbytes": int(stats[0] or 0),
                "rxpackets": int(stats[1] or 0),
                "rxerrors": int(stats[2] or 0),
                "rxdrops": int(stats[3] or 0),
                "txbytes": int(stats[4] or 0),
                "txpackets": int(stats[5] or 0),
                "txerrors": int(stats[6] or 0),
                "txdrops": int(stats[7] or 0),
            }
        except libvirt.libvirtError as e:
            logger.warning(f"Error getting stats for interface {iface_name}: {str(e)}")
            return {
                "rxbytes": 0, "rxpackets": 0, "rxerrors": 0, "rxdrops": 0,
                "txbytes": 0, "txpackets": 0, "txerrors": 0, "txdrops": 0,
            }
    
    def get_block_stats(self, dom: libvirt.virDomain, block_name: str) -> Dict[str, int]:
        """
        Get block device (disk) I/O statistics.
        
        Returns:
            Dict with keys: rd_req, rd_bytes, wr_reqs, wr_bytes, errors
        """
        try:
            stats = dom.blockStats(block_name)
            # Returns: (rd_req, rd_bytes, wr_reqs, wr_bytes, errs)
            return {
                "rd_req": int(stats[0] or 0),
                "rd_bytes": int(stats[1] or 0),
                "wr_reqs": int(stats[2] or 0),
                "wr_bytes": int(stats[3] or 0),
                "errors": int(stats[4] or 0),
            }
        except libvirt.libvirtError as e:
            logger.warning(f"Error getting stats for block {block_name}: {str(e)}")
            return {
                "rd_req": 0, "rd_bytes": 0, "wr_reqs": 0, "wr_bytes": 0, "errors": 0
            }
    
    def get_memory_stats(self, dom: libvirt.virDomain) -> Dict[str, int]:
        """
        Get extended memory statistics using memoryStats().
        
        Returns:
            Dict with memory metrics including balloon stats
        """
        try:
            mem_stats = dom.memoryStats()
            
            # Extract memory fields with defaults to 0
            return {
                "memactual": int(mem_stats.get("actual", 0) or 0),
                "memrss": int(mem_stats.get("rss", 0) or 0),
                "memavailable": int(mem_stats.get("available", 0) or 0),
                "memusable": int(mem_stats.get("usable", 0) or 0),
                "memswap_in": int(mem_stats.get("swap_in", 0) or 0),
                "memswap_out": int(mem_stats.get("swap_out", 0) or 0),
                "memmajor_fault": int(mem_stats.get("major_fault", 0) or 0),
                "memminor_fault": int(mem_stats.get("minor_fault", 0) or 0),
                "memdisk_cache": int(mem_stats.get("disk_caches", 0) or 0),
            }
        except libvirt.libvirtError as e:
            logger.warning(f"Error getting memory stats: {str(e)}")
            return {
                "memactual": 0, "memrss": 0, "memavailable": 0, "memusable": 0,
                "memswap_in": 0, "memswap_out": 0, "memmajor_fault": 0,
                "memminor_fault": 0, "memdisk_cache": 0,
            }
    
    def get_cpu_stats(self, dom: libvirt.virDomain) -> Dict[str, int]:
        """
        Get CPU time breakdown (user vs system mode).
        
        Returns:
            Dict with keys: timeusr (user time), timesys (system time)
        """
        try:
            # Get detailed domain stats if available
            stats = dom.getCPUStats(True)  # True = live CPU stats
            
            # Try to extract user and system time
            if isinstance(stats, list) and len(stats) > 0:
                cpu_dict = stats[0]
                return {
                    "timeusr": int(cpu_dict.get("user_time", 0) or 0),
                    "timesys": int(cpu_dict.get("system_time", 0) or 0),
                }
        except libvirt.libvirtError:
            pass
        
        # Fallback: try domainGetStats for CPU breakdown
        try:
            dom_stats = (
                self._libvirt_compat["VIR_DOMAIN_STATS_CPU_TOTAL"]
            )
            stats_flags = (
                self._libvirt_compat["VIR_CONNECT_GET_ALL_DOMAINS_STATS_ACTIVE"]
            )
            
            all_stats = self._conn.getAllDomainStats(dom_stats, stats_flags)
            for dom_obj, stats_dict in all_stats:
                if dom_obj.ID() == dom.ID():
                    return {
                        "timeusr": int(stats_dict.get("cpu.time", 0) or 0),
                        "timesys": int(stats_dict.get("cpu.system", 0) or 0),
                    }
        except (libvirt.libvirtError, TypeError):
            pass
        
        # Default values if unable to retrieve
        logger.debug("Unable to retrieve CPU breakdown stats")
        return {
            "timeusr": 0,
            "timesys": 0,
        }
