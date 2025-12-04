"""
InfluxDB Query Module
Queries metrics from InfluxDB to get VM information and status
"""

import requests
import logging
import math
from typing import Dict, Any, List, Set
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class InfluxQueryError(Exception):
    """Raised when InfluxDB query operations fail"""
    pass


class InfluxQuery:
    """Query metrics from InfluxDB (v1 API compatible)"""
    
    def __init__(self, url: str, db: str, token: str):
        """
        Initialize InfluxDB query client.
        Uses InfluxDB v1 API which is compatible with InfluxDB 3.x
        
        Args:
            url: InfluxDB URL (e.g., http://localhost:8181)
            db: Database/bucket name
            token: Authentication token (supports both v1 and v3 tokens)
        """
        self.url = url.rstrip('/')
        self.db = db
        self.token = token
        # Use Token header for v1 API (compatible with InfluxDB 3.x)
        self.headers = {"Authorization": f"Token {token}"}
        # Use v1 query endpoint which works with InfluxDB 3.x
        self.query_endpoint = f"{self.url}/query"  # v1 API endpoint
        
        logger.info(f"InfluxDB query client initialized (v1 API): {self.url}/db={self.db}")
    
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
        Get latest metrics for a specific VM from vm_totals measurement.
        Uses InfluxDB v1 API query syntax which is compatible with InfluxDB 3.x
        
        Args:
            vm_id: VM ID to query (as string or int)
            hours: Look back this many hours (not used in this query, we get latest)
            
        Returns:
            Dictionary with latest CPU, memory, network, and disk metrics
        """
        try:
            # InfluxDB v1 query syntax - VMID is a tag
            query = f"""SELECT * FROM "vm_totals" WHERE "VMID"='{vm_id}' ORDER BY time DESC LIMIT 1"""
            
            params = {
                "db": self.db,
                "q": query
            }
            
            logger.debug(f"Querying vm_totals for VM {vm_id} using v1 API")
            
            response = requests.get(
                self.query_endpoint,
                headers=self.headers,
                params=params,
                timeout=10
            )
            
            if response.status_code != 200:
                logger.warning(f"InfluxDB query returned status {response.status_code}")
                return {}
            
            metrics = self._parse_vm_totals_response(response.json())
            if metrics:
                logger.debug(f"Retrieved {len(metrics)} fields for VM {vm_id} from InfluxDB")
            return metrics
        
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

    def _parse_vm_totals_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse vm_totals response from InfluxDB v3.
        
        Args:
            data: Response from InfluxDB query
            
        Returns:
            Dictionary with all available metrics from vm_totals
        """
        metrics = {}
        
        try:
            logger.debug(f"Parsing vm_totals response: {str(data)[:500]}")
            
            if not data:
                logger.warning("Response data is empty or None")
                return metrics
            
            # InfluxDB v3 returns data in "results" key
            if "results" not in data:
                logger.warning(f"No 'results' key in response. Keys: {data.keys()}")
                return metrics
            
            results = data["results"]
            if not results:
                logger.warning("Results array is empty")
                return metrics
            
            # Handle error in result
            if isinstance(results[0], dict) and "error" in results[0]:
                logger.warning(f"Query error in response: {results[0]['error']}")
                return metrics
            
            # InfluxDB v3 returns data as series objects
            if not isinstance(results[0], dict) or "series" not in results[0]:
                logger.warning(f"No 'series' in first result. Result: {results[0]}")
                return metrics
            
            series_list = results[0]["series"]
            if not series_list:
                logger.warning("Series list is empty")
                return metrics
            
            # Get the first series
            serie = series_list[0]
            if not serie:
                logger.warning("First series is empty")
                return metrics
            
            columns = serie.get("columns", [])
            values = serie.get("values", [])
            
            logger.debug(f"Columns: {columns}")
            logger.debug(f"Values count: {len(values) if values else 0}")
            
            if not values or len(values) == 0:
                logger.warning("No values in series response")
                return metrics
            
            # Map column names to values from first row
            value_row = values[0]
            for col_idx, col_name in enumerate(columns):
                if col_idx < len(value_row):
                    value = value_row[col_idx]
                    
                    # Skip time and string tag columns
                    if col_name == "time":
                        continue
                    
                    # Convert to numeric type
                    try:
                        if value is None:
                            metrics[col_name] = 0
                        elif isinstance(value, (int, float)):
                            metrics[col_name] = value
                        elif isinstance(value, bool):
                            metrics[col_name] = 1 if value else 0
                        else:
                            # Try to convert string to number
                            try:
                                metrics[col_name] = float(value) if value != "" else 0
                            except (ValueError, TypeError):
                                # Skip non-numeric columns
                                logger.debug(f"Skipping non-numeric column {col_name}={value}")
                                continue
                    except Exception as e:
                        logger.debug(f"Error converting {col_name}={value}: {str(e)}")
                        metrics[col_name] = 0
            
            logger.info(f"Successfully parsed {len(metrics)} metrics from vm_totals")
            return metrics
        
        except Exception as e:
            logger.error(f"Error parsing vm_totals response: {str(e)}", exc_info=True)
            return metrics


    def get_vm_telemetry_with_rates(self, vm_id: str, minutes: int = 5) -> Dict[str, Any]:
        """
        Get current VM telemetry with rate-of-change calculations.
        
        Args:
            vm_id: VM ID to query
            minutes: Look back this many minutes for rate calculation
            
        Returns:
            Dictionary with current metrics and their rate of change
        """
        try:
            # Query to get last two data points for rate calculation
            query = f"""
            SELECT 
                LAST("net_rxbytes") as rx_bytes_current,
                LAST("net_txbytes") as tx_bytes_current,
                LAST("disk_rd_bytes") as disk_rd_bytes_current,
                LAST("disk_wr_bytes") as disk_wr_bytes_current,
                LAST("cputime") as cpu_time_current
            FROM "vm_totals"
            WHERE "VMID" = '{vm_id}' AND time > now() - {minutes}m
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
                logger.warning(f"Failed to get telemetry for VM {vm_id}: {response.status_code}")
                return self._default_telemetry()
            
            data = response.json()
            current_metrics = self._parse_metrics_response(data)
            
            # Query for previous data point
            query_prev = f"""
            SELECT 
                LAST("net_rxbytes") as rx_bytes_prev,
                LAST("net_txbytes") as tx_bytes_prev,
                LAST("disk_rd_bytes") as disk_rd_bytes_prev,
                LAST("disk_wr_bytes") as disk_wr_bytes_prev,
                LAST("cputime") as cpu_time_prev,
                LAST(time) as prev_time
            FROM "vm_totals"
            WHERE "VMID" = '{vm_id}' AND time < now() - 1m AND time > now() - {minutes}m
            LIMIT 1
            """
            
            params_prev = {
                "db": self.db,
                "q": query_prev
            }
            
            response_prev = requests.get(
                self.query_endpoint,
                headers=self.headers,
                params=params_prev,
                timeout=10
            )
            
            prev_metrics = {}
            if response_prev.status_code == 200:
                prev_metrics = self._parse_metrics_response(response_prev.json())
            
            # Calculate rates
            rates = self._calculate_rates(current_metrics, prev_metrics)
            
            # Combine current metrics and rates
            telemetry = {
                "cpu_usage_percent": self._calculate_cpu_percent(current_metrics.get("cputime", 0)),
                "memory_usage_percent": current_metrics.get("memory_used_kb", 0),
                "disk_read_bytes": current_metrics.get("disk_rd_bytes", 0),
                "disk_write_bytes": current_metrics.get("disk_wr_bytes", 0),
                "network_rx_bytes": current_metrics.get("rx_bytes_current", 0),
                "network_tx_bytes": current_metrics.get("tx_bytes_current", 0),
                "cpu_rate": rates.get("cpu_rate", 0),
                "memory_rate": rates.get("memory_rate", 0),
                "disk_read_rate": rates.get("disk_read_rate", 0),
                "disk_write_rate": rates.get("disk_write_rate", 0),
                "network_rx_rate": rates.get("network_rx_rate", 0),
                "network_tx_rate": rates.get("network_tx_rate", 0),
            }
            
            return telemetry
        
        except Exception as e:
            logger.error(f"Error getting telemetry with rates for VM {vm_id}: {str(e)}")
            return self._default_telemetry()

    def _calculate_rates(self, current: Dict[str, Any], previous: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate rate of change using arctan formula.
        rate = atan((newValue - oldValue) / timeDelta) * 180 / pi
        
        Args:
            current: Current metrics
            previous: Previous metrics
            
        Returns:
            Dictionary with calculated rates
        """
        rates = {
            "cpu_rate": 0.0,
            "memory_rate": 0.0,
            "disk_read_rate": 0.0,
            "disk_write_rate": 0.0,
            "network_rx_rate": 0.0,
            "network_tx_rate": 0.0,
        }
        
        try:
            # Default time delta is 1 second if no previous data
            time_delta = 1.0
            
            if not previous:
                return rates
            
            # Calculate rates for each metric
            metrics_to_calculate = [
                ("cpu_time_current", "cpu_time_prev", "cpu_rate"),
                ("disk_rd_bytes_current", "disk_rd_bytes_prev", "disk_read_rate"),
                ("disk_wr_bytes_current", "disk_wr_bytes_prev", "disk_write_rate"),
                ("rx_bytes_current", "rx_bytes_prev", "network_rx_rate"),
                ("tx_bytes_current", "tx_bytes_prev", "network_tx_rate"),
            ]
            
            for current_key, prev_key, rate_key in metrics_to_calculate:
                current_val = float(current.get(current_key, 0) or 0)
                prev_val = float(previous.get(prev_key, 0) or 0)
                
                if current_val != prev_val and time_delta > 0:
                    delta = current_val - prev_val
                    # rate = atan(delta / time_delta) * 180 / pi
                    rate = math.atan(delta / time_delta) * 180 / math.pi
                    rates[rate_key] = rate
            
            return rates
        
        except Exception as e:
            logger.error(f"Error calculating rates: {str(e)}")
            return rates

    def _calculate_cpu_percent(self, cputime_ns: float) -> float:
        """
        Convert CPU time (nanoseconds) to percentage.
        This is a simplified calculation assuming 100% = 1e9 ns per second.
        
        Args:
            cputime_ns: CPU time in nanoseconds
            
        Returns:
            CPU usage percentage (0-100)
        """
        try:
            # Approximate: assume max CPU time is 1e9 ns per second per core
            # For a rough estimate: usage = (cputime_ns / 1e9) % 100
            percent = (cputime_ns / 1e9) % 100
            return min(100.0, max(0.0, percent))
        except:
            return 0.0

    def _default_telemetry(self) -> Dict[str, Any]:
        """
        Return default telemetry when data is unavailable.
        
        Returns:
            Dictionary with default/zero values
        """
        return {
            "cpu_usage_percent": 0.0,
            "memory_usage_percent": 0.0,
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
