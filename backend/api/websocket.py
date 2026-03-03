"""
WebSocket API para comunicación en tiempo real con clientes (Mobile/Frontend)
Envía telemetría y recibe comandos de control.

CORRECCIONES:
- Añadido comando REBOOT (faltaba en process_command)
- Eliminado deadlock: recv_match ya no adquiere el lock de conexión dentro de wait_ack
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Set
import asyncio
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._locks: dict = {}
        self.telemetry_task = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        self._locks[id(websocket)] = asyncio.Lock()
        logger.info(f"Cliente conectado. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        self._locks.pop(id(websocket), None)
        logger.info(f"Cliente desconectado. Total: {len(self.active_connections)}")

    async def send(self, websocket: WebSocket, message: dict):
        lock = self._locks.get(id(websocket))
        if lock is None:
            return
        async with lock:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error enviando a cliente: {e}")
                raise

    async def broadcast(self, message: dict):
        disconnected = set()
        for connection in list(self.active_connections):
            try:
                await self.send(connection, message)
            except Exception:
                disconnected.add(connection)
        for conn in disconnected:
            self.disconnect(conn)


manager = ConnectionManager()


async def telemetry_broadcaster(mav_controller):
    """Tarea en background que transmite telemetría a 10 Hz."""
    logger.info("Iniciando broadcaster de telemetría...")
    while True:
        try:
            if manager.active_connections:
                telemetry = await get_telemetry_data(mav_controller)
                await manager.broadcast({
                    "type": "telemetry",
                    "data": telemetry,
                    "timestamp": datetime.utcnow().isoformat(),
                })
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Error en telemetry_broadcaster: {e}")
            await asyncio.sleep(1)


async def get_telemetry_data(mav_controller) -> dict:
    """Extrae telemetría del controlador MAVLink."""
    try:
        telemetry = getattr(mav_controller, "telemetry", None)

        # Soporte simulador
        if telemetry is None and hasattr(mav_controller, "get_telemetry"):
            sim = mav_controller.get_telemetry()
            return {
                "armed":             mav_controller.is_armed(),
                "mode":              mav_controller.get_mode(),
                "altitude":          sim.get("altitude", 0),
                "latitude":          sim.get("gps", {}).get("lat", 0),
                "longitude":         sim.get("gps", {}).get("lon", 0),
                "roll":              sim.get("attitude", {}).get("roll", 0),
                "pitch":             sim.get("attitude", {}).get("pitch", 0),
                "yaw":               sim.get("attitude", {}).get("yaw", 0),
                "battery_voltage":   sim.get("battery", {}).get("voltage", 0),
                "battery_current":   sim.get("battery", {}).get("current", 0),
                "battery_remaining": sim.get("battery", {}).get("remaining", 0),
                "ground_speed":      sim.get("speed", 0),
                "vertical_speed":    sim.get("climb_rate", 0),
                "satellites":        sim.get("gps", {}).get("satellites", 0),
                "hdop":              sim.get("gps", {}).get("hdop", 0),
            }

        if telemetry is None:
            if not getattr(get_telemetry_data, "_error_shown", False):
                logger.error("Telemetría no disponible")
                get_telemetry_data._error_shown = True
            return {"error": "Telemetría no disponible"}

        attitude = telemetry.get_attitude() or {}
        gps      = telemetry.get_gps()      or {}
        battery  = telemetry.get_battery()  or {}
        velocity = telemetry.get_velocity() or {}

        return {
            "armed":             mav_controller.is_armed(),
            "mode":              mav_controller.get_mode(),
            "altitude":          gps.get("alt", 0),
            "latitude":          gps.get("lat", 0),
            "longitude":         gps.get("lon", 0),
            "roll":              attitude.get("roll", 0),
            "pitch":             attitude.get("pitch", 0),
            "yaw":               attitude.get("yaw", 0),
            "battery_voltage":   battery.get("voltage", 0),
            "battery_current":   battery.get("current", 0),
            "battery_remaining": battery.get("remaining", 0),
            "ground_speed":      velocity.get("ground_speed", 0),
            "vertical_speed":    velocity.get("vertical_speed", 0),
            "satellites":        gps.get("satellites", gps.get("satellites_visible", 0)),
            "hdop":              gps.get("hdop", 0),
        }

    except Exception as e:
        logger.error(f"Error obteniendo telemetría: {e}")
        return {"error": str(e)}


async def process_command(command: dict, mav_controller) -> dict:
    """
    Procesa comandos recibidos desde el cliente WebSocket.
    Todos los valores RC se esperan NORMALIZADOS (-1.0 a 1.0 / 0.0 a 1.0 para throttle).
    """
    cmd_type = command.get("type", "")
    params   = command.get("params", {})

    logger.info(f"Procesando comando: {cmd_type} | params: {params}")

    if not mav_controller:
        return {"success": False, "message": "MAVLink no conectado"}

    try:
        # ── Comandos de estado ────────────────────────────────────────────────
        if cmd_type == "ARM":
            success = await asyncio.to_thread(mav_controller.arm)
            return {"success": success, "message": "Drone armado" if success else "Error armando"}

        elif cmd_type == "DISARM":
            success = await asyncio.to_thread(mav_controller.disarm)
            return {"success": success, "message": "Drone desarmado" if success else "Error desarmando"}

        elif cmd_type == "TAKEOFF":
            altitude = params.get("altitude", 10)
            success  = await asyncio.to_thread(mav_controller.takeoff, altitude)
            return {"success": success, "message": f"Despegando a {altitude}m" if success else "Error despegando"}

        elif cmd_type == "LAND":
            success = await asyncio.to_thread(mav_controller.land)
            return {"success": success, "message": "Aterrizando" if success else "Error aterrizando"}

        elif cmd_type == "RTL":
            success = await asyncio.to_thread(mav_controller.return_to_launch)
            return {"success": success, "message": "Regresando a home" if success else "Error en RTL"}

        elif cmd_type == "SET_MODE":
            mode    = params.get("mode", "STABILIZE")
            success = await asyncio.to_thread(mav_controller.set_mode, mode)
            return {"success": success, "message": f"Modo cambiado a {mode}" if success else f"Error cambiando a {mode}"}

        # ── REBOOT — CORRECCIÓN: faltaba este handler ─────────────────────────
        elif cmd_type == "REBOOT":
            try:
                if hasattr(mav_controller, "cmd") and mav_controller.cmd:
                    await asyncio.to_thread(mav_controller.cmd.reboot_autopilot)
                    return {"success": True, "message": "Autopiloto reiniciando..."}
                else:
                    return {"success": False, "message": "REBOOT no disponible en modo simulador"}
            except Exception as e:
                return {"success": False, "message": f"Error en REBOOT: {e}"}

        # ── Control RC — valores normalizados ─────────────────────────────────
        elif cmd_type == "RC_CONTROL":
            rc = getattr(mav_controller, "rc", None)
            if not rc:
                return {"success": False, "message": "RC no disponible"}

            # Valores ya normalizados: throttle 0..1, yaw/pitch/roll -1..1
            rc.set_controls(
                throttle=params.get("throttle"),
                yaw=params.get("yaw"),
                pitch=params.get("pitch"),
                roll=params.get("roll"),
            )
            return {"success": True, "message": "RC actualizado", "values": rc.get_current_values()}

        elif cmd_type == "RC_RESET":
            rc = getattr(mav_controller, "rc", None)
            if rc:
                rc.reset_controls()
            return {"success": True, "message": "RC reseteado"}

        # ── Emergencia ────────────────────────────────────────────────────────
        elif cmd_type == "EMERGENCY":
            action = params.get("action", "").upper()
            if action == "STOP":
                success = await asyncio.to_thread(mav_controller.set_mode, "BRAKE")
                if not success:
                    success = await asyncio.to_thread(mav_controller.set_mode, "LOITER")
                rc = getattr(mav_controller, "rc", None)
                if rc:
                    rc.reset_controls()
                return {"success": success, "message": "STOP activado" if success else "Error en STOP"}
            elif action == "RTL":
                success = await asyncio.to_thread(mav_controller.return_to_launch)
                return {"success": success, "message": "RTL activado" if success else "Error en RTL"}
            elif action == "LAND":
                success = await asyncio.to_thread(mav_controller.land)
                return {"success": success, "message": "Aterrizaje de emergencia" if success else "Error aterrizando"}
            else:
                return {"success": False, "message": f"Acción desconocida: {action}"}

        # ── Navegación ────────────────────────────────────────────────────────
        elif cmd_type == "GOTO":
            lat     = params.get("latitude")
            lon     = params.get("longitude")
            alt     = params.get("altitude", 10)
            success = await asyncio.to_thread(mav_controller.goto, lat, lon, alt)
            return {"success": success, "message": f"Navegando a ({lat}, {lon})" if success else "Error navegando"}

        else:
            logger.warning(f"Comando desconocido recibido: {cmd_type}")
            return {"success": False, "message": f"Comando desconocido: {cmd_type}"}

    except Exception as e:
        logger.error(f"Error procesando {cmd_type}: {e}")
        return {"success": False, "message": f"Error: {e}"}


@router.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    """
    Endpoint WebSocket principal.
    - Envía telemetría cada 100ms (via telemetry_broadcaster)
    - Recibe comandos y responde con ACK
    """
    client_id = f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "unknown"
    logger.info(f"[WS] Nueva conexión desde {client_id}")
    await manager.connect(websocket)

    from backend.api import rest
    mav_controller = rest.mav

    if not mav_controller:
        logger.warning(f"[WS] {client_id} — MAVLink no disponible")

    try:
        while True:
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
            except json.JSONDecodeError as e:
                logger.warning(f"[WS] JSON inválido de {client_id}: {e}")
                continue

            cmd_type = message.get("type", "<sin tipo>")
            logger.info(f"[WS] {client_id} → {cmd_type}")

            result = await process_command(message, mav_controller)

            # RC_CONTROL y RC_RESET son continuos — no necesitan ACK
            # para evitar saturar el canal WebSocket a 10Hz
            if cmd_type not in ("RC_CONTROL", "RC_RESET"):
                await manager.send(websocket, {
                    "type":      "command_ack",
                    "command":   cmd_type,
                    "result":    result,
                    "timestamp": datetime.utcnow().isoformat(),
                })

    except WebSocketDisconnect as e:
        manager.disconnect(websocket)
        logger.info(f"[WS] {client_id} desconectado (code={e.code})")
    except Exception as e:
        logger.error(f"[WS] {client_id} ERROR: {type(e).__name__}: {e}", exc_info=True)
        manager.disconnect(websocket)


def start_telemetry_broadcast(mav_controller):
    loop = asyncio.get_event_loop()
    manager.telemetry_task = loop.create_task(telemetry_broadcaster(mav_controller))
    logger.info("Telemetry broadcaster iniciado")