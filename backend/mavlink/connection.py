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
        self._auto_reconnect_thread = None
        self._auto_reconnect_stop = None
        
        # Conectar automáticamente
        self.connect()
    
    def connect(self, max_retries: int = 5, backoff_factor: float = 1.0):
        """Establecer conexión con Pixhawk con reintentos exponenciales.

        Args:
            max_retries: número máximo de intentos (incluye el primer intento).
            backoff_factor: factor base (segundos) para backoff exponencial.

        Lanza ConnectionError si no puede conectar después de los reintentos.
        """
        attempt = 0
        last_exc = None

        while attempt < max_retries:
            try:
                logger.info(f"🔌 Conectando a {self.device} @ {self.baud} baud... (intento {attempt+1}/{max_retries})")
                
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
                last_exc = e
                self.connected = False
                logger.warning(f"❌ Error de conexión en intento {attempt+1}: {e}")
                
                attempt += 1
                if attempt >= max_retries:
                    break
                
                # Exponential backoff antes del siguiente intento
                sleep_time = backoff_factor * (2 ** (attempt - 1))
                logger.info(f"⏱ Reintentando en {sleep_time} segundos...")
                time.sleep(sleep_time)
        
        logger.error(f"No se pudo conectar a {self.device} después de {max_retries} intentos: {last_exc}")
        raise ConnectionError(f"No se pudo conectar a {self.device}: {last_exc}")
    
    def disconnect(self):
        """Cerrar conexión"""
        self.connected = False
        
        if self.master:
            with self._lock:
                self.master.close()
                self.master = None
        
        logger.info("🔌 Desconectado")
    
    def reconnect(self, max_retries: int = 5, backoff_factor: float = 1.0):
        """Forzar re-conexión: desconecta (si procede) y vuelve a intentar conectar."""
        try:
            self.disconnect()
        except Exception:
            pass
        return self.connect(max_retries=max_retries, backoff_factor=backoff_factor)
    
    def start_auto_reconnect(self, interval: float = 5.0):
        """Inicia un hilo que intentará reconectar periódicamente si la conexión se pierde.

        El hilo es silencioso y no bloqueante; para detenerlo llamar a `stop_auto_reconnect()`.
        """
        if self._auto_reconnect_thread and self._auto_reconnect_thread.is_alive():
            return

        self._auto_reconnect_stop = threading.Event()

        def _loop():
            logger.info("🔁 Auto-reconnect thread iniciado")
            while not self._auto_reconnect_stop.is_set():
                if not self.is_connected():
                    try:
                        # Intento rápido de reconexión (un intento por ciclo)
                        self.connect(max_retries=1)
                    except Exception:
                        logger.debug("Auto-reconnect: intento fallido")
                # Esperar antes del siguiente chequeo
                self._auto_reconnect_stop.wait(interval)
            logger.info("🔁 Auto-reconnect thread detenido")

        self._auto_reconnect_thread = threading.Thread(target=_loop, daemon=True)
        self._auto_reconnect_thread.start()

    def stop_auto_reconnect(self):
        """Detiene el hilo de reconexión automática (si existe)."""
        if self._auto_reconnect_stop:
            self._auto_reconnect_stop.set()
        if self._auto_reconnect_thread:
            self._auto_reconnect_thread.join(timeout=2)
            self._auto_reconnect_thread = None
            self._auto_reconnect_stop = None
    
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