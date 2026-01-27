# backend/api/rest.py
from fastapi import APIRouter, HTTPException
from mavlink_connection import MAVLinkConnection, MAVLINK_DEVICE, MAVLINK_BAUD
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
mav = MAVLinkConnection(MAVLINK_DEVICE, MAVLINK_BAUD)

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
        telemetry = mav.get_telemetry()
        return {
            "success": True,
            "data": telemetry
        }
    except Exception as e:
        logger.error(f"Error getting telemetry: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get telemetry: {str(e)}")

@router.get("/status")
def get_status():
    """Estado rápido del dron (conexión, armado, modo)"""
    try:
        status = mav.get_status()
        return {
            "success": True,
            "data": status
        }
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")

@router.get("/battery")
def get_battery():
    """Información detallada de la batería"""
    try:
        battery = mav.get_battery()
        return {
            "success": True,
            "data": battery
        }
    except Exception as e:
        logger.error(f"Error getting battery: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get battery: {str(e)}")

@router.get("/gps")
def get_gps():
    """Información GPS del dron"""
    try:
        gps = mav.get_gps()
        return {
            "success": True,
            "data": gps
        }
    except Exception as e:
        logger.error(f"Error getting GPS: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get GPS: {str(e)}")

@router.get("/preflight")
def preflight_checks():
    """Verificaciones pre-vuelo"""
    try:
        checks = mav.preflight_checks()
        all_ok = all(checks.values())
        
        return {
            "success": True,
            "ready_to_fly": all_ok,
            "checks": checks
        }
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
        mav.arm()
        return {"success": True, "message": "Armando motores..."}
    except Exception as e:
        logger.error(f"Error arming: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to arm: {str(e)}")

@router.post("/command/disarm")
def disarm():
    """Desarmar motores del dron"""
    try:
        mav.disarm()
        return {"success": True, "message": "Desarmando motores..."}
    except Exception as e:
        logger.error(f"Error disarming: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to disarm: {str(e)}")

@router.post("/command/takeoff")
def takeoff(request: TakeoffRequest):
    """Despegar a altitud especificada"""
    try:
        # Verificaciones pre-vuelo
        checks = mav.preflight_checks()
        if not all(checks.values()):
            failed = [k for k, v in checks.items() if not v]
            raise HTTPException(
                status_code=400, 
                detail=f"Preflight checks failed: {', '.join(failed)}"
            )
        
        mav.takeoff(request.altitude)
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
        mav.land()
        return {"success": True, "message": "Aterrizando..."}
    except Exception as e:
        logger.error(f"Error landing: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to land: {str(e)}")

@router.post("/command/rtl")
def rtl():
    """Return to Launch - Regresar al punto de despegue"""
    try:
        mav.rtl()
        return {"success": True, "message": "Regresando a casa..."}
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
        
        mav.set_mode(request.mode.upper())
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
        mav.goto_position(request.lat, request.lon, request.alt)
        return {
            "success": True, 
            "message": f"Yendo a ({request.lat}, {request.lon}) a {request.alt}m"
        }
    except Exception as e:
        logger.error(f"Error going to position: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to goto: {str(e)}")

@router.post("/command/emergency")
def emergency_stop():
    """Botón de emergencia - RTL inmediato"""
    try:
        logger.warning("🚨 EMERGENCY STOP ACTIVATED")
        mav.emergency_stop()
        return {
            "success": True, 
            "message": "🚨 EMERGENCIA - RTL activado"
        }
    except Exception as e:
        logger.error(f"Error in emergency stop: {e}")
        # Último recurso: desarmar
        try:
            mav.disarm()
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
        
        mav.upload_mission(request.waypoints)
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
        mav.start_mission()
        return {"success": True, "message": "Misión iniciada"}
    except Exception as e:
        logger.error(f"Error starting mission: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start mission: {str(e)}")

@router.post("/mission/pause")
def pause_mission():
    """Pausar misión actual"""
    try:
        mav.set_mode('LOITER')
        return {"success": True, "message": "Misión pausada"}
    except Exception as e:
        logger.error(f"Error pausing mission: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to pause mission: {str(e)}")

@router.post("/mission/resume")
def resume_mission():
    """Reanudar misión"""
    try:
        mav.set_mode('AUTO')
        return {"success": True, "message": "Misión reanudada"}
    except Exception as e:
        logger.error(f"Error resuming mission: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to resume mission: {str(e)}")

@router.post("/mission/clear")
def clear_mission():
    """Limpiar misión cargada"""
    try:
        mav.clear_mission()
        return {"success": True, "message": "Misión eliminada"}
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
        mav.set_mode('CIRCLE')
        # Configurar radio del círculo
        mav.set_param('CIRCLE_RADIUS', radius)
        return {
            "success": True, 
            "message": f"Modo círculo activado (radio: {radius}m)"
        }
    except Exception as e:
        logger.error(f"Error in circle mode: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to activate circle mode: {str(e)}")

@router.get("/logs")
def get_logs():
    """Obtener logs de vuelo"""
    try:
        logs = mav.get_flight_logs()
        return {"success": True, "logs": logs}
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get logs: {str(e)}")

@router.get("/parameters/{param_name}")
def get_parameter(param_name: str):
    """Obtener valor de un parámetro del dron"""
    try:
        value = mav.get_param(param_name)
        return {
            "success": True, 
            "parameter": param_name,
            "value": value
        }
    except Exception as e:
        logger.error(f"Error getting parameter: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get parameter: {str(e)}")

@router.post("/parameters/{param_name}")
def set_parameter(param_name: str, value: float):
    """Establecer valor de un parámetro del dron"""
    try:
        mav.set_param(param_name, value)
        return {
            "success": True, 
            "message": f"Parámetro {param_name} = {value}"
        }
    except Exception as e:
        logger.error(f"Error setting parameter: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to set parameter: {str(e)}")