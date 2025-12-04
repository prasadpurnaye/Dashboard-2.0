"""
Telemetry API Routes
Endpoints for managing telemetry collection
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List, Optional
import logging
import requests
from datetime import datetime

from src.telemetry.collector import TelemetryCollector, TelemetryCollectorError
from src.telemetry.influx_query import InfluxQuery
from src.config.telemetry_config import TelemetryConfig

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/telemetry", tags=["telemetry"])

# Global collector instance (singleton)
_collector: Optional[TelemetryCollector] = None


def get_collector() -> Optional[TelemetryCollector]:
    """Get global collector instance"""
    return _collector


def set_collector(collector: TelemetryCollector) -> None:
    """Set global collector instance"""
    global _collector
    _collector = collector


@router.post("/start")
async def start_telemetry() -> Dict[str, Any]:
    """
    Start telemetry collection.
    
    Returns:
        Status of telemetry service
    """
    collector = get_collector()
    if not collector:
        raise HTTPException(
            status_code=500,
            detail="Telemetry collector not initialized"
        )
    
    if collector.is_running():
        return {
            "status": "already_running",
            "message": "Telemetry collection is already running",
            "details": collector.get_status()
        }
    
    try:
        success = collector.start()
        if success:
            return {
                "status": "started",
                "message": "Telemetry collection started successfully",
                "details": collector.get_status()
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to start telemetry collection"
            )
    except TelemetryCollectorError as e:
        logger.error(f"Telemetry start error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Telemetry start failed: {str(e)}"
        )


@router.post("/stop")
async def stop_telemetry() -> Dict[str, Any]:
    """
    Stop telemetry collection.
    
    Returns:
        Final status before stopping
    """
    collector = get_collector()
    if not collector:
        raise HTTPException(
            status_code=500,
            detail="Telemetry collector not initialized"
        )
    
    if not collector.is_running():
        return {
            "status": "not_running",
            "message": "Telemetry collection is not running"
        }
    
    try:
        collector.stop()
        return {
            "status": "stopped",
            "message": "Telemetry collection stopped successfully"
        }
    except Exception as e:
        logger.error(f"Telemetry stop error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Telemetry stop failed: {str(e)}"
        )


@router.get("/status")
async def get_telemetry_status() -> Dict[str, Any]:
    """
    Get telemetry collection status.
    
    Returns:
        Detailed status and statistics
    """
    collector = get_collector()
    if not collector:
        return {
            "status": "not_initialized",
            "running": False,
            "message": "Telemetry collector not initialized"
        }
    
    return collector.get_status()


@router.get("/vms")
async def get_monitored_vms() -> Dict[str, Any]:
    """
    Get list of currently monitored VMs.
    
    Returns:
        List of VMs with basic information
    """
    collector = get_collector()
    if not collector:
        raise HTTPException(
            status_code=500,
            detail="Telemetry collector not initialized"
        )
    
    try:
        vms = collector.get_vms()
        # Remove non-serializable 'dom' object from each VM
        vms_serializable = [
            {k: v for k, v in vm.items() if k != "dom"}
            for vm in vms
        ]
        return {
            "count": len(vms_serializable),
            "vms": vms_serializable
        }
    except Exception as e:
        logger.error(f"Error getting VMs: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get VMs: {str(e)}"
        )


@router.get("/config")
async def get_telemetry_config() -> Dict[str, Any]:
    """
    Get telemetry configuration (safe, non-sensitive info only).
    
    Returns:
        Configuration with sensitive data masked
    """
    collector = get_collector()
    if not collector:
        raise HTTPException(
            status_code=500,
            detail="Telemetry collector not initialized"
        )
    
    return {
        "config": collector.config.to_safe_dict()
    }


@router.get("/live-vms")
async def get_live_vms() -> Dict[str, Any]:
    """
    Get list of live VMs currently running on KVM host.
    Uses libvirt API to get real-time VM list.
    
    Returns:
        List of currently running VMs with details
    """
    collector = get_collector()
    if not collector:
        raise HTTPException(
            status_code=500,
            detail="Telemetry collector not initialized"
        )
    
    try:
        # Use the collector's KVM connection if available and connected
        # Otherwise create a fresh connection
        kvm_connector = None
        
        if collector.kvm and collector.kvm.is_connected():
            # Use existing connection
            logger.info("Using existing KVM connection from collector")
            live_vms = collector.kvm.get_live_vms()
        else:
            # Create a fresh connection for this request
            from src.telemetry.kvm_connector import KVMConnector
            
            logger.info("Creating fresh KVM connection for live VMs query")
            kvm_connector = KVMConnector(
                collector.config.libvirt_uri,
                collector.config.libvirt_timeout
            )
            
            if not kvm_connector.connect():
                raise HTTPException(
                    status_code=500,
                    detail="Failed to connect to KVM host"
                )
            
            live_vms = kvm_connector.get_live_vms()
            kvm_connector.disconnect()
        
        logger.info(f"✓ Retrieved {len(live_vms)} live VMs from KVM")
        
        # Remove non-serializable 'dom' object from each VM
        vms_serializable = [
            {k: v for k, v in vm.items() if k != "dom"}
            for vm in live_vms
        ]
        
        return {
            "count": len(vms_serializable),
            "source": "libvirt",
            "vms": vms_serializable
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting live VMs: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get live VMs: {str(e)}"
        )


@router.get("/monitored-vms")
async def get_monitored_vms_from_influx() -> Dict[str, Any]:
    """
    Get unique VMs that have been monitored (from InfluxDB).
    Parses historical data to identify unique Dom values.
    
    Returns:
        List of unique VMs found in monitoring data
    """
    collector = get_collector()
    if not collector:
        raise HTTPException(
            status_code=500,
            detail="Telemetry collector not initialized"
        )
    
    try:
        # Create InfluxDB query client
        influx_query = InfluxQuery(
            collector.config.influx_url,
            collector.config.influx_db,
            collector.config.influx_token
        )
        
        # Get unique VMs from InfluxDB
        unique_vms = influx_query.get_unique_vms()
        
        # Get latest collection time
        latest_collection = influx_query.get_latest_collection_time()
        
        logger.info(f"Found {len(unique_vms)} unique VMs in InfluxDB")
        
        return {
            "count": len(unique_vms),
            "source": "influxdb",
            "last_collection": latest_collection,
            "vms": unique_vms
        }
    
    except Exception as e:
        logger.error(f"Error getting monitored VMs from InfluxDB: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get monitored VMs: {str(e)}"
        )


@router.get("/vm-stats/{vm_id}")
async def get_vm_stats(vm_id: str) -> Dict[str, Any]:
    """
    Get latest statistics for a specific VM from InfluxDB.
    Returns all 26+ metrics with real data from InfluxDB or defaults if unavailable.
    
    Args:
        vm_id: The VM ID to get stats for
        
    Returns:
        Latest metrics for the VM (26 metrics across CPU/Memory, Network, Disk)
    """
    collector = get_collector()
    if not collector:
        raise HTTPException(
            status_code=500,
            detail="Telemetry collector not initialized"
        )
    
    try:
        # Default metrics structure with all 26 fields
        metrics = {
            # VM Info
            "state": "running",
            "cpus": 0,
            "cputime": 0,
            
            # CPU & Memory (11 metrics)
            "timeusr": 0,
            "timesys": 0,
            "memactual": 0,
            "memrss": 0,
            "memavailable": 0,
            "memusable": 0,
            "memswap_in": 0,
            "memswap_out": 0,
            "memmajor_fault": 0,
            "memminor_fault": 0,
            "memdisk_cache": 0,
            
            # Network (8 metrics)
            "net_rxbytes": 0,
            "net_rxpackets": 0,
            "net_rxerrors": 0,
            "net_rxdrops": 0,
            "net_txbytes": 0,
            "net_txpackets": 0,
            "net_txerrors": 0,
            "net_txdrops": 0,
            
            # Disk (5 metrics)
            "disk_rd_req": 0,
            "disk_rd_bytes": 0,
            "disk_wr_reqs": 0,
            "disk_wr_bytes": 0,
            "disk_errors": 0,
        }
        
        try:
            influx_query = InfluxQuery(
                collector.config.influx_url,
                collector.config.influx_db,
                collector.config.influx_token
            )
            
            # Try to get actual metrics from InfluxDB
            db_metrics = influx_query.get_vm_metrics(vm_id)
            if db_metrics:
                logger.info(f"Retrieved {len(db_metrics)} fields from InfluxDB for VM {vm_id}")
                metrics.update(db_metrics)
            else:
                logger.warning(f"No metrics from InfluxDB for VM {vm_id}, using defaults")
        except Exception as e:
            logger.error(f"Could not retrieve metrics from InfluxDB for VM {vm_id}: {str(e)}", exc_info=True)
        
        # Try to get VM info from libvirt if available
        try:
            if collector.kvm and collector.kvm.is_connected():
                vms = collector.kvm.get_live_vms()
                for vm in vms:
                    if str(vm.get("id")) == str(vm_id):
                        metrics["state"] = vm.get("state", "unknown")
                        metrics["cpus"] = vm.get("cpu_count", 0)
                        metrics["cputime"] = vm.get("cputime", 0)
                        break
        except Exception as e:
            logger.debug(f"Could not get VM info from libvirt: {str(e)}")
        
        return {
            "vm_id": vm_id,
            "metrics": metrics
        }
    
    except Exception as e:
        logger.error(f"Error getting VM stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get VM stats: {str(e)}"
        )


@router.get("/vm-telemetry")
async def get_vm_telemetry() -> Dict[str, Any]:
    """
    Get real-time telemetry for all VMs with rate-of-change calculations.
    Falls back to live VM data if no historical telemetry available.
    
    Returns:
        List of VMs with current metrics and rate-of-change values
    """
    collector = get_collector()
    if not collector:
        raise HTTPException(
            status_code=500,
            detail="Telemetry collector not initialized"
        )
    
    try:
        influx_query = InfluxQuery(
            collector.config.influx_url,
            collector.config.influx_db,
            collector.config.influx_token
        )
        
        # Get live VMs from collector or create fresh connection
        vms = []
        if collector.kvm and collector.kvm.is_connected():
            try:
                vms = collector.kvm.get_live_vms()
                logger.debug(f"Got {len(vms)} VMs from collector KVM")
            except Exception as e:
                logger.warning(f"Failed to get VMs from collector KVM: {str(e)}")
        
        # Fallback: create fresh KVM connection if needed
        if not vms:
            try:
                from src.telemetry.kvm_connector import KVMConnector
                logger.info("Creating fresh KVM connection for telemetry")
                kvm_conn = KVMConnector(
                    collector.config.libvirt_uri,
                    collector.config.libvirt_timeout
                )
                if kvm_conn.connect():
                    vms = kvm_conn.get_live_vms()
                    kvm_conn.disconnect()
                    logger.debug(f"Got {len(vms)} VMs from fresh KVM connection")
                else:
                    logger.warning("Failed to connect with fresh KVM connection")
            except Exception as e:
                logger.warning(f"Error creating fresh KVM connection: {str(e)}")
        
        vms_serializable = [
            {k: v for k, v in vm.items() if k != "dom"}
            for vm in vms
        ]
        
        logger.debug(f"VM Telemetry: Processing {len(vms_serializable)} VMs")
        
        # Enhance each VM with telemetry data and rates
        vm_telemetry = []
        for vm in vms_serializable:
            vm_id = str(vm.get("id"))
            
            # Try to get telemetry from InfluxDB
            telemetry = influx_query.get_vm_telemetry_with_rates(vm_id)
            
            # If no telemetry data available, use defaults based on live VM info
            if not telemetry or all(v == 0 for v in telemetry.values() if isinstance(v, (int, float))):
                # Calculate basic metrics from VM info
                memory_gb = (vm.get("memory_max", 0) or 0) / 1024 / 1024
                memory_used_gb = (vm.get("memory_used", 0) or 0) / 1024 / 1024
                memory_percent = (memory_used_gb / memory_gb * 100) if memory_gb > 0 else 0
                
                telemetry = {
                    "cpu_usage_percent": 0.0,
                    "memory_usage_percent": min(100.0, memory_percent),
                    "disk_read_bytes": 0,
                    "disk_write_bytes": 0,
                    "network_rx_bytes": 0,
                    "network_tx_bytes": 0,
                    "cpu_rate": 0.0,
                    "memory_rate": 0.0,
                    "disk_read_rate": 0.0,
                    "disk_write_rate": 0.0,
                    "network_rx_rate": 0.0,
                    "network_tx_rate": 0.0,
                }
            
            # Merge VM info with telemetry
            vm_data = {**vm, **telemetry}
            vm_telemetry.append(vm_data)
        
        return {
            "count": len(vm_telemetry),
            "timestamp": datetime.utcnow().isoformat(),
            "vms": vm_telemetry
        }
    
    except Exception as e:
        logger.error(f"Error getting VM telemetry: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get VM telemetry: {str(e)}"
        )


@router.get("/diagnostic")
async def get_diagnostic_info() -> Dict[str, Any]:
    """
    Get diagnostic information about telemetry setup.
    Useful for troubleshooting connection issues.
    
    Returns:
        Configuration and connection status info
    """
    collector = get_collector()
    if not collector:
        return {
            "status": "error",
            "message": "Collector not initialized"
        }
    
    try:
        from src.telemetry.kvm_connector import KVMConnector
        
        # Check configuration
        config = collector.config.to_safe_dict()
        
        # Test KVM connection
        kvm_status = "unknown"
        kvm_vms = 0
        kvm_error = None
        
        try:
            test_kvm = KVMConnector(
                collector.config.libvirt_uri,
                collector.config.libvirt_timeout
            )
            if test_kvm.connect():
                kvm_status = "connected"
                vms = test_kvm.get_live_vms()
                kvm_vms = len(vms)
                test_kvm.disconnect()
            else:
                kvm_status = "connection_failed"
        except Exception as e:
            kvm_status = "error"
            kvm_error = str(e)
        
        # Test InfluxDB connection
        influx_status = "unknown"
        influx_error = None
        
        try:
            response = requests.get(
                f"{collector.config.influx_url}/ping",
                timeout=5
            )
            if response.status_code in (200, 204):
                influx_status = "connected"
            else:
                influx_status = "error"
                influx_error = f"HTTP {response.status_code}"
        except Exception as e:
            influx_status = "error"
            influx_error = str(e)
        
        return {
            "status": "success",
            "config": config,
            "kvm": {
                "status": kvm_status,
                "live_vms": kvm_vms,
                "error": kvm_error
            },
            "influx": {
                "status": influx_status,
                "error": influx_error
            },
            "collector": {
                "running": collector.is_running(),
                "vms_monitored": collector.stats["vms_monitored"]
            }
        }
    
    except Exception as e:
        logger.error(f"Error getting diagnostic info: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get diagnostic info: {str(e)}"
        )

