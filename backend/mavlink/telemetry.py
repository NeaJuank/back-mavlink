# backend/mavlink/telemetry.py
"""
Lectura y procesamiento de telemetría
"""

from pymavlink import mavutil
import logging
import threading
import time
import math

logger = logging.getLogger(__name__)


class DroneTelemetry:
    """Clase para leer y almacenar telemetría del dron"""
    
    def __init__(self, connection):
        """
        Args:
            connection: Instancia de MAVLinkConnection
        """
        self.conn = connection
        self.master = connection.master
        
        # Almacenamiento de datos
        self.data = {
            'altitude': 0.0,
            'speed': 0.0,
            'climb_rate': 0.0,
            'throttle': 0,
            'armed': False,
            'mode': 'UNKNOWN',
            'system_status': 0,
            'gps': {
                'lat': 0.0,
                'lon': 0.0,
                'alt': 0.0,
                'satellites': 0,
                'fix_type': 0,
                'hdop': 0.0
            },
            'battery': {
                'voltage': 0.0,
                'current': 0.0,
                'remaining': 0
            },
            'attitude': {
                'roll': 0.0,
                'pitch': 0.0,
                'yaw': 0.0
            },
            'home_position': {
                'lat': 0.0,
                'lon': 0.0,
                'alt': 0.0
            }
        }
        
        self._running = False
        self._thread = None
        
        # Iniciar thread de lectura
        self.start()
    
    def start(self):
        """Iniciar thread de lectura de telemetría"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()
        logger.info("📡 Thread de telemetría iniciado")
    
    def stop(self):
        """Detener thread"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        logger.info("📡 Thread de telemetría detenido")
    
    def _read_loop(self):
        """Loop principal de lectura"""
        while self._running:
            try:
                if not self.conn.is_connected():
                    time.sleep(0.5)
                    continue
                
                # Leer mensaje (no bloqueante)
                msg = self.master.recv_match(blocking=False)
                
                if msg:
                    self._process_message(msg)
                
                time.sleep(0.01)  # 100Hz
                
            except Exception as e:
                logger.error(f"Error en read_loop: {e}")
                time.sleep(0.1)
    
    def _process_message(self, msg):
        """Procesar mensaje MAVLink"""
        msg_type = msg.get_type()
        
        try:
            if msg_type == "VFR_HUD":
                self.data['altitude'] = round(msg.alt, 2)
                self.data['speed'] = round(msg.airspeed, 2)
                self.data['climb_rate'] = round(msg.climb, 2)
                self.data['throttle'] = msg.throttle
            
            elif msg_type == "GPS_RAW_INT":
                self.data['gps'] = {
                    'lat': round(msg.lat / 1e7, 7),
                    'lon': round(msg.lon / 1e7, 7),
                    'alt': round(msg.alt / 1000.0, 2),
                    'satellites': msg.satellites_visible,
                    'fix_type': msg.fix_type,
                    'hdop': round(msg.eph / 100.0, 2)
                }
            
            elif msg_type == "BATTERY_STATUS":
                self.data['battery'] = {
                    'voltage': round(msg.voltages[0] / 1000.0, 2),
                    'current': round(msg.current_battery / 100.0, 2),
                    'remaining': msg.battery_remaining
                }
            
            elif msg_type == "ATTITUDE":
                self.data['attitude'] = {
                    'roll': round(math.degrees(msg.roll), 2),
                    'pitch': round(math.degrees(msg.pitch), 2),
                    'yaw': round(math.degrees(msg.yaw), 2)
                }
            
            elif msg_type == "HEARTBEAT":
                self.data['armed'] = bool(
                    msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED
                )
                self.data['mode'] = mavutil.mode_string_v10(msg)
                self.data['system_status'] = msg.system_status
            
            elif msg_type == "HOME_POSITION":
                self.data['home_position'] = {
                    'lat': round(msg.latitude / 1e7, 7),
                    'lon': round(msg.longitude / 1e7, 7),
                    'alt': round(msg.altitude / 1000.0, 2)
                }
        
        except Exception as e:
            logger.error(f"Error procesando {msg_type}: {e}")
    
    # ============================================
    # GETTERS
    # ============================================
    
    def get_all(self):
        """Obtener toda la telemetría"""
        return {
            "connected": self.conn.is_connected(),
            **self.data
        }
    
    def get_status(self):
        """Estado básico"""
        return {
            "connected": self.conn.is_connected(),
            "armed": self.data['armed'],
            "mode": self.data['mode'],
            "system_status": self.data['system_status']
        }
    
    def get_battery(self):
        """Información de batería con tiempo estimado"""
        battery = self.data['battery']
        
        # Calcular tiempo restante
        current = battery['current']
        remaining_percent = battery['remaining']
        
        if current > 0:
            battery_capacity = 5000  # mAh (ajustar según tu batería)
            remaining_mah = (remaining_percent / 100) * battery_capacity
            time_remaining_min = (remaining_mah / (current * 1000)) * 60
        else:
            time_remaining_min = 0
        
        return {
            **battery,
            "time_remaining_minutes": round(time_remaining_min, 1)
        }
    
    def get_gps(self):
        """Información GPS"""
        return self.data['gps']
    
    def get_attitude(self):
        """Orientación"""
        return self.data['attitude']
    
    def get_position(self):
        """Posición completa"""
        return {
            "gps": self.data['gps'],
            "altitude": self.data['altitude'],
            "attitude": self.data['attitude']
        }
    
    # ============================================
    # PRE-FLIGHT CHECKS
    # ============================================
    
    def preflight_checks(self):
        """Verificaciones de seguridad"""
        checks = {
            "gps_fix": False,
            "battery_ok": False,
            "ekf_ok": False,
            "home_set": False,
            "sensors_ok": False
        }
        
        # GPS
        gps = self.data['gps']
        if gps['fix_type'] >= 3 and gps['satellites'] >= 6:
            checks["gps_fix"] = True
        
        # Batería
        battery = self.data['battery']
        if battery['remaining'] > 30:
            checks["battery_ok"] = True
        
        # EKF
        ekf = self.master.recv_match(type='EKF_STATUS_REPORT', blocking=True, timeout=2)
        if ekf and (ekf.flags & 0x01):
            checks["ekf_ok"] = True
        
        # Home
        if self.data['home_position']['lat'] != 0:
            checks["home_set"] = True
        
        # Sensores
        sys_status = self.master.recv_match(type='SYS_STATUS', blocking=True, timeout=2)
        if sys_status:
            sensors_ok = (sys_status.onboard_control_sensors_health &
                         sys_status.onboard_control_sensors_enabled) == \
                        sys_status.onboard_control_sensors_enabled
            checks["sensors_ok"] = sensors_ok
        
        return checks