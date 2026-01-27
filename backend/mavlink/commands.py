# backend/mavlink/commands.py
"""
Comandos de control del dron
"""

from pymavlink import mavutil
import logging
import time

logger = logging.getLogger(__name__)


class DroneCommands:
    """Clase para enviar comandos al dron"""
    
    def __init__(self, connection):
        """
        Args:
            connection: Instancia de MAVLinkConnection
        """
        self.conn = connection
        self.master = connection.master
    
    # ============================================
    # COMANDOS BÁSICOS
    # ============================================
    
    def arm(self):
        """Armar motores"""
        logger.info("🔴 ARM - Armando motores...")
        
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0,  # confirmation
            1,  # 1 = ARM
            0, 0, 0, 0, 0, 0
        )
        
        if self.conn.wait_ack(mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM):
            logger.info("✅ Motores armados")
            return True
        else:
            logger.error("❌ No se pudo armar")
            return False
    
    def disarm(self, force=False):
        """
        Desarmar motores
        
        Args:
            force: Forzar desarme (incluso en vuelo, PELIGROSO)
        """
        logger.info("🟢 DISARM - Desarmando motores...")
        
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0,
            0,  # 0 = DISARM
            21196 if force else 0,  # Magic number para forzar
            0, 0, 0, 0, 0
        )
        
        if self.conn.wait_ack(mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM):
            logger.info("✅ Motores desarmados")
            return True
        else:
            logger.error("❌ No se pudo desarmar")
            return False
    
    def set_mode(self, mode_name):
        """
        Cambiar modo de vuelo
        
        Args:
            mode_name: Nombre del modo (STABILIZE, LOITER, GUIDED, RTL, etc)
        """
        logger.info(f"🔄 Cambiando a modo: {mode_name}")
        
        # Verificar que el modo existe
        if mode_name not in self.master.mode_mapping():
            valid_modes = list(self.master.mode_mapping().keys())
            raise ValueError(f"Modo inválido. Modos válidos: {valid_modes}")
        
        mode_id = self.master.mode_mapping()[mode_name]
        
        self.master.set_mode(mode_id)
        
        # Verificar cambio
        time.sleep(0.5)
        # Aquí podrías verificar con telemetría
        
        logger.info(f"✅ Comando de modo enviado: {mode_name}")
        return True
    
    def takeoff(self, altitude):
        """
        Despegar a altitud especificada
        
        Args:
            altitude: Altitud objetivo en metros
        """
        logger.info(f"🚁 TAKEOFF - Despegando a {altitude}m")
        
        # Paso 1: Modo GUIDED
        self.set_mode('GUIDED')
        time.sleep(1)
        
        # Paso 2: Armar
        if not self.arm():
            raise Exception("No se pudo armar el dron")
        time.sleep(2)
        
        # Paso 3: Comando takeoff
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
            0,
            0, 0, 0, 0,  # Params no usados
            0, 0,        # Lat/Lon (0 = posición actual)
            altitude
        )
        
        if self.conn.wait_ack(mavutil.mavlink.MAV_CMD_NAV_TAKEOFF):
            logger.info(f"✅ Despegando a {altitude}m")
            return True
        else:
            logger.error("❌ Comando de despegue rechazado")
            return False
    
    def land(self):
        """Aterrizar en posición actual"""
        logger.info("🛬 LAND - Aterrizando...")
        
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_CMD_NAV_LAND,
            0,
            0, 0, 0, 0,
            0, 0, 0  # Lat/Lon/Alt (0 = actual)
        )
        
        if self.conn.wait_ack(mavutil.mavlink.MAV_CMD_NAV_LAND):
            logger.info("✅ Aterrizando")
            return True
        else:
            logger.error("❌ Comando de aterrizaje rechazado")
            return False
    
    def rtl(self):
        """Return to Launch"""
        logger.info("🏠 RTL - Return to Launch")
        return self.set_mode('RTL')
    
    def loiter(self):
        """Modo Loiter (mantener posición)"""
        logger.info("⭕ LOITER - Mantener posición")
        return self.set_mode('LOITER')
    
    # ============================================
    # NAVEGACIÓN
    # ============================================
    
    def goto_position(self, lat, lon, alt):
        """
        Ir a coordenadas GPS
        
        Args:
            lat: Latitud (grados)
            lon: Longitud (grados)
            alt: Altitud relativa (metros)
        """
        logger.info(f"📍 GOTO - Yendo a ({lat:.6f}, {lon:.6f}) @ {alt}m")
        
        # Asegurar modo GUIDED
        current_mode = self.get_current_mode()
        if current_mode != 'GUIDED':
            self.set_mode('GUIDED')
            time.sleep(1)
        
        # Enviar posición objetivo
        self.master.mav.set_position_target_global_int_send(
            0,  # timestamp
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
            int(0b110111111000),  # type_mask (solo posición)
            int(lat * 1e7),
            int(lon * 1e7),
            alt,
            0, 0, 0,  # vx, vy, vz
            0, 0, 0,  # afx, afy, afz
            0, 0      # yaw, yaw_rate
        )
        
        logger.info("✅ Waypoint enviado")
        return True
    
    def set_velocity(self, vx, vy, vz, yaw_rate=0):
        """
        Establecer velocidad del dron
        
        Args:
            vx: Velocidad Norte (m/s)
            vy: Velocidad Este (m/s)
            vz: Velocidad Down (m/s, negativo = subir)
            yaw_rate: Velocidad de rotación (rad/s)
        """
        self.master.mav.set_position_target_local_ned_send(
            0,
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_FRAME_LOCAL_NED,
            int(0b0000111111000111),  # type_mask (solo velocidad)
            0, 0, 0,  # posición
            vx, vy, vz,  # velocidad
            0, 0, 0,  # aceleración
            0, yaw_rate
        )
    
    # ============================================
    # EMERGENCIA
    # ============================================
    
    def emergency_stop(self):
        """Parada de emergencia"""
        logger.warning("🚨 EMERGENCY STOP")
        
        try:
            # Intentar RTL primero
            self.rtl()
            time.sleep(1)
            
            # Verificar si funcionó
            current_mode = self.get_current_mode()
            if current_mode == 'RTL':
                logger.info("✅ RTL activado")
                return True
            
            # Si RTL falló, intentar LAND
            logger.warning("RTL falló, intentando LAND...")
            self.land()
            time.sleep(1)
            
            current_mode = self.get_current_mode()
            if current_mode == 'LAND':
                logger.info("✅ LAND activado")
                return True
            
            # Último recurso: desarmar (PELIGROSO en vuelo)
            logger.critical("🚨 LAND falló, DESARMANDO (puede causar caída)")
            return self.disarm(force=True)
            
        except Exception as e:
            logger.critical(f"Error en emergency stop: {e}")
            return False
    
    # ============================================
    # UTILIDADES
    # ============================================
    
    def get_current_mode(self):
        """Obtener modo actual del dron"""
        msg = self.conn.recv_match('HEARTBEAT', blocking=True, timeout=2)
        if msg:
            return mavutil.mode_string_v10(msg)
        return None
    
    def reboot_autopilot(self):
        """Reiniciar autopiloto"""
        logger.warning("🔄 Reiniciando autopiloto...")
        
        self.master.mav.command_long_send(
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_CMD_PREFLIGHT_REBOOT_SHUTDOWN,
            0,
            1, 0, 0, 0, 0, 0, 0  # 1 = reboot autopilot
        )
        
        self.conn.disconnect()