from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from src.api.routes import router as api_router
from src.api.telemetry import router as telemetry_router, set_collector
from src.api.memory_dumps import router as memory_dumps_router
import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Dashboard 2.0", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(api_router)
app.include_router(telemetry_router)
app.include_router(memory_dumps_router)

# Serve static files (CSS, JS, images)
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def read_root():
    template_path = os.path.join(os.path.dirname(__file__), "..", "templates", "index.html")
    return FileResponse(template_path)

@app.get("/vms")
async def read_vms():
    template_path = os.path.join(os.path.dirname(__file__), "..", "templates", "vms.html")
    return FileResponse(template_path)

@app.get("/telemetry")
async def read_telemetry():
    template_path = os.path.join(os.path.dirname(__file__), "..", "templates", "telemetry.html")
    return FileResponse(template_path)

@app.get("/memory-dumps")
async def read_memory_dumps():
    template_path = os.path.join(os.path.dirname(__file__), "..", "templates", "memory-dumps.html")
    return FileResponse(template_path)

# Initialize telemetry collector on startup
@app.on_event("startup")
async def startup_event():
    """Initialize telemetry collector on application startup"""
    try:
        from src.config.telemetry_config import TelemetryConfig
        from src.telemetry.collector import TelemetryCollector
        
        # Try to load telemetry config from environment
        try:
            config = TelemetryConfig.from_env()
            collector = TelemetryCollector(config)
            set_collector(collector)
            logger.info("✓ Telemetry collector initialized (ready to start)")
        except ValueError as e:
            logger.warning(f"Telemetry not configured: {str(e)}")
            logger.info("Set environment variables to enable telemetry:")
            logger.info("  - LIBVIRT_URI: qemu+ssh://user@host/system")
            logger.info("  - INFLUX_URL: http://localhost:8181")
            logger.info("  - INFLUX_DB: vmstats")
            logger.info("  - INFLUX_TOKEN: <your-token>")
    
    except Exception as e:
        logger.error(f"Failed to initialize telemetry: {str(e)}")

# Cleanup on shutdown
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup telemetry on application shutdown"""
    try:
        from src.api.telemetry import get_collector
        collector = get_collector()
        if collector and collector.is_running():
            logger.info("Stopping telemetry collector...")
            collector.stop()
            logger.info("✓ Telemetry collector stopped")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)