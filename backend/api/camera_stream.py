"""
Streaming de video desde Intel RealSense D435i via OpenCV (V4L2).
Incluye WebSocket para streaming fluido en React Native.
"""

import cv2
import numpy as np
import threading
import asyncio
import base64
import logging
from fastapi import APIRouter, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse, HTMLResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/camera", tags=["camera"])

# ── Frame de fallback ────────────────────────────────────────
def _build_fallback_frame() -> bytes:
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(img, "CAMERA NOT AVAILABLE", (80, 240),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 80, 0), 2)
    _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 70])
    return buf.tobytes()

_FALLBACK_FRAME: bytes = _build_fallback_frame()

# Dispositivos de video a probar
VIDEO_DEVICES = [4, 2, 0, 1, 3, 5]

# Clientes WebSocket conectados
_ws_clients: set = set()


# ── Controlador de cámara ────────────────────────────────────
class RealSenseCamera:
    def __init__(self):
        self.cap           = None
        self.running       = False
        self.current_frame = None
        self.lock          = threading.Lock()
        self._device_index = None
        self._width        = 640
        self._height       = 480
        self._fps          = 30

    def start(self, width: int = 640, height: int = 480, fps: int = 30):
        self._width  = width
        self._height = height
        self._fps    = fps

        for idx in VIDEO_DEVICES:
            cap = cv2.VideoCapture(idx)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_FRAME_WIDTH,  width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                cap.set(cv2.CAP_PROP_FPS,          fps)
                self.cap           = cap
                self._device_index = idx
                self.running       = True
                logger.info(f"✅ Cámara iniciada en /dev/video{idx} — {width}x{height} @ {fps}fps")
                break
            cap.release()

        if not self.running:
            raise RuntimeError("No device connected")

        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()

    def stop(self):
        self.running = False
        if self.cap:
            self.cap.release()
            self.cap = None
        logger.info("🛑 Cámara detenida")

    def _capture_loop(self):
        while self.running:
            if self.cap is None:
                break
            ret, frame = self.cap.read()
            if ret:
                with self.lock:
                    self.current_frame = frame.copy()
            else:
                logger.warning("⚠️  Frame no disponible, reintentando...")
                import time
                time.sleep(0.1)

    def get_frame(self):
        with self.lock:
            return self.current_frame.copy() if self.current_frame is not None else None

    def get_frame_as_base64(self) -> str | None:
        frame = self.get_frame()
        if frame is None:
            return None
        small = cv2.resize(frame, (480, 360))
        ret, buf = cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, 75])
        if not ret:
            return None
        return base64.b64encode(buf.tobytes()).decode("utf-8")

    def get_frame_with_overlay(self, telemetry=None):
        frame = self.get_frame()
        if frame is None:
            return None
        if telemetry:
            self._draw_hud(frame, telemetry)
        return frame

    def _draw_hud(self, frame, telemetry):
        h, w  = frame.shape[:2]
        font  = cv2.FONT_HERSHEY_SIMPLEX
        green = (0, 255, 0)

        cv2.putText(frame, f"ALT: {telemetry.get('altitude', 0):.1f}m",
                    (10, 30), font, 0.7, green, 2)
        cv2.putText(frame, f"SPD: {telemetry.get('ground_speed', 0):.1f}m/s",
                    (10, 60), font, 0.7, green, 2)

        bat   = telemetry.get("battery_remaining", 0)
        b_col = (0, 255, 0) if bat > 30 else (0, 165, 255) if bat > 15 else (0, 0, 255)
        cv2.putText(frame, f"BAT: {bat}%", (10, 90), font, 0.7, b_col, 2)

        cv2.putText(frame, f"MODE: {telemetry.get('mode', 'UNKNOWN')}",
                    (w - 200, 30), font, 0.7, green, 2)

        armed     = telemetry.get("armed", False)
        armed_col = (0, 0, 255) if armed else (0, 255, 0)
        cv2.putText(frame, "ARMED" if armed else "DISARMED",
                    (w - 200, 60), font, 0.7, armed_col, 2)

        cx, cy = w // 2, h // 2
        cv2.circle(frame, (cx, cy), 5, green, 2)
        cv2.line(frame, (cx - 20, cy), (cx + 20, cy), green, 2)
        cv2.line(frame, (cx, cy - 20), (cx, cy + 20), green, 2)


# ── Instancia global ─────────────────────────────────────────
camera = RealSenseCamera()


# ── Auto-inicio ──────────────────────────────────────────────
async def startup_camera():
    try:
        if not camera.running:
            camera.start()
            logger.info("✅ Cámara iniciada automáticamente en startup")
    except Exception as e:
        logger.error(f"❌ No se pudo iniciar cámara en startup: {e}")


async def shutdown_camera():
    camera.stop()


# ── WebSocket endpoint ───────────────────────────────────────
@router.websocket("/ws")
async def camera_websocket(websocket: WebSocket):
    """
    WebSocket para streaming fluido en React Native.
    Envía frames JPEG en base64 a 25fps.
    URL: ws://IP:8000/api/camera/ws
    """
    await websocket.accept()
    _ws_clients.add(websocket)
    logger.info(f"📡 Cliente WS conectado. Total: {len(_ws_clients)}")
    try:
        while True:
            b64 = camera.get_frame_as_base64()
            if b64:
                await websocket.send_text(b64)
            await asyncio.sleep(1 / 25)  # 25 fps
    except WebSocketDisconnect:
        logger.info("📡 Cliente WS desconectado")
    except Exception as e:
        logger.error(f"❌ Error WS: {e}")
    finally:
        _ws_clients.discard(websocket)


# ── Stream MJPEG (para navegador) ────────────────────────────
async def generate_mjpeg_stream():
    while True:
        frame = camera.get_frame()
        if frame is not None:
            ret, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            frame_bytes = buf.tobytes() if ret else _FALLBACK_FRAME
        else:
            frame_bytes = _FALLBACK_FRAME

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n"
            + frame_bytes
            + b"\r\n"
        )
        await asyncio.sleep(1 / 30)


@router.get("/stream", response_class=StreamingResponse, include_in_schema=False)
async def video_stream():
    return StreamingResponse(
        generate_mjpeg_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@router.get("/view", response_class=HTMLResponse)
async def view_stream():
    return HTMLResponse(content="""
<!DOCTYPE html>
<html>
  <head>
    <title>RealSense D435i — Live Stream</title>
    <style>
      body { background:#000; margin:0; display:flex; flex-direction:column;
             justify-content:center; align-items:center; height:100vh;
             font-family:monospace; color:#0f0; }
      h3 { margin-bottom:10px; letter-spacing:2px; }
      img { max-width:100%; max-height:85vh; border:1px solid #0f0; }
      #status { margin-top:10px; font-size:12px; color:#0a0; }
    </style>
  </head>
  <body>
    <h3>📷 RealSense D435i — LIVE</h3>
    <img src="/api/camera/stream" alt="Camera stream"
         onerror="document.getElementById('status').innerText='❌ Stream no disponible'" />
    <div id="status">🟢 Conectando...</div>
  </body>
</html>
""")


@router.get("/snapshot")
async def get_snapshot():
    frame = camera.get_frame()
    if frame is None:
        return Response(content="No hay frame disponible", status_code=503)
    ret, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
    if not ret:
        return Response(content="Error codificando imagen", status_code=500)
    return Response(content=buf.tobytes(), media_type="image/jpeg")


@router.post("/start")
async def start_camera(width: int = 640, height: int = 480, fps: int = 30):
    try:
        if not camera.running:
            camera.start(width, height, fps)
            return {"success": True, "message": f"Cámara iniciada en /dev/video{camera._device_index}"}
        return {"success": False, "message": "Cámara ya está corriendo"}
    except Exception as e:
        logger.error(f"Error iniciando cámara: {e}")
        return {"success": False, "message": str(e)}


@router.post("/stop")
async def stop_camera():
    try:
        if camera.running:
            camera.stop()
            return {"success": True, "message": "Cámara detenida"}
        return {"success": False, "message": "Cámara no está corriendo"}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.get("/status")
async def camera_status():
    return {
        "running":    camera.running,
        "has_frame":  camera.current_frame is not None,
        "device":     f"/dev/video{camera._device_index}" if camera._device_index is not None else None,
        "resolution": f"{camera._width}x{camera._height}",
        "fps":        camera._fps,
        "ws_clients": len(_ws_clients),
    }
