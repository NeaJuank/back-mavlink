"""
Streaming de video desde Intel RealSense D435i
Transmite video en tiempo real vía HTTP MJPEG
"""
import pyrealsense2 as rs
import numpy as np
import cv2
import threading
import logging
from fastapi import APIRouter, Response
from fastapi.responses import StreamingResponse
import io

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/camera", tags=["camera"])

class RealSenseCamera:
    """
    Controlador para Intel RealSense D435i
    Captura video y profundidad en tiempo real
    """
    
    def __init__(self):
        self.pipeline = None
        self.config = None
        self.running = False
        self.current_frame = None
        self.depth_frame = None
        self.lock = threading.Lock()
        
    def start(self, width=640, height=480, fps=30):
        """Inicia el streaming de la cámara"""
        try:
            # Configurar pipeline
            self.pipeline = rs.pipeline()
            self.config = rs.config()
            
            # Configurar stream de color
            self.config.enable_stream(rs.stream.color, width, height, rs.format.bgr8, fps)
            
            # Configurar stream de profundidad (opcional)
            self.config.enable_stream(rs.stream.depth, width, height, rs.format.z16, fps)
            
            # Iniciar pipeline
            self.pipeline.start(self.config)
            self.running = True
            
            # Iniciar thread de captura
            self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.capture_thread.start()
            
            logger.info(f"RealSense D435i iniciada - {width}x{height} @ {fps}fps")
            
        except Exception as e:
            logger.error(f"Error iniciando RealSense: {e}")
            raise
    
    def stop(self):
        """Detiene el streaming"""
        self.running = False
        if self.pipeline:
            self.pipeline.stop()
        logger.info("RealSense D435i detenida")
    
    def _capture_loop(self):
        """Loop de captura de frames"""
        while self.running:
            try:
                # Esperar frames
                frames = self.pipeline.wait_for_frames(timeout_ms=1000)
                
                # Obtener frame de color
                color_frame = frames.get_color_frame()
                depth_frame = frames.get_depth_frame()
                
                if not color_frame:
                    continue
                
                # Convertir a numpy array
                color_image = np.asanyarray(color_frame.get_data())
                
                # Actualizar frame actual (thread-safe)
                with self.lock:
                    self.current_frame = color_image.copy()
                    
                    if depth_frame:
                        self.depth_frame = np.asanyarray(depth_frame.get_data())
                
            except Exception as e:
                logger.error(f"Error capturando frame: {e}")
                continue
    
    def get_frame(self):
        """Obtiene el frame actual"""
        with self.lock:
            return self.current_frame.copy() if self.current_frame is not None else None
    
    def get_depth_frame(self):
        """Obtiene el frame de profundidad actual"""
        with self.lock:
            return self.depth_frame.copy() if self.depth_frame is not None else None
    
    def get_frame_with_overlay(self, telemetry=None):
        """
        Obtiene frame con overlay de información (HUD)
        """
        frame = self.get_frame()
        if frame is None:
            return None
        
        # Crear overlay con telemetría
        if telemetry:
            self._draw_hud(frame, telemetry)
        
        return frame
    
    def _draw_hud(self, frame, telemetry):
        """Dibuja HUD (Heads-Up Display) en el frame"""
        height, width = frame.shape[:2]
        
        # Configuración de texto
        font = cv2.FONT_HERSHEY_SIMPLEX
        color = (0, 255, 0)  # Verde
        thickness = 2
        
        # Altitud
        cv2.putText(frame, f"ALT: {telemetry.get('altitude', 0):.1f}m", 
                    (10, 30), font, 0.7, color, thickness)
        
        # Velocidad
        cv2.putText(frame, f"SPD: {telemetry.get('ground_speed', 0):.1f}m/s", 
                    (10, 60), font, 0.7, color, thickness)
        
        # Batería
        battery = telemetry.get('battery_remaining', 0)
        battery_color = (0, 255, 0) if battery > 30 else (0, 165, 255) if battery > 15 else (0, 0, 255)
        cv2.putText(frame, f"BAT: {battery}%", 
                    (10, 90), font, 0.7, battery_color, thickness)
        
        # Modo de vuelo
        cv2.putText(frame, f"MODE: {telemetry.get('mode', 'UNKNOWN')}", 
                    (width - 200, 30), font, 0.7, color, thickness)
        
        # Estado armado
        armed_text = "ARMED" if telemetry.get('armed', False) else "DISARMED"
        armed_color = (0, 0, 255) if telemetry.get('armed', False) else (0, 255, 0)
        cv2.putText(frame, armed_text, 
                    (width - 200, 60), font, 0.7, armed_color, thickness)
        
        # Crosshair central
        center_x, center_y = width // 2, height // 2
        cv2.circle(frame, (center_x, center_y), 5, (0, 255, 0), 2)
        cv2.line(frame, (center_x - 20, center_y), (center_x + 20, center_y), (0, 255, 0), 2)
        cv2.line(frame, (center_x, center_y - 20), (center_x, center_y + 20), (0, 255, 0), 2)

# Instancia global de la cámara
camera = RealSenseCamera()

def generate_mjpeg_stream():
    """
    Genera stream MJPEG para transmisión HTTP
    """
    while True:
        frame = camera.get_frame()
        
        if frame is None:
            continue
        
        # Codificar frame a JPEG
        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        
        if not ret:
            continue
        
        # Convertir a bytes
        frame_bytes = buffer.tobytes()
        
        # Yield frame en formato MJPEG
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@router.get("/stream")
async def video_stream():
    """
    Endpoint de streaming de video MJPEG
    Retorna stream de video en tiempo real
    """
    return StreamingResponse(
        generate_mjpeg_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@router.get("/snapshot")
async def get_snapshot():
    """
    Obtiene una foto instantánea
    """
    frame = camera.get_frame()
    
    if frame is None:
        return Response(content="No hay frame disponible", status_code=503)
    
    # Codificar a JPEG
    ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
    
    if not ret:
        return Response(content="Error codificando imagen", status_code=500)
    
    return Response(content=buffer.tobytes(), media_type="image/jpeg")

@router.post("/start")
async def start_camera(width: int = 640, height: int = 480, fps: int = 30):
    """Inicia la cámara"""
    try:
        if not camera.running:
            camera.start(width, height, fps)
            return {"success": True, "message": "Cámara iniciada"}
        else:
            return {"success": False, "message": "Cámara ya está corriendo"}
    except Exception as e:
        logger.error(f"Error iniciando cámara: {e}")
        return {"success": False, "message": str(e)}

@router.post("/stop")
async def stop_camera():
    """Detiene la cámara"""
    try:
        if camera.running:
            camera.stop()
            return {"success": True, "message": "Cámara detenida"}
        else:
            return {"success": False, "message": "Cámara no está corriendo"}
    except Exception as e:
        logger.error(f"Error deteniendo cámara: {e}")
        return {"success": False, "message": str(e)}

@router.get("/status")
async def camera_status():
    """Estado de la cámara"""
    return {
        "running": camera.running,
        "has_frame": camera.current_frame is not None
    }
