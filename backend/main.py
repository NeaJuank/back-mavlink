# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from backend.api import rest
from backend.config import API_HOST, API_PORT, LOG_LEVEL, MAVLINK_BAUD, detect_mavlink_device
from sqlalchemy import text 

logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Drone Control API",
    description="API REST para control de dron vía MAVLink",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir rutas
app.include_router(rest.router, prefix="/api", tags=["drone"])

# Inicialización en eventos de ciclo de vida para evitar side-effects en import
@app.on_event("startup")
def startup_event():
    try:
        device = detect_mavlink_device()
        logger.info(f"Selected MAVLink device: {device}")
        rest.init_mav(device, MAVLINK_BAUD)
        # Start a background monitor that will switch to SIM or to the real
        # device automatically when the Pi is attached/detached.
        rest.start_monitoring(MAVLINK_BAUD, interval=5)
    except Exception as e:
        logger.error(f"Failed to initialize MAV controller on startup: {e}")

@app.on_event("shutdown")
def shutdown_event():
    try:
        if getattr(rest, 'mav', None):
            try:
                rest.mav.conn.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting MAV: {e}")
    except Exception as e:
        logger.error(f"Error during shutdown cleanup: {e}")

@app.get("/")
def root():
    return {
        "message": "Drone Control API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=API_HOST, port=API_PORT)