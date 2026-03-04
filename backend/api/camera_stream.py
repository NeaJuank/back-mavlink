"""
Streaming de video desde Intel RealSense D435i.
Transmite video en tiempo real vía HTTP MJPEG.

CORRECCIONES:
- generate_mjpeg_stream es ahora async generator para no bloquear el event loop
- Frame negro de fallback cuando la cámara no está disponible (evita hang infinito)
- Guard para rs=None: error claro si pyrealsense2 no está instalado
- camera.start() verifica rs antes de intentar usar la librería
- /stream excluido de Swagger (include_in_schema=False) — no funciona en Swagger UI
- /view agregado: página HTML para ver el stream en el navegador
"""
try:
    import pyrealsense2 as rs
except ImportError:
    rs = None

import numpy as np
import cv2
import threading
import asyncio
import logging
from fastapi import APIRouter, Response
from fastapi.responses import StreamingResponse, HTMLResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/camera", tags=["camera"])

# Frame negro de fallback (640x480, JPEG) — se genera una sola vez
_FALLBACK_FRAME: bytes = b""

def _build_fallback_frame() -> bytes:
    """Genera un frame negro con texto de error, codificado en JPEG."""
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(img, "CAMERA NOT AVAILABLE", (80, 240),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 80, 0), 2)
    _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 70])
    return buf.tobytes()

_FALLBACK_FRAME = _build_fallback_frame()


class RealSenseCamera:
    """Controlador para Intel RealSense D435i."""

    def __init__(self):
        self.pipeline      = None
        self.config        = None
        self.running       = False
        self.current_frame = None
        self.depth_frame   = None
        self.lock          = threading.Lock()

    def start(self, width=640, height=480, fps=30):
        if rs is None:
            raise RuntimeError(
                "pyrealsense2 no está instalado. "
                "Instálalo con: pip install pyrealsense2"
            )

        try:
            self.pipeline = rs.pipeline()
            self.config   = rs.config()
            self.config.enable_stream(rs.stream.color, width, height, rs.format.bgr8, fps)
            self.config.enable_stream(rs.stream.depth, width, height, rs.format.z16,  fps)
            self.pipeline.start(self.config)
            self.running = True

            self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.capture_thread.start()

            logger.info(f"✅ RealSense D435i iniciada — {width}x{height} @ {fps}fps")

        except Exception as e:
            self.running = False
            logger.error(f"Error iniciando RealSense: {e}")
            raise

    def stop(self):
        self.running = False
        if self.pipeline:
            try:
                self.pipeline.stop()
            except Exception:
                pass
        logger.info("RealSense D435i detenida")

    def _capture_loop(self):
        while self.running:
            try:
                frames      = self.pipeline.wait_for_frames(timeout_ms=1000)
                color_frame = frames.get_color_frame()
                depth_frame = frames.get_depth_frame()

                if not color_frame:
                    continue

                color_image = np.asanyarray(color_frame.get_data())
                with self.lock:
                    self.current_frame = color_image.copy()
                    if depth_frame:
                        self.depth_frame = np.asanyarray(depth_frame.get_data())

            except Exception as e:
                logger.error(f"Error capturando frame: {e}")

    def get_frame(self):
        with self.lock:
            return self.current_frame.copy() if self.current_frame is not None else None

    def get_depth_frame(self):
        with self.lock:
            return self.depth_frame.copy() if self.depth_frame is not None else None

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

        cv2.putText(frame, f"ALT: {telemetry.get('altitude', 0):.1f}m",       (10, 30), font, 0.7, green, 2)
        cv2.putText(frame, f"SPD: {telemetry.get('ground_speed', 0):.1f}m/s", (10, 60), font, 0.7, green, 2)

        bat   = telemetry.get("battery_remaining", 0)
        b_col = (0, 255, 0) if bat > 30 else (0, 165, 255) if bat > 15 else (0, 0, 255)
        cv2.putText(frame, f"BAT: {bat}%", (10, 90), font, 0.7, b_col, 2)

        cv2.putText(frame, f"MODE: {telemetry.get('mode', 'UNKNOWN')}", (w - 200, 30), font, 0.7, green, 2)

        armed      = telemetry.get("armed", False)
        armed_text = "ARMED" if armed else "DISARMED"
        armed_col  = (0, 0, 255) if armed else (0, 255, 0)
        cv2.putText(frame, armed_text, (w - 200, 60), font, 0.7, armed_col, 2)

        cx, cy = w // 2, h // 2
        cv2.circle(frame, (cx, cy), 5,  (0, 255, 0), 2)
        cv2.line(frame,   (cx - 20, cy), (cx + 20, cy), (0, 255, 0), 2)
        cv2.line(frame,   (cx, cy - 20), (cx, cy + 20), (0, 255, 0), 2)


# Instancia global de la cámara
camera = RealSenseCamera()


async def generate_mjpeg_stream():
    """
    Generador ASYNC de stream MJPEG.
    Si la cámara no tiene frame disponible se envía el frame de fallback negro.
    """
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


# CAMBIO: include_in_schema=False para excluir de Swagger (no funciona ahí)
@router.get("/stream", response_class=StreamingResponse, include_in_schema=False)
async def video_stream():
    """Endpoint de streaming MJPEG — abrir directo en navegador o <img>."""
    return StreamingResponse(
        generate_mjpeg_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


# NUEVO: página HTML para ver el stream en el navegador
@router.get("/view", response_class=HTMLResponse)
async def view_stream():
    """Abre esta URL en el navegador para ver el video en tiempo real."""
    return HTMLResponse(content="""
<!DOCTYPE html>
<html>
  <head>
    <title>RealSense D435i — Live Stream</title>
    <style>
      body {
        background: #000;
        margin: 0;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        height: 100vh;
        font-family: monospace;
        color: #0f0;
      }
      h3 { margin-bottom: 10px; letter-spacing: 2px; }
      img { max-width: 100%; max-height: 85vh; border: 1px solid #0f0; }
    </style>
  </head>
  <body>
    <h3>📷 RealSense D435i — LIVE</h3>
    <img src="/api/camera/stream" alt="Camera stream" />
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
            return {"success": True, "message": "Cámara iniciada"}
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
        "running":            camera.running,
        "has_frame":          camera.current_frame is not None,
        "realsense_available": rs is not None,
    }