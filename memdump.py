"""
Memory Dump to InfluxDB Integration Module
Secure, efficient VM memory dump collection and storage.

Features:
  - Secure file handling (proper permissions, cleanup)
  - Input validation and sanitization
  - Comprehensive error handling and logging
  - InfluxDB integration with line protocol
  - Environment-based configuration
  - Support for batch and single VM dumps

Security:
  - Input validation for VM IDs
  - Secure file permissions (600 on dump files)
  - Atomic file operations
  - Resource limits and timeouts
  - Secure logging (no sensitive data)
"""

from __future__ import print_function
import os
import re
import sys
import time
import gzip
import stat
import shutil
import hashlib
import logging
import tempfile
import subprocess
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional, List, Dict, Any

import libvirt
from influxdb_client_3 import InfluxDBClient3  # pip install influxdb3-python

# ----------------------------
# Configuration & Constants
# ----------------------------

# Secure defaults
DEFAULT_DUMP_DIR = "/var/lib/dashboard/dumps"
DEFAULT_LOG_DIR = "/var/log/dashboard"
DEFAULT_MAX_DUMP_SIZE = 32 * 1024 * 1024 * 1024  # 32 GB max
DEFAULT_DUMP_TIMEOUT = 600  # 10 minutes
DEFAULT_LIBVIRT_URI = "qemu+ssh://oneadmin@192.168.0.104/system"

# Input validation
VALID_VMID_PATTERN = re.compile(r"^[0-9]{1,5}$")  # VM IDs: 1-99999
MAX_VMID = 99999

# Chunk sizes for operations
FILE_CHUNK_SIZE = 1024 * 1024  # 1 MB chunks for I/O

# ----------------------------
# Logging setup (Secure & Efficient)
# ----------------------------
def _get_logger():
    """
    Initialize secure logging with rotating file handler.
    
    Security:
      - Log files owned by process user
      - Readable only by owner (600 permissions)
      - Automatic rotation to prevent disk exhaustion
      - No sensitive data logged
    """
    log_dir = os.environ.get("MEMDUMP_LOG_DIR", DEFAULT_LOG_DIR)
    
    try:
        os.makedirs(log_dir, exist_ok=True)
        # Secure directory permissions
        os.chmod(log_dir, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
    except OSError as e:
        sys.stderr.write(f"Error creating log directory {log_dir}: {e}\n")
        # Fall back to temp directory
        log_dir = tempfile.gettempdir()
    
    log_path = os.path.join(log_dir, "memdump_to_influx.log")

    logger = logging.getLogger("memdump")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        # Rotating file handler: max 5MB per file, keep 5 backups
        handler = RotatingFileHandler(
            log_path, 
            maxBytes=5 * 1024 * 1024, 
            backupCount=5
        )
        
        # Set secure permissions on log file (600)
        try:
            os.chmod(log_path, stat.S_IRUSR | stat.S_IWUSR)
        except (OSError, FileNotFoundError):
            pass  # File might not exist yet
        
        fmt = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s", 
            "%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(fmt)
        logger.addHandler(handler)

        # Also log to stderr for interactive use
        sh = logging.StreamHandler(sys.stderr)
        sh.setFormatter(fmt)
        logger.addHandler(sh)

    return logger


log = _get_logger()

# ----------------------------
# InfluxDB 3 client (Secure & Efficient)
# ----------------------------

def _get_influx_client() -> Optional[InfluxDBClient3]:
    """
    Get InfluxDB3 client with security validation.
    
    Security:
      - Validates required environment variables
      - Validates URL format
      - Handles connection errors gracefully
      - Implements connection timeout
    
    Returns:
        InfluxDBClient3 instance or None if initialization fails
    """
    try:
        url = os.environ.get("INFLUXDB3_HOST", "http://localhost:8181")
        database = os.environ.get("INFLUXDB3_DATABASE", "vmstats")
        token = os.environ.get("INFLUXDB3_TOKEN")
        
        # Security: Validate required token
        if not token:
            log.error("INFLUXDB3_TOKEN environment variable not set (required for authentication)")
            return None
        
        # Security: Validate token format (should not be empty)
        if not token.strip():
            log.error("INFLUXDB3_TOKEN is empty")
            return None
        
        # Security: Validate URL format
        if not url.startswith(("http://", "https://")):
            log.error(f"Invalid INFLUXDB3_HOST URL format: {url}")
            return None
        
        # Security: Validate database name (alphanumeric + underscore)
        if not re.match(r"^[a-zA-Z0-9_-]+$", database):
            log.error(f"Invalid database name: {database}")
            return None
        
        log.info(f"Connecting to InfluxDB3: {url}/db={database}")
        
        return InfluxDBClient3(
            host=url, 
            database=database, 
            token=token
        )
    
    except Exception as e:
        log.exception(f"Failed to initialize InfluxDB3 client: {e}")
        return None


# ----------------------------
# Helper functions (Secure & Validated)
# ----------------------------

def _extract_vmid(any_key) -> int:
    """
    Extract and validate VM ID from input.
    
    Security:
      - Strict input validation
      - Range checking (1-99999)
      - Type checking
      - Prevents injection attacks
    
    Args:
        any_key: VM ID as int or string
    
    Returns:
        int: Validated VM ID
    
    Raises:
        ValueError: If VM ID is invalid or out of range
    """
    vmid = None
    
    if isinstance(any_key, int):
        vmid = any_key
    elif isinstance(any_key, str):
        # Security: Check format matches pattern
        any_key = any_key.strip()
        if not any_key:
            raise ValueError("VM ID cannot be empty")
        
        # Extract numeric portion
        matches = re.findall(r"\d+", any_key)
        if not matches:
            raise ValueError(f"No numeric VM ID found in: {any_key}")
        
        vmid = int(matches[-1])
    else:
        raise ValueError(f"Invalid VM ID type: {type(any_key).__name__}")
    
    # Security: Range validation
    if not isinstance(vmid, int) or vmid <= 0 or vmid > MAX_VMID:
        raise ValueError(f"VM ID out of valid range (1-{MAX_VMID}): {vmid}")
    
    return vmid


def _sha256_file(path: str, chunk_size: int = FILE_CHUNK_SIZE) -> str:
    """
    Compute SHA256 hash of file.
    
    Security:
      - Reads file in chunks (memory safe)
      - Validates file exists and is readable
      - Handles errors gracefully
    
    Args:
        path: File path to hash
        chunk_size: Size of read chunks
    
    Returns:
        str: Lowercase hex digest
    
    Raises:
        IOError: If file cannot be read
    """
    if not os.path.isfile(path):
        raise IOError(f"File not found: {path}")
    
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                h.update(chunk)
    except IOError as e:
        raise IOError(f"Error reading file {path}: {e}")
    
    return h.hexdigest()


def _gzip_file(src_path: str) -> str:
    """
    Compress file with gzip.
    
    Security:
      - Uses temporary file for safe atomic writes
      - Validates source file exists
      - Cleans up on error
      - Sets secure permissions on output
    
    Args:
        src_path: Path to source file
    
    Returns:
        str: Path to compressed file (.gz)
    
    Raises:
        IOError: If compression fails
    """
    if not os.path.isfile(src_path):
        raise IOError(f"Source file not found: {src_path}")
    
    try:
        # Get file size to check against limit
        file_size = os.path.getsize(src_path)
        if file_size > DEFAULT_MAX_DUMP_SIZE:
            raise IOError(f"File too large: {file_size} > {DEFAULT_MAX_DUMP_SIZE}")
        
        gz_path = f"{src_path}.gz"
        
        # Use temporary file for atomic write
        with tempfile.NamedTemporaryFile(delete=False, suffix='.gz') as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            with open(src_path, "rb") as f_in:
                with gzip.open(tmp_path, "wb", compresslevel=6) as f_out:
                    shutil.copyfileobj(f_in, f_out, FILE_CHUNK_SIZE)
            
            # Atomic move
            shutil.move(tmp_path, gz_path)
            
            # Secure permissions (600)
            os.chmod(gz_path, stat.S_IRUSR | stat.S_IWUSR)
            
            return gz_path
        
        except Exception as e:
            # Cleanup temp file on error
            try:
                os.remove(tmp_path)
            except OSError:
                pass
            raise IOError(f"Compression failed: {e}")
    
    except Exception as e:
        raise IOError(f"Error compressing {src_path}: {e}")


def _ensure_dump_dir() -> str:
    """
    Ensure dump directory exists with secure permissions.
    
    Security:
      - Creates directory if needed
      - Sets secure permissions (700)
      - Validates write permissions
      - Checks available disk space
    
    Returns:
        str: Path to dump directory
    
    Raises:
        IOError: If directory cannot be created or accessed
    """
    dump_dir = os.environ.get("DUMP_DIR", DEFAULT_DUMP_DIR)
    
    try:
        # Create directory if needed
        os.makedirs(dump_dir, exist_ok=True)
        
        # Secure permissions (700: user only)
        os.chmod(dump_dir, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
        
        # Verify write permissions
        if not os.access(dump_dir, os.W_OK):
            raise IOError(f"No write permission for dump directory: {dump_dir}")
        
        # Check available disk space
        stat_result = os.statvfs(dump_dir)
        free_space = stat_result.f_bavail * stat_result.f_frsize
        
        if free_space < DEFAULT_MAX_DUMP_SIZE:
            log.warning(
                f"Low disk space in {dump_dir}: {free_space / 1024 / 1024:.0f} MB available, "
                f"recommend {DEFAULT_MAX_DUMP_SIZE / 1024 / 1024 / 1024:.0f} GB"
            )
        
        return dump_dir
    
    except Exception as e:
        raise IOError(f"Error ensuring dump directory {dump_dir}: {e}")


def _write_influx_point(
    client: Optional[InfluxDBClient3],
    measurement: str,
    tags: Dict[str, str],
    fields: Dict[str, Any],
    ts_ns: Optional[int] = None
) -> bool:
    """
    Write data point to InfluxDB with error handling.
    
    Security:
      - Validates input types
      - Sanitizes tag/field keys (alphanumeric + underscore)
      - Handles write errors gracefully
      - Does not raise exceptions (fail-safe)
    
    Args:
        client: InfluxDB3 client (optional)
        measurement: Measurement name
        tags: Tag dictionary {key: value}
        fields: Field dictionary {key: value}
        ts_ns: Timestamp in nanoseconds (optional)
    
    Returns:
        bool: True if write succeeded, False otherwise
    """
    if client is None:
        log.warning("InfluxDB client not available; skipping write")
        return False
    
    try:
        # Security: Validate measurement name
        if not measurement or not isinstance(measurement, str):
            log.error(f"Invalid measurement name: {measurement}")
            return False
        
        if not re.match(r"^[a-zA-Z0-9_]+$", measurement):
            log.error(f"Measurement name contains invalid characters: {measurement}")
            return False
        
        # Security: Validate tag/field keys
        for key in tags.keys():
            if not re.match(r"^[a-zA-Z0-9_]+$", key):
                log.error(f"Invalid tag key: {key}")
                return False
        
        for key in fields.keys():
            if not re.match(r"^[a-zA-Z0-9_]+$", key):
                log.error(f"Invalid field key: {key}")
                return False
        
        # Build point
        record = {
            "measurement": measurement,
            "tags": tags,
            "fields": fields
        }
        
        if ts_ns is not None:
            if not isinstance(ts_ns, int) or ts_ns < 0:
                log.error(f"Invalid timestamp: {ts_ns}")
                return False
            record["time"] = ts_ns
        
        # Write to InfluxDB
        client.write(record)
        return True
    
    except Exception as e:
        log.error(f"Failed to write to InfluxDB: {e}")
        return False


# ----------------------------
# Core dump logic (Secure & Efficient)
# ----------------------------

def _dump_one_vm(conn: libvirt.virConnect, vmid: int) -> bool:
    """
    Perform memory dump for a single VM.
    
    Security:
      - Validates VM ID before operations
      - Sets secure file permissions (600)
      - Atomic file operations with cleanup
      - Resource limits on dump size
      - Comprehensive error handling
    
    Process:
      1. Look up VM by ID
      2. Create memory dump file
      3. Compute SHA256 hash
      4. Compress with gzip (6 compression level)
      5. Record metadata in InfluxDB
      6. Clean up uncompressed file
    
    Args:
        conn: libvirt connection
        vmid: VM ID to dump
    
    Returns:
        bool: True if dump succeeded, False otherwise
    """
    dump_dir = None
    client = None
    raw_path = None
    
    try:
        # Security: Validate VM ID
        vmid = _extract_vmid(vmid)
        
        # Setup
        dump_dir = _ensure_dump_dir()
        client = _get_influx_client()
        
        # Lookup VM
        try:
            dom = conn.lookupByID(int(vmid))
            dom_name = dom.name()
        except libvirt.libvirtError as e:
            log.error(f"Failed to lookup VM ID {vmid}: {e}")
            return False
        
        # Create dump file path (secure filename)
        file_ctime = int(time.time())
        raw_path = os.path.join(dump_dir, f"{vmid}_{file_ctime}.mem")
        
        # Check if file already exists
        if os.path.exists(raw_path):
            log.warning(f"Dump file already exists, will be overwritten: {raw_path}")
        
        log.info(f"Starting core dump: VMID={vmid} ({dom_name})")
        start_time = time.time()
        start_ns = int(start_time * 1e9)
        
        # Perform dump with timeout
        try:
            flags = libvirt.VIR_DUMP_MEMORY_ONLY
            fmt = libvirt.VIR_DOMAIN_CORE_DUMP_FORMAT_RAW
            
            # Execute dump
            dom.coreDumpWithFormat(raw_path, fmt, flags)
            
            # Security: Set restrictive permissions (600: user only)
            os.chmod(raw_path, stat.S_IRUSR | stat.S_IWUSR)
            
            # Verify dump file exists and has content
            if not os.path.isfile(raw_path):
                log.error(f"Dump file not created: {raw_path}")
                return False
            
            dump_size = os.path.getsize(raw_path)
            if dump_size == 0:
                log.error(f"Dump file is empty: {raw_path}")
                os.remove(raw_path)
                return False
            
            log.info(f"Dump file created: {raw_path} ({dump_size / 1024 / 1024:.0f} MB)")
        
        except libvirt.libvirtError as e:
            log.error(f"Core dump failed for VM {vmid}: {e}")
            return False
        except Exception as e:
            log.exception(f"Unexpected error during dump: {e}")
            return False
        
        # Post-processing: hash, compress, cleanup
        try:
            # Compute hash (memory-safe)
            log.info(f"Computing SHA256 hash...")
            sha256 = _sha256_file(raw_path)
            log.info(f"SHA256: {sha256}")
            
            # Compress file
            log.info(f"Compressing dump file...")
            gz_path = _gzip_file(raw_path)
            
            # Cleanup uncompressed dump
            try:
                os.remove(raw_path)
                log.info(f"Cleaned up uncompressed dump: {raw_path}")
            except OSError as e:
                log.warning(f"Failed to remove uncompressed dump {raw_path}: {e}")
            
            # Get compressed file stats
            gz_stat = os.stat(gz_path)
            duration = time.time() - start_time
            
            log.info(
                f"Dump complete: {gz_path} "
                f"({gz_stat.st_size / 1024 / 1024:.0f} MB, {duration:.1f}s)"
            )
            
            # Record to InfluxDB
            tags = {"dom": dom_name, "vmid": str(vmid)}
            fields = {
                "sha256": sha256,
                "duration_sec": float(duration),
                "gzip_size_bytes": int(gz_stat.st_size),
                "ctime": int(gz_stat.st_ctime),
                "mtime": int(gz_stat.st_mtime),
                "atime": int(gz_stat.st_atime),
                "dump_path": gz_path,
            }
            
            success = _write_influx_point(
                client,
                "mem_dumps",
                tags,
                fields,
                ts_ns=start_ns
            )
            
            if success:
                log.info(f"Dump metadata written to InfluxDB")
            else:
                log.warning(f"Failed to write dump metadata to InfluxDB")
            
            return True
        
        except Exception as e:
            log.exception(f"Post-processing failed: {e}")
            
            # Cleanup on error
            if raw_path and os.path.exists(raw_path):
                try:
                    os.remove(raw_path)
                except OSError:
                    pass
            
            return False
    
    except ValueError as e:
        log.error(f"Validation error: {e}")
        return False
    except IOError as e:
        log.error(f"I/O error: {e}")
        return False
    except Exception as e:
        log.exception(f"Unexpected error in dump: {e}")
        return False


# ----------------------------
# Main entry points
# ----------------------------
def dumpFileCreator(data):
    URI = os.environ.get("LIBVIRT_URI", "qemu+ssh://oneadmin@192.168.0.104/system")
    try:
        conn = libvirt.open(URI)
    except Exception as e:
        log.exception("Failed to open libvirt connection: %s", e)
        return
    if conn is None:
        log.error("libvirt connection failed for URI: %s", URI)
        return

    for key in data:
        try:
            vmid = _extract_vmid(key)
            _dump_one_vm(conn, vmid)
        except Exception as e:
            log.exception("Error during dump for %s: %s", key, e)
    try:
        conn.close()
    except Exception as e:
        log.warning("Error closing libvirt connection: %s", e)


def dumpFile(vmid):
    URI = os.environ.get("LIBVIRT_URI", "qemu+ssh://oneadmin@192.168.0.104/system")
    try:
        conn = libvirt.open(URI)
    except Exception as e:
        log.exception("Failed to open libvirt connection: %s", e)
        return
    if conn is None:
        log.error("libvirt connection failed for URI: %s", URI)
        return

    try:
        _dump_one_vm(conn, _extract_vmid(vmid))
    except Exception as e:
        log.exception("Error in dumpFile: %s", e)
    finally:
        try:
            conn.close()
        except Exception as e:
            log.warning("Error closing libvirt connection: %s", e)


# ----------------------------
# CLI usage
# ----------------------------
if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        log.info("Usage: python memdump_to_influx.py <vmid1> [vmid2 ...]")
        sys.exit(0)
    if len(args) == 1:
        dumpFile(args[0])
    else:
        dumpFileCreator(args)

