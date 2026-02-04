# backend/api/rest.py
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from backend.config import MAVLINK_DEVICE, MAVLINK_BAUD
from backend.mavlink.controller import MAVController
from pydantic import BaseModel
import logging
import asyncio

logger = logging.getLogger(__name__)

router = APIRouter()
# Controlador alto nivel que usa connection/commands/telemetry
# Se inicializa en el evento de arranque para evitar abrir puertos en tiempo de import
mav = None
_monitor_thread = None
_mlock = __import__('threading').Lock()
_current_device = None


def init_mav(device, baud):
    """Inicializar el controlador MAV. Llamar desde `app.on_event('startup')`.

    Si falla con un dispositivo físico, intentará hacer fallback a 'SIM' para
    mantener la API disponible en modo simulación.
    """
    global mav, _current_device
    logger.info(f"Inicializando MAVController en device={device} baud={baud}")
    try:
        m = MAVController(device, baud)
        with _mlock:
            mav = m
            _current_device = device
        logger.info("MAVController inicializado")
        return True
    except Exception as e:
        logger.error(f"No se pudo inicializar MAVController en {device}: {e}")
        # Si el intento fue con un device físico, intentar fallback a simulador
        if device and device.upper() != 'SIM':
            logger.info("Intentando fallback a 'SIM'...")
            try:
                m = MAVController('SIM', baud)
                with _mlock:
                    mav = m
                    _current_device = 'SIM'
                logger.info("MAVController (SIM) inicializado")
                return True
            except Exception as e2:
                logger.error(f"No se pudo inicializar el simulador: {e2}")
        with _mlock:
            mav = None
            _current_device = None
        return False


def _monitor_loop(baud, interval=5):
    """Loop de background que detecta cambios en el dispositivo e intenta reconectar."""
    import time
    from backend.config import detect_mavlink_device

    logger.info("MAV monitor thread started")
    while True:
        try:
            dev = detect_mavlink_device()
            with _mlock:
                cur = _current_device
            if dev != cur:
                logger.info(f"Device change detected: {cur} -> {dev}")
                success = init_mav(dev, baud)
                if success:
                    logger.info(f"Switched MAV controller to {dev}")
            # If current device is None, ensure we have at least SIM
            with _mlock:
                if _current_device is None:
                    init_mav('SIM', baud)
        except Exception as e:
            logger.error(f"Error in MAV monitor loop: {e}")
        time.sleep(interval)


def start_monitoring(baud, interval=5):
    """Inicia el hilo monitor si no está ya corriendo."""
    global _monitor_thread
    import threading
    if _monitor_thread and getattr(_monitor_thread, 'is_alive', lambda: False)():
        return
    _monitor_thread = threading.Thread(target=_monitor_loop, args=(baud, interval), daemon=True)
    _monitor_thread.start()


def get_current_device():
    with _mlock:
        return _current_device


@router.get("/device")
def get_device():
    """Información sobre el dispositivo MAV actual."""
    device = get_current_device()
    simulated = bool(device and isinstance(device, str) and device.upper() == 'SIM')

    # Determinar si estamos conectados (siempre True para SIM)
    connected = False
    if mav is None:
        connected = False
    else:
        if simulated:
            connected = True
        else:
            try:
                conn = getattr(mav, 'conn', None)
                connected = bool(conn and getattr(conn, 'is_connected', lambda: False)())
            except Exception:
                connected = False

    return {
        "success": True,
        "data": {
            "device": device,
            "connected": connected,
            "simulated": simulated
        }
    }


def get_mav():
    """Obtener el controlador inicializado o lanzar HTTP 503 si no está disponible."""
    if mav is None:
        raise HTTPException(status_code=503, detail="MAV controller not available")
    return mav


@router.websocket('/ws/telemetry')
async def telemetry_ws(websocket: WebSocket):
    """WebSocket que emite telemetría cada segundo."""
    await websocket.accept()
    try:
        while True:
            try:
                data = get_mav().get_telemetry()
            except Exception as e:
                data = {"error": str(e)}

            await websocket.send_json(data)
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        return

# ============================================
# MODELOS DE DATOS (Request Bodies)
# ============================================

class TakeoffRequest(BaseModel):
    altitude: float = 5.0  # metros

class LandRequest(BaseModel):
    pass  # No necesita parámetros

class ModeRequest(BaseModel):
    mode: str  # STABILIZE, GUIDED, LOITER, RTL, LAND, etc

class GotoRequest(BaseModel):
    lat: float
    lon: float
    alt: float = 10.0

class MissionRequest(BaseModel):
    waypoints: list  # [{"lat": 4.123, "lon": -74.456, "alt": 10}, ...]

# ============================================
# ENDPOINTS DE TELEMETRÍA (GET)
# ============================================

@router.get("/telemetry")
def get_telemetry():
    """Obtener toda la telemetría del dron"""
    try:
        telemetry = get_mav().get_telemetry()
        return {
            "success": True,
            "data": telemetry
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting telemetry: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get telemetry: {str(e)}")

@router.get("/status")
def get_status():
    """Estado rápido del dron (conexión, armado, modo)"""
    try:
        status = get_mav().get_status()
        return {
            "success": True,
            "data": status
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")

@router.get("/battery")
def get_battery():
    """Información detallada de la batería"""
    try:
        battery = get_mav().get_battery()
        return {
            "success": True,
            "data": battery
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting battery: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get battery: {str(e)}")

@router.get("/gps")
def get_gps():
    """Información GPS del dron"""
    try:
        gps = get_mav().get_gps()
        return {
            "success": True,
            "data": gps
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting GPS: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get GPS: {str(e)}")

@router.get("/preflight")
def preflight_checks():
    """Verificaciones pre-vuelo"""
    try:
        checks = get_mav().preflight_checks()
        all_ok = all(checks.values())
        
        return {
            "success": True,
            "ready_to_fly": all_ok,
            "checks": checks
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in preflight checks: {e}")
        raise HTTPException(status_code=500, detail=f"Preflight checks failed: {str(e)}")

# ============================================
# ENDPOINTS DE COMANDOS (POST)
# ============================================

@router.post("/command/arm")
def arm():
    """Armar motores del dron"""
    try:
        get_mav().arm()
        return {"success": True, "message": "Armando motores..."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error arming: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to arm: {str(e)}")

@router.post("/command/disarm")
def disarm():
    """Desarmar motores del dron"""
    try:
        get_mav().disarm()
        return {"success": True, "message": "Desarmando motores..."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disarming: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to disarm: {str(e)}")

@router.post("/command/takeoff")
def takeoff(request: TakeoffRequest):
    """Despegar a altitud especificada"""
    try:
        # Verificaciones pre-vuelo
        checks = get_mav().preflight_checks()
        if not all(checks.values()):
            failed = [k for k, v in checks.items() if not v]
            raise HTTPException(
                status_code=400, 
                detail=f"Preflight checks failed: {', '.join(failed)}"
            )
        
        get_mav().takeoff(request.altitude)
        return {
            "success": True, 
            "message": f"Despegando a {request.altitude}m"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error taking off: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to takeoff: {str(e)}")

@router.post("/command/land")
def land():
    """Aterrizar el dron"""
    try:
        get_mav().land()
        return {"success": True, "message": "Aterrizando..."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error landing: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to land: {str(e)}")

@router.post("/command/rtl")
def rtl():
    """Return to Launch - Regresar al punto de despegue"""
    try:
        get_mav().rtl()
        return {"success": True, "message": "Regresando a casa..."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error RTL: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to RTL: {str(e)}")

@router.post("/command/mode")
def change_mode(request: ModeRequest):
    """Cambiar modo de vuelo"""
    try:
        valid_modes = ['STABILIZE', 'LOITER', 'GUIDED', 'RTL', 'LAND', 'AUTO']
        
        if request.mode.upper() not in valid_modes:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid mode. Valid modes: {', '.join(valid_modes)}"
            )
        
        get_mav().set_mode(request.mode.upper())
        return {
            "success": True, 
            "message": f"Modo cambiado a {request.mode}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing mode: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to change mode: {str(e)}")

@router.post("/command/goto")
def goto(request: GotoRequest):
    """Ir a coordenadas GPS específicas"""
    try:
        get_mav().goto_position(request.lat, request.lon, request.alt)
        return {
            "success": True, 
            "message": f"Yendo a ({request.lat}, {request.lon}) a {request.alt}m"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error going to position: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to goto: {str(e)}")

@router.post("/command/emergency")
def emergency_stop():
    """Botón de emergencia - RTL inmediato"""
    try:
        logger.warning("🚨 EMERGENCY STOP ACTIVATED")
        get_mav().emergency_stop()
        return {
            "success": True, 
            "message": "🚨 EMERGENCIA - RTL activado"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in emergency stop: {e}")
        # Último recurso: desarmar
        try:
            get_mav().disarm()
            return {
                "success": False, 
                "message": "RTL falló, motores desarmados",
                "error": str(e)
            }
        except:
            raise HTTPException(status_code=500, detail=f"Emergency stop failed: {str(e)}")

# ============================================
# ENDPOINTS DE MISIONES (Waypoints)
# ============================================

@router.post("/mission/upload")
def upload_mission(request: MissionRequest):
    """Subir misión de waypoints al dron"""
    try:
        if not request.waypoints:
            raise HTTPException(status_code=400, detail="No waypoints provided")
        
        get_mav().upload_mission(request.waypoints)
        return {
            "success": True, 
            "message": f"Misión cargada con {len(request.waypoints)} waypoints"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading mission: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload mission: {str(e)}")

@router.post("/mission/start")
def start_mission():
    """Iniciar misión cargada (cambiar a modo AUTO)"""
    try:
        get_mav().start_mission()
        return {"success": True, "message": "Misión iniciada"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting mission: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start mission: {str(e)}")

@router.post("/mission/pause")
def pause_mission():
    """Pausar misión actual"""
    try:
        get_mav().set_mode('LOITER')
        return {"success": True, "message": "Misión pausada"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pausing mission: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to pause mission: {str(e)}")

@router.post("/mission/resume")
def resume_mission():
    """Reanudar misión"""
    try:
        get_mav().set_mode('AUTO')
        return {"success": True, "message": "Misión reanudada"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resuming mission: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to resume mission: {str(e)}")

@router.post("/mission/clear")
def clear_mission():
    """Limpiar misión cargada"""
    try:
        get_mav().clear_mission()
        return {"success": True, "message": "Misión eliminada"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing mission: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear mission: {str(e)}")

# ============================================
# ENDPOINTS AVANZADOS
# ============================================

@router.post("/command/circle")
def circle_mode(radius: float = 10.0):
    """Modo círculo - Dar vueltas en círculo"""
    try:
        get_mav().set_mode('CIRCLE')
        # Configurar radio del círculo
        get_mav().set_param('CIRCLE_RADIUS', radius)
        return {
            "success": True, 
            "message": f"Modo círculo activado (radio: {radius}m)"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in circle mode: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to activate circle mode: {str(e)}")

@router.get("/logs")
def get_logs():
    """Obtener logs de vuelo"""
    try:
        logs = get_mav().get_flight_logs()
        return {"success": True, "logs": logs}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get logs: {str(e)}")

@router.get("/device")
def get_device():
    """Información del dispositivo MAV actual y estado de conexión."""
    try:
        dev = get_current_device()
        result = {"device": dev}
        try:
            m = get_mav()
            simulated = getattr(m, '_sim', None) is not None
            result["simulated"] = simulated
            if simulated:
                result["connected"] = True
            else:
                conn = getattr(m, 'conn', None)
                result["connected"] = conn.is_connected() if conn else False
        except HTTPException:
            # controller not initialized
            result["simulated"] = (dev == 'SIM')
            result["connected"] = False
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Error getting device info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/parameters/{param_name}")
def get_parameter(param_name: str):
    """Obtener valor de un parámetro del dron"""
    try:
        value = get_mav().get_param(param_name)
        return {
            "success": True, 
            "parameter": param_name,
            "value": value
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting parameter: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get parameter: {str(e)}")

@router.post("/parameters/{param_name}")
def set_parameter(param_name: str, value: float):
    """Establecer valor de un parámetro del dron"""
    try:
        get_mav().set_param(param_name, value)
        return {
            "success": True, 
            "message": f"Parámetro {param_name} = {value}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting parameter: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to set parameter: {str(e)}")