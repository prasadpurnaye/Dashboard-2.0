"""
KVM/QEMU Connector Module
Handles libvirt connections and VM management
"""

import libvirt
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class KVMConnectorError(Exception):
    """Raised when KVM connection operations fail"""
    pass


class KVMConnector:
    """Manages connections to libvirt and retrieves VM information"""
    
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
            List of VM info dicts with keys: id, name, uuid, state, cpu_count, memory
        """
        if not self.is_connected():
            raise KVMConnectorError("Not connected to libvirt")
        
        vms = []
        try:
            for dom_id in self._conn.listDomainsID():
                try:
                    dom = self._conn.lookupByID(dom_id)
                    vms.append(self._extract_vm_info(dom))
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
        
        Returns:
            Tuple of (network_interfaces, disk_devices)
        """
        try:
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
            
            return nics, disks
        except Exception as e:
            logger.error(f"Error extracting devices: {str(e)}")
            return [], []
