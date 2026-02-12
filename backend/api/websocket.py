"""
WebSocket API para comunicación en tiempo real con clientes (Mobile/Frontend)
Envía telemetría y recibe comandos de control
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, List, Set
import asyncio
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter()

# Gestor de conexiones activas
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.telemetry_task = None
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"Cliente conectado. Total conexiones: {len(self.active_connections)}")
        
    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info(f"Cliente desconectado. Total conexiones: {len(self.active_connections)}")
        
    async def broadcast(self, message: dict):
        """Envía mensaje a todos los clientes conectados"""
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error enviando a cliente: {e}")
                disconnected.add(connection)
        
        # Limpiar conexiones muertas
        self.active_connections -= disconnected

manager = ConnectionManager()

async def telemetry_broadcaster(mav_controller):
    """
    Tarea en background que lee telemetría del dron y la transmite
    a todos los clientes WebSocket conectados
    """
    logger.info("Iniciando broadcaster de telemetría...")
    
    while True:
        try:
            if len(manager.active_connections) > 0:
                # Obtener telemetría del controlador MAVLink
                telemetry = await get_telemetry_data(mav_controller)
                
                # Broadcast a todos los clientes
                await manager.broadcast({
                    "type": "telemetry",
                    "data": telemetry,
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            # Frecuencia de actualización: 10Hz
            await asyncio.sleep(0.1)
            
        except Exception as e:
            logger.error(f"Error en telemetry_broadcaster: {e}")
            await asyncio.sleep(1)

async def get_telemetry_data(mav_controller) -> dict:
    """
    Extrae telemetría del controlador MAVLink
    """
    try:
        # Obtener datos de los diferentes módulos de telemetría
        attitude = mav_controller.telemetry.get_attitude()
        gps = mav_controller.telemetry.get_gps()
        battery = mav_controller.telemetry.get_battery()
        velocity = mav_controller.telemetry.get_velocity()
        
        return {
            "armed": mav_controller.is_armed(),
            "mode": mav_controller.get_mode(),
            "altitude": gps.get("alt", 0) if gps else 0,
            "latitude": gps.get("lat", 0) if gps else 0,
            "longitude": gps.get("lon", 0) if gps else 0,
            "roll": attitude.get("roll", 0) if attitude else 0,
            "pitch": attitude.get("pitch", 0) if attitude else 0,
            "yaw": attitude.get("yaw", 0) if attitude else 0,
            "battery_voltage": battery.get("voltage", 0) if battery else 0,
            "battery_current": battery.get("current", 0) if battery else 0,
            "battery_remaining": battery.get("remaining", 0) if battery else 0,
            "ground_speed": velocity.get("ground_speed", 0) if velocity else 0,
            "vertical_speed": velocity.get("vertical_speed", 0) if velocity else 0,
            "satellites": gps.get("satellites_visible", 0) if gps else 0,
            "hdop": gps.get("hdop", 0) if gps else 0,
        }
    except Exception as e:
        logger.error(f"Error obteniendo telemetría: {e}")
        return {}

async def process_command(command: dict, mav_controller):
    """
    Procesa comandos recibidos desde el cliente WebSocket
    """
    cmd_type = command.get("type")
    params = command.get("params", {})
    
    logger.info(f"Procesando comando: {cmd_type} con params: {params}")
    
    try:
        if cmd_type == "ARM":
            success = await mav_controller.arm()
            return {"success": success, "message": "Drone armado" if success else "Error armando"}
            
        elif cmd_type == "DISARM":
            success = await mav_controller.disarm()
            return {"success": success, "message": "Drone desarmado" if success else "Error desarmando"}
            
        elif cmd_type == "TAKEOFF":
            altitude = params.get("altitude", 10)
            success = await mav_controller.takeoff(altitude)
            return {"success": success, "message": f"Despegando a {altitude}m" if success else "Error despegando"}
            
        elif cmd_type == "LAND":
            success = await mav_controller.land()
            return {"success": success, "message": "Aterrizando" if success else "Error aterrizando"}
            
        elif cmd_type == "RTL":
            success = await mav_controller.return_to_launch()
            return {"success": success, "message": "Regresando a home" if success else "Error en RTL"}
            
        elif cmd_type == "SET_MODE":
            mode = params.get("mode", "STABILIZE")
            success = await mav_controller.set_mode(mode)
            return {"success": success, "message": f"Modo cambiado a {mode}" if success else "Error cambiando modo"}
            
        elif cmd_type == "THROTTLE":
            value = params.get("value", 0)
            mav_controller.rc.set_throttle(value)
            return {"success": True, "message": f"Throttle: {value}"}
            
        elif cmd_type == "YAW":
            value = params.get("value", 0)
            mav_controller.rc.set_yaw(value)
            return {"success": True, "message": f"Yaw: {value}"}
            
        elif cmd_type == "PITCH":
            value = params.get("value", 0)
            mav_controller.rc.set_pitch(value)
            return {"success": True, "message": f"Pitch: {value}"}
            
        elif cmd_type == "ROLL":
            value = params.get("value", 0)
            mav_controller.rc.set_roll(value)
            return {"success": True, "message": f"Roll: {value}"}
            
        elif cmd_type == "GOTO":
            lat = params.get("latitude")
            lon = params.get("longitude")
            alt = params.get("altitude", 10)
            success = await mav_controller.goto(lat, lon, alt)
            return {"success": success, "message": f"Navegando a ({lat}, {lon})" if success else "Error navegando"}
            
        else:
            return {"success": False, "message": f"Comando desconocido: {cmd_type}"}
            
    except Exception as e:
        logger.error(f"Error procesando comando {cmd_type}: {e}")
        return {"success": False, "message": f"Error: {str(e)}"}

@router.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    """
    Endpoint WebSocket principal
    - Envía telemetría cada 100ms
    - Recibe comandos de control
    """
    await manager.connect(websocket)
    
    # Obtener el controlador MAVLink desde la app
    from main import mav_controller
    
    try:
        while True:
            # Esperar mensaje del cliente
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Procesar comando
            result = await process_command(message, mav_controller)
            
            # Enviar ACK al cliente
            await websocket.send_json({
                "type": "command_ack",
                "command": message.get("type"),
                "result": result,
                "timestamp": datetime.utcnow().isoformat()
            })
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Cliente desconectado")
    except Exception as e:
        logger.error(f"Error en WebSocket: {e}")
        manager.disconnect(websocket)

def start_telemetry_broadcast(mav_controller):
    """
    Inicia la tarea de broadcast de telemetría
    Llamar desde main.py al iniciar la aplicación
    """
    loop = asyncio.get_event_loop()
    manager.telemetry_task = loop.create_task(telemetry_broadcaster(mav_controller))
    logger.info("Telemetry broadcaster iniciado")
