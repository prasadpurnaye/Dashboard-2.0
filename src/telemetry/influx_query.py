"""
InfluxDB Query Module
Queries metrics from InfluxDB to get VM information and status
"""

import requests
import logging
from typing import Dict, Any, List, Set
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class InfluxQueryError(Exception):
    """Raised when InfluxDB query operations fail"""
    pass


class InfluxQuery:
    """Query metrics from InfluxDB v3"""
    
    def __init__(self, url: str, db: str, token: str):
        """
        Initialize InfluxDB query client.
        
        Args:
            url: InfluxDB URL (e.g., http://localhost:8181)
            db: Database/bucket name
            token: Bearer token for authentication
        """
        self.url = url.rstrip('/')
        self.db = db
        self.token = token
        self.headers = {"Authorization": f"Bearer {token}"}
        self.query_endpoint = f"{self.url}/api/v3/query"
        
        logger.info(f"InfluxDB query client initialized: {self.url}/db={self.db}")
    
    def get_unique_vms(self) -> List[Dict[str, Any]]:
        """
        Get unique VMs from InfluxDB by querying vm_info measurements.
        Extracts VMID, name, uuid from tags.
        
        Returns:
            List of unique VMs with their metadata
        """
        try:
            # Query to get unique VM identifiers from the last 24 hours
            query = f"""
            SELECT DISTINCT "name", "VMID", "uuid" 
            FROM "vm_info" 
            WHERE time > now() - 24h
            ORDER BY "VMID"
            """
            
            params = {
                "db": self.db,
                "q": query
            }
            
            response = requests.get(
                self.query_endpoint,
                headers=self.headers,
                params=params,
                timeout=10
            )
            
            if response.status_code != 200:
                logger.warning(f"InfluxDB query failed: {response.status_code} - {response.text}")
                return []
            
            vms = self._parse_vm_response(response.json())
            logger.info(f"Found {len(vms)} unique VMs in InfluxDB")
            return vms
        
        except Exception as e:
            logger.error(f"Error querying VMs from InfluxDB: {str(e)}")
            return []
    
    def get_latest_collection_time(self) -> str:
        """
        Get the timestamp of the latest metrics collection.
        
        Returns:
            ISO format timestamp or "Never" if no data
        """
        try:
            # Query to get the latest timestamp from any vm_info measurement
            query = f"""
            SELECT MAX(time) as latest_time 
            FROM "vm_info"
            """
            
            params = {
                "db": self.db,
                "q": query
            }
            
            response = requests.get(
                self.query_endpoint,
                headers=self.headers,
                params=params,
                timeout=10
            )
            
            if response.status_code != 200:
                return "Never"
            
            data = response.json()
            if not data or not data.get("results"):
                return "Never"
            
            # Parse the timestamp from response
            result = data["results"][0] if data["results"] else None
            if result and "series" in result:
                series = result["series"][0] if result["series"] else None
                if series and "values" in series:
                    values = series["values"]
                    if values and len(values) > 0:
                        # values[0][0] should contain the timestamp
                        timestamp = values[0][0]
                        return str(timestamp)
            
            return "Never"
        
        except Exception as e:
            logger.error(f"Error querying latest collection time: {str(e)}")
            return "Never"
    
    def get_vm_metrics(self, vm_id: str, hours: int = 1) -> Dict[str, Any]:
        """
        Get latest metrics for a specific VM.
        
        Args:
            vm_id: VM ID to query
            hours: Look back this many hours
            
        Returns:
            Dictionary with latest CPU, memory, network metrics
        """
        try:
            query = f"""
            SELECT LAST("cpu_time_ns") as cpu_time,
                   LAST("memory_used_kb") as memory_used,
                   LAST("rx_bytes") as rx_bytes,
                   LAST("tx_bytes") as tx_bytes
            FROM "vm_cpu", "vm_memory", "vm_network"
            WHERE "VMID" = '{vm_id}' AND time > now() - {hours}h
            """
            
            params = {
                "db": self.db,
                "q": query
            }
            
            response = requests.get(
                self.query_endpoint,
                headers=self.headers,
                params=params,
                timeout=10
            )
            
            if response.status_code != 200:
                return {}
            
            return self._parse_metrics_response(response.json())
        
        except Exception as e:
            logger.error(f"Error querying metrics for VM {vm_id}: {str(e)}")
            return {}
    
    def _parse_vm_response(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse InfluxDB response to extract unique VMs.
        
        Args:
            data: Response from InfluxDB query
            
        Returns:
            List of unique VM dictionaries
        """
        vms: Dict[str, Dict[str, Any]] = {}  # Use dict to track unique VMs
        
        try:
            if not data or "results" not in data:
                return []
            
            results = data["results"]
            if not results or "series" not in results[0]:
                return []
            
            series = results[0]["series"]
            if not series:
                return []
            
            for serie in series:
                columns = serie.get("columns", [])
                values = serie.get("values", [])
                
                # Find column indices
                name_idx = columns.index("name") if "name" in columns else -1
                vmid_idx = columns.index("VMID") if "VMID" in columns else -1
                uuid_idx = columns.index("uuid") if "uuid" in columns else -1
                
                # Parse each row
                for value_row in values:
                    vmid = value_row[vmid_idx] if vmid_idx >= 0 else None
                    name = value_row[name_idx] if name_idx >= 0 else None
                    uuid = value_row[uuid_idx] if uuid_idx >= 0 else None
                    
                    if vmid and vmid not in vms:
                        vms[vmid] = {
                            "id": vmid,
                            "name": name or f"VM-{vmid}",
                            "uuid": uuid or "unknown",
                            "source": "influxdb"
                        }
            
            return list(vms.values())
        
        except Exception as e:
            logger.error(f"Error parsing VM response: {str(e)}")
            return []
    
    def _parse_metrics_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse metrics response from InfluxDB.
        
        Args:
            data: Response from InfluxDB query
            
        Returns:
            Dictionary with parsed metrics
        """
        metrics = {
            "cpu_time_ns": 0,
            "memory_used_kb": 0,
            "rx_bytes": 0,
            "tx_bytes": 0
        }
        
        try:
            if not data or "results" not in data:
                return metrics
            
            results = data["results"]
            if not results or "series" not in results[0]:
                return metrics
            
            series = results[0]["series"]
            for serie in series:
                columns = serie.get("columns", [])
                values = serie.get("values", [])
                
                if values and len(values) > 0:
                    for col_idx, col_name in enumerate(columns):
                        if col_name in metrics and col_idx < len(values[0]):
                            metrics[col_name] = values[0][col_idx] or 0
            
            return metrics
        
        except Exception as e:
            logger.error(f"Error parsing metrics response: {str(e)}")
            return metrics
