# backend/mavlink/connection.py
"""
Gestión de la conexión MAVLink con Pixhawk
"""

from pymavlink import mavutil
import logging
import threading
import time

logger = logging.getLogger(__name__)


class MAVLinkConnection:
    """Clase base para la conexión MAVLink"""
    
    def __init__(self, device, baud):
        """
        Inicializar conexión
        
        Args:
            device: Puerto serial (/dev/ttyUSB0, /dev/ttyAMA0, etc)
            baud: Baudrate (57600, 115200, etc)
        """
        self.device = device
        self.baud = baud
        self.master = None
        self.connected = False
        self._lock = threading.Lock()
        
        # Conectar automáticamente
        self.connect()
    
    def connect(self):
        """Establecer conexión con Pixhawk"""
        try:
            logger.info(f"🔌 Conectando a {self.device} @ {self.baud} baud...")
            
            with self._lock:
                self.master = mavutil.mavlink_connection(
                    self.device,
                    baud=self.baud,
                    source_system=255  # GCS (Ground Control Station)
                )
            
            logger.info("⏳ Esperando heartbeat...")
            self.master.wait_heartbeat(timeout=10)
            
            self.connected = True
            logger.info(f"✅ Conectado (System: {self.master.target_system}, Component: {self.master.target_component})")
            
            return True
            
        except Exception as e:
            self.connected = False
            logger.error(f"❌ Error de conexión: {e}")
            raise ConnectionError(f"No se pudo conectar a {self.device}: {e}")
    
    def disconnect(self):
        """Cerrar conexión"""
        self.connected = False
        
        if self.master:
            with self._lock:
                self.master.close()
                self.master = None
        
        logger.info("🔌 Desconectado")
    
    def is_connected(self):
        """Verificar si está conectado"""
        return self.connected and self.master is not None
    
    def send_command(self, command_type, *args, **kwargs):
        """
        Enviar comando genérico
        
        Args:
            command_type: Tipo de comando MAVLink
            *args: Argumentos del comando
            **kwargs: Argumentos con nombre
        """
        if not self.is_connected():
            raise ConnectionError("No hay conexión con Pixhawk")
        
        with self._lock:
            # Aquí puedes agregar lógica genérica de envío
            pass
    
    def recv_match(self, msg_type=None, blocking=True, timeout=None):
        """
        Recibir mensaje MAVLink
        
        Args:
            msg_type: Tipo de mensaje a esperar
            blocking: Si debe bloquear hasta recibir
            timeout: Tiempo máximo de espera
        
        Returns:
            Mensaje recibido o None
        """
        if not self.is_connected():
            return None
        
        with self._lock:
            return self.master.recv_match(
                type=msg_type,
                blocking=blocking,
                timeout=timeout
            )
    
    def wait_ack(self, command_id=None, timeout=3):
        """
        Esperar confirmación (ACK) de comando
        
        Args:
            command_id: ID del comando (opcional)
            timeout: Tiempo de espera
        
        Returns:
            True si fue aceptado, False si no
        """
        ack = self.recv_match('COMMAND_ACK', blocking=True, timeout=timeout)
        
        if not ack:
            logger.warning("⚠️ No se recibió ACK")
            return False
        
        if command_id and ack.command != command_id:
            return False
        
        if ack.result == mavutil.mavlink.MAV_RESULT_ACCEPTED:
            logger.debug("✅ Comando aceptado")
            return True
        else:
            logger.warning(f"⚠️ Comando rechazado (código: {ack.result})")
            return False