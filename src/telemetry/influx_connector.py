"""
InfluxDB Connector Module
Handles writing metrics to InfluxDB v3
"""

import requests
import queue
import threading
import time
import logging
from typing import Dict, Any, Optional
import datetime as dt

logger = logging.getLogger(__name__)


class InfluxConnectorError(Exception):
    """Raised when InfluxDB operations fail"""
    pass


class InfluxConnector(threading.Thread):
    """
    Batched InfluxDB v3 line protocol writer
    Runs as background thread with queue-based batching
    """
    
    def __init__(
        self,
        url: str,
        db: str,
        token: str,
        batch_lines: int = 2000,
        batch_sec: float = 1.0,
        max_queue: int = 20000
    ):
        """
        Initialize InfluxDB connector.
        
        Args:
            url: InfluxDB URL (e.g., http://localhost:8181)
            db: Database/bucket name
            token: Bearer token for authentication
            batch_lines: Max lines before flushing
            batch_sec: Max time between flushes
            max_queue: Maximum queue size
        """
        super().__init__(daemon=True)
        
        if not token:
            raise InfluxConnectorError("InfluxDB token is required")
        
        self.url = url.rstrip('/')
        self.db = db
        self.token = token
        self.batch_lines = max(1, batch_lines)
        self.batch_sec = max(0.05, batch_sec)
        
        self.endpoint = f"{self.url}/api/v3/write_lp?db={self.db}&precision=ns"
        self.headers = {"Authorization": f"Bearer {token}"}
        
        self.queue: "queue.Queue[str]" = queue.Queue(maxsize=max_queue)
        self._running = False
        self._stopped_event = threading.Event()
        
        logger.info(f"InfluxDB connector initialized: {self.url}/db={self.db}")
    
    def run(self) -> None:
        """Main thread loop for writing to InfluxDB"""
        self._running = True
        buf = []
        last_flush = time.time()
        session = requests.Session()
        
        logger.info("InfluxDB writer thread started")
        
        try:
            while self._running or not self.queue.empty():
                timeout = max(0.0, self.batch_sec - (time.time() - last_flush))
                
                try:
                    line = self.queue.get(timeout=timeout)
                    buf.append(line)
                except queue.Empty:
                    pass
                
                # Check if should flush
                should_flush = (
                    (len(buf) >= self.batch_lines) or 
                    ((time.time() - last_flush) >= self.batch_sec)
                )
                
                if should_flush and buf:
                    self._flush_batch(session, buf)
                    buf.clear()
                    last_flush = time.time()
        
        except Exception as e:
            logger.error(f"InfluxDB writer error: {str(e)}")
        finally:
            session.close()
            logger.info("InfluxDB writer thread stopped")
            self._stopped_event.set()
    
    def _flush_batch(self, session: requests.Session, lines: list) -> None:
        """Write batch of lines to InfluxDB"""
        if not lines:
            return
        
        payload = "\n".join(lines)
        
        # Log the entries being sent
        ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"\n[{ts}] 📤 Sending {len(lines)} line(s) to InfluxDB:")
        for i, line in enumerate(lines, 1):
            logger.info(f"  [{i}] {line}")
        
        try:
            response = session.post(
                self.endpoint,
                headers=self.headers,
                data=payload,
                timeout=10
            )
            
            ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            if response.status_code in (204, 200):
                logger.info(
                    f"[{ts}] ✅ SUCCESS: Wrote {len(lines)} lines to InfluxDB (HTTP {response.status_code})"
                )
            else:
                logger.warning(
                    f"[{ts}] ❌ FAILED: InfluxDB write error HTTP {response.status_code}: "
                    f"{response.text[:200]}"
                )
        
        except requests.RequestException as e:
            ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logger.error(f"[{ts}] ❌ InfluxDB connection error: {str(e)}")
    
    def enqueue(self, line: str) -> bool:
        """
        Add a line protocol line to the write queue.
        
        Returns:
            True if enqueued, False if queue is full
        """
        try:
            self.queue.put_nowait(line)
            return True
        except queue.Full:
            logger.warning("InfluxDB queue is full, dropping oldest item")
            try:
                self.queue.get_nowait()
                self.queue.put_nowait(line)
                return True
            except queue.Empty:
                return False
    
    def start_writing(self) -> None:
        """Start the background writer thread"""
        if not self.is_alive():
            self.start()
            logger.info("InfluxDB writer started")
    
    def stop_writing(self, timeout: float = 5.0) -> None:
        """
        Stop the writer thread gracefully.
        
        Args:
            timeout: Max time to wait for thread to stop
        """
        self._running = False
        logger.info("Stopping InfluxDB writer...")
        
        if self.is_alive():
            self._stopped_event.wait(timeout=timeout)
        
        if self.is_alive():
            logger.warning("InfluxDB writer did not stop gracefully")
        else:
            logger.info("InfluxDB writer stopped")
    
    def is_writing(self) -> bool:
        """Check if writer thread is active"""
        return self.is_alive() and self._running
    
    def get_queue_size(self) -> int:
        """Get current queue size"""
        return self.queue.qsize()
