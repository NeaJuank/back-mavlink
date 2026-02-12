"""
Endpoints REST para control del dron
API completa para control desde Mobile/Frontend
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["drone"])

# ============ Schemas ============

class ArmRequest(BaseModel):
    force: bool = False

class TakeoffRequest(BaseModel):
    altitude: float = 10.0  # metros

class ModeRequest(BaseModel):
    mode: str  # STABILIZE, GUIDED, RTL, etc.

class GotoRequest(BaseModel):
    latitude: float
    longitude: float
    altitude: float = 10.0

class RCControlRequest(BaseModel):
    """Control de joysticks - valores normalizados"""
    throttle: Optional[float] = None  # 0.0 - 1.0 (arriba/abajo)
    yaw: Optional[float] = None       # -1.0 - 1.0 (rotación)
    pitch: Optional[float] = None     # -1.0 - 1.0 (adelante/atrás)
    roll: Optional[float] = None      # -1.0 - 1.0 (izquierda/derecha)

class EmergencyRequest(BaseModel):
    action: str  # "STOP", "RTL", "LAND", "KILL"

# ============ Helper ============

def get_mav_controller():
    """Obtiene la instancia del controlador MAVLink"""
    from main import mav_controller
    if not mav_controller:
        raise HTTPException(status_code=503, detail="MAVLink no conectado")
    return mav_controller

# ============ Estado y Telemetría ============

@router.get("/status")
async def get_status():
    """Estado general del dron"""
    try:
        mav = get_mav_controller()
        
        return {
            "connected": mav.is_connected(),
            "armed": mav.is_armed(),
            "mode": mav.get_mode(),
            "system_status": mav.get_system_status(),
        }
    except Exception as e:
        logger.error(f"Error obteniendo status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/telemetry")
async def get_telemetry():
    """Telemetría completa del dron"""
    try:
        mav = get_mav_controller()
        
        attitude = mav.telemetry.get_attitude()
        gps = mav.telemetry.get_gps()
        battery = mav.telemetry.get_battery()
        velocity = mav.telemetry.get_velocity()
        
        return {
            "armed": mav.is_armed(),
            "mode": mav.get_mode(),
            "altitude": gps.get("alt", 0) if gps else 0,
            "latitude": gps.get("lat", 0) if gps else 0,
            "longitude": gps.get("lon", 0) if gps else 0,
            "roll": attitude.get("roll", 0) if attitude else 0,
            "pitch": attitude.get("pitch", 0) if attitude else 0,
            "yaw": attitude.get("yaw", 0) if attitude else 0,
            "battery_voltage": battery.get("voltage", 0) if battery else 0,
            "battery_remaining": battery.get("remaining", 0) if battery else 0,
            "ground_speed": velocity.get("ground_speed", 0) if velocity else 0,
            "satellites": gps.get("satellites_visible", 0) if gps else 0,
        }
    except Exception as e:
        logger.error(f"Error obteniendo telemetría: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============ Control Básico ============

@router.post("/arm")
async def arm_drone(request: ArmRequest):
    """Arma los motores"""
    try:
        mav = get_mav_controller()
        
        if mav.is_armed() and not request.force:
            return {"success": False, "message": "Dron ya está armado"}
        
        success = await mav.arm()
        
        return {
            "success": success,
            "message": "Dron armado" if success else "Error armando",
            "armed": mav.is_armed()
        }
    except Exception as e:
        logger.error(f"Error armando: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/disarm")
async def disarm_drone():
    """Desarma los motores"""
    try:
        mav = get_mav_controller()
        
        if not mav.is_armed():
            return {"success": False, "message": "Dron ya está desarmado"}
        
        success = await mav.disarm()
        
        return {
            "success": success,
            "message": "Dron desarmado" if success else "Error desarmando",
            "armed": mav.is_armed()
        }
    except Exception as e:
        logger.error(f"Error desarmando: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/takeoff")
async def takeoff(request: TakeoffRequest):
    """Despega a altitud específica"""
    try:
        mav = get_mav_controller()
        
        if not mav.is_armed():
            return {"success": False, "message": "Dron no está armado"}
        
        if request.altitude < 2 or request.altitude > 100:
            return {"success": False, "message": "Altitud debe estar entre 2 y 100 metros"}
        
        success = await mav.takeoff(request.altitude)
        
        return {
            "success": success,
            "message": f"Despegando a {request.altitude}m" if success else "Error despegando",
            "target_altitude": request.altitude
        }
    except Exception as e:
        logger.error(f"Error en despegue: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/land")
async def land():
    """Aterriza el dron"""
    try:
        mav = get_mav_controller()
        
        success = await mav.land()
        
        return {
            "success": success,
            "message": "Aterrizando" if success else "Error aterrizando"
        }
    except Exception as e:
        logger.error(f"Error aterizando: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rtl")
async def return_to_launch():
    """Return To Launch - Regresa a home"""
    try:
        mav = get_mav_controller()
        
        success = await mav.return_to_launch()
        
        return {
            "success": success,
            "message": "Regresando a home" if success else "Error en RTL"
        }
    except Exception as e:
        logger.error(f"Error en RTL: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============ Control de Joysticks (RC Override) ============

@router.post("/rc/control")
async def rc_control(request: RCControlRequest):
    """
    Control manual con joysticks
    Envía comandos RC_CHANNELS_OVERRIDE al dron
    """
    try:
        mav = get_mav_controller()
        
        # Verificar que el RC controller esté inicializado
        if not hasattr(mav, 'rc') or not mav.rc:
            return {"success": False, "message": "RC Controller no inicializado"}
        
        # Aplicar controles
        mav.rc.set_controls(
            throttle=request.throttle,
            yaw=request.yaw,
            pitch=request.pitch,
            roll=request.roll
        )
        
        return {
            "success": True,
            "message": "Controles RC actualizados",
            "values": mav.rc.get_current_values()
        }
    except Exception as e:
        logger.error(f"Error en RC control: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rc/reset")
async def rc_reset():
    """Resetea todos los controles RC a neutral"""
    try:
        mav = get_mav_controller()
        
        if hasattr(mav, 'rc') and mav.rc:
            mav.rc.reset_controls()
            return {"success": True, "message": "Controles RC reseteados"}
        else:
            return {"success": False, "message": "RC Controller no disponible"}
    except Exception as e:
        logger.error(f"Error reseteando RC: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/rc/values")
async def get_rc_values():
    """Obtiene los valores actuales de los controles RC"""
    try:
        mav = get_mav_controller()
        
        if hasattr(mav, 'rc') and mav.rc:
            return {
                "success": True,
                "values": mav.rc.get_current_values()
            }
        else:
            return {"success": False, "message": "RC Controller no disponible"}
    except Exception as e:
        logger.error(f"Error obteniendo valores RC: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============ Emergencias ============

@router.post("/emergency")
async def emergency_action(request: EmergencyRequest):
    """
    Acciones de emergencia
    - STOP: Detiene todos los motores (BRAKE)
    - RTL: Return to launch
    - LAND: Aterrizaje inmediato
    - KILL: Motor kill (PELIGROSO - solo en emergencia extrema)
    """
    try:
        mav = get_mav_controller()
        action = request.action.upper()
        
        if action == "STOP":
            # Modo BRAKE o LOITER
            success = await mav.set_mode("LOITER")
            # Resetear controles RC
            if hasattr(mav, 'rc') and mav.rc:
                mav.rc.reset_controls()
            message = "STOP: Dron en modo LOITER" if success else "Error en STOP"
            
        elif action == "RTL":
            success = await mav.return_to_launch()
            message = "RTL activado" if success else "Error activando RTL"
            
        elif action == "LAND":
            success = await mav.land()
            message = "Aterrizaje de emergencia activado" if success else "Error aterrizando"
            
        elif action == "KILL":
            # MOTOR KILL - solo en emergencia extrema
            logger.warning("⚠️ MOTOR KILL ACTIVADO")
            success = await mav.kill_motors()
            message = "MOTORES DETENIDOS" if success else "Error en MOTOR KILL"
            
        else:
            return {"success": False, "message": f"Acción desconocida: {action}"}
        
        return {
            "success": success,
            "action": action,
            "message": message
        }
        
    except Exception as e:
        logger.error(f"Error en emergencia {request.action}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============ Cambio de Modo ============

@router.post("/mode")
async def set_mode(request: ModeRequest):
    """Cambia el modo de vuelo"""
    try:
        mav = get_mav_controller()
        
        valid_modes = ["STABILIZE", "GUIDED", "RTL", "LOITER", "AUTO", "ALT_HOLD", "LAND", "BRAKE"]
        
        if request.mode.upper() not in valid_modes:
            return {
                "success": False,
                "message": f"Modo inválido. Modos válidos: {', '.join(valid_modes)}"
            }
        
        success = await mav.set_mode(request.mode.upper())
        
        return {
            "success": success,
            "message": f"Modo cambiado a {request.mode}" if success else "Error cambiando modo",
            "mode": mav.get_mode()
        }
    except Exception as e:
        logger.error(f"Error cambiando modo: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============ Navegación ============

@router.post("/goto")
async def goto_location(request: GotoRequest):
    """Navega a coordenadas GPS específicas"""
    try:
        mav = get_mav_controller()
        
        if not mav.is_armed():
            return {"success": False, "message": "Dron debe estar armado"}
        
        success = await mav.goto(request.latitude, request.longitude, request.altitude)
        
        return {
            "success": success,
            "message": f"Navegando a ({request.latitude}, {request.longitude})" if success else "Error navegando",
            "target": {
                "latitude": request.latitude,
                "longitude": request.longitude,
                "altitude": request.altitude
            }
        }
    except Exception as e:
        logger.error(f"Error navegando: {e}")
        raise HTTPException(status_code=500, detail=str(e))
