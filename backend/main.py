import asyncio
import logging
from fastapi import FastAPI, WebSocket
from config import MAVLINK_DEVICE, MAVLINK_BAUD
from mavlink.connection import MAVLinkConnection
from mavlink.telemetry import TelemetryBuffer
from db.repository import save_telemetry
from api.rest import router
from api.websocket import telemetry_ws

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
app.include_router(router)

mav = MAVLinkConnection(MAVLINK_DEVICE, MAVLINK_BAUD)
telemetry = TelemetryBuffer()

@app.websocket("/ws/telemetry")
async def ws(ws: WebSocket):
    await telemetry_ws(ws, telemetry)

async def mavlink_loop():
    while True:
        try:
            msg = mav.recv()
            if msg:
                telemetry.update(msg)
                if telemetry.should_persist():
                    save_telemetry(telemetry.data)
                    telemetry.last_save = telemetry.data["timestamp"]
        except Exception as e:
            logger.error(f"Error in MAVLink loop: {e}")
        await asyncio.sleep(0.01)

@app.on_event("startup")
async def startup():
    asyncio.create_task(mavlink_loop())

###asi se inicia chavales "uvicorn main:app --reload"