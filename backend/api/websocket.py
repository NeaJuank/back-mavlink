from fastapi import WebSocket
import asyncio
import logging

logger = logging.getLogger(__name__)

clients = []

async def telemetry_ws(ws: WebSocket, telemetry_buffer):
    await ws.accept()
    clients.append(ws)
    logger.info("WebSocket client connected")

    try:
        while True:
            try:
                await ws.send_json(telemetry_buffer.data)
                await asyncio.sleep(0.2)
            except Exception as e:
                logger.error(f"Error sending telemetry: {e}")
                break
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        if ws in clients:
            clients.remove(ws)
        logger.info("WebSocket client disconnected")
