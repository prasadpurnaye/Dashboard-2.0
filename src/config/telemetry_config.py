"""
Secure configuration for Telemetry Monitoring
Stores credentials and endpoints as environment variables
Never exposes sensitive data in logs or responses
"""

import os
from typing import Optional
from dataclasses import dataclass


@dataclass
class TelemetryConfig:
    """Secure telemetry configuration from environment variables"""
    
    # LibVirt Configuration
    libvirt_uri: str
    libvirt_timeout: float
    
    # InfluxDB Configuration
    influx_url: str
    influx_db: str
    influx_token: str
    
    # Collection Configuration
    poll_interval: float
    batch_max_lines: int
    batch_max_sec: float
    device_cache_ttl: float
    
    @classmethod
    def from_env(cls) -> 'TelemetryConfig':
        """
        Load configuration from environment variables.
        Raises ValueError if required variables are missing.
        """
        # Required configurations
        libvirt_uri = os.environ.get("LIBVIRT_URI")
        if not libvirt_uri:
            raise ValueError(
                "LIBVIRT_URI not set. Example: qemu+ssh://user@host/system"
            )
        
        influx_url = os.environ.get("INFLUX_URL")
        if not influx_url:
            raise ValueError("INFLUX_URL not set. Example: http://localhost:8181")
        
        influx_db = os.environ.get("INFLUX_DB")
        if not influx_db:
            raise ValueError("INFLUX_DB not set. Example: vmstats")
        
        influx_token = os.environ.get("INFLUX_TOKEN")
        if not influx_token:
            raise ValueError(
                "INFLUX_TOKEN not set. Use a Bearer token from InfluxDB v3"
            )
        
        # Optional configurations with defaults
        poll_interval = float(os.environ.get("POLL_INTERVAL", "1.0"))
        batch_max_lines = int(os.environ.get("BATCH_MAX_LINES", "2000"))
        batch_max_sec = float(os.environ.get("BATCH_MAX_SEC", "1.0"))
        device_cache_ttl = float(os.environ.get("DEVICE_CACHE_TTL", "300"))
        libvirt_timeout = float(os.environ.get("LIBVIRT_TIMEOUT", "30.0"))
        
        return cls(
            libvirt_uri=libvirt_uri,
            libvirt_timeout=libvirt_timeout,
            influx_url=influx_url,
            influx_db=influx_db,
            influx_token=influx_token,
            poll_interval=poll_interval,
            batch_max_lines=batch_max_lines,
            batch_max_sec=batch_max_sec,
            device_cache_ttl=device_cache_ttl,
        )
    
    def to_safe_dict(self) -> dict:
        """
        Return config as dict with sensitive data masked for logging.
        Never use sensitive data in API responses!
        """
        return {
            "libvirt_uri": "***" if self.libvirt_uri else None,
            "influx_url": "***" if self.influx_url else None,
            "influx_db": self.influx_db,
            "poll_interval": self.poll_interval,
            "batch_max_lines": self.batch_max_lines,
            "batch_max_sec": self.batch_max_sec,
            "device_cache_ttl": self.device_cache_ttl,
        }
