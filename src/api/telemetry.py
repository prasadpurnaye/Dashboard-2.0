"""
Telemetry API Routes
Endpoints for managing telemetry collection
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List, Optional
import logging
import requests

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
    
    Args:
        vm_id: The VM ID to get stats for
        
    Returns:
        Latest metrics for the VM
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
        
        metrics = influx_query.get_vm_metrics(vm_id)
        
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

