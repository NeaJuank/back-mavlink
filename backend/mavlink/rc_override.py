"""
Control RC Override para joysticks virtuales
Permite control manual del dron mediante comandos RC_CHANNELS_OVERRIDE
"""
import threading
import time
import logging
from pymavlink import mavutil

logger = logging.getLogger(__name__)

class RCOverrideController:
    """
    Controlador de RC Override para control manual del dron
    Mapea valores de joystick (-1 a 1) a valores PWM (1000-2000)
    """
    
    # Canales RC estándar
    CHANNEL_ROLL = 0      # Aileron
    CHANNEL_PITCH = 1     # Elevator
    CHANNEL_THROTTLE = 2  # Throttle
    CHANNEL_YAW = 3       # Rudder
    
    # Valores PWM
    PWM_MIN = 1000
    PWM_MAX = 2000
    PWM_CENTER = 1500
    
    def __init__(self, mavlink_connection):
        """
        Args:
            mavlink_connection: Conexión MAVLink activa
        """
        self.conn = mavlink_connection
        self.channels = [0] * 8  # 8 canales RC
        self.running = False
        self.thread = None
        
        # Valores de joystick (-1.0 a 1.0)
        self.throttle = 0.0
        self.yaw = 0.0
        self.pitch = 0.0
        self.roll = 0.0
        
        # Lock para thread-safety
        self.lock = threading.Lock()
        
        logger.info("RCOverrideController inicializado")
    
    def start(self):
        """Inicia el envío periódico de comandos RC"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._send_loop, daemon=True)
            self.thread.start()
            logger.info("RC Override iniciado - Enviando a 10Hz")
    
    def stop(self):
        """Detiene el envío de comandos RC"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
        self._release_control()
        logger.info("RC Override detenido")
    
    def _send_loop(self):
        """Loop que envía comandos RC cada 100ms (10Hz)"""
        while self.running:
            try:
                with self.lock:
                    # Convertir valores de joystick a PWM
                    self.channels[self.CHANNEL_ROLL] = self._map_to_pwm(self.roll)
                    self.channels[self.CHANNEL_PITCH] = self._map_to_pwm(self.pitch)
                    self.channels[self.CHANNEL_THROTTLE] = self._map_to_pwm_throttle(self.throttle)
                    self.channels[self.CHANNEL_YAW] = self._map_to_pwm(self.yaw)
                
                # Enviar comando RC_CHANNELS_OVERRIDE
                self.conn.mav.rc_channels_override_send(
                    self.conn.target_system,
                    self.conn.target_component,
                    *self.channels
                )
                
                time.sleep(0.1)  # 10Hz
                
            except Exception as e:
                logger.error(f"Error enviando RC override: {e}")
                time.sleep(0.5)
    
    def _map_to_pwm(self, value: float) -> int:
        """
        Mapea valor de joystick (-1.0 a 1.0) a PWM (1000-2000)
        0 = centro (1500)
        """
        # Clamp value
        value = max(-1.0, min(1.0, value))
        
        # Map to PWM
        pwm = self.PWM_CENTER + int(value * 500)
        return max(self.PWM_MIN, min(self.PWM_MAX, pwm))
    
    def _map_to_pwm_throttle(self, value: float) -> int:
        """
        Mapea throttle (0.0 a 1.0) a PWM (1000-2000)
        0 = mínimo (1000), 1 = máximo (2000)
        """
        # Clamp value
        value = max(0.0, min(1.0, value))
        
        # Map to PWM
        pwm = self.PWM_MIN + int(value * 1000)
        return max(self.PWM_MIN, min(self.PWM_MAX, pwm))
    
    def _release_control(self):
        """Libera el control RC (todos los canales a 0)"""
        try:
            self.conn.mav.rc_channels_override_send(
                self.conn.target_system,
                self.conn.target_component,
                0, 0, 0, 0, 0, 0, 0, 0
            )
            logger.info("Control RC liberado")
        except Exception as e:
            logger.error(f"Error liberando control RC: {e}")
    
    # ============ API Pública ============
    
    def set_throttle(self, value: float):
        """
        Establece el throttle (altitud)
        Args:
            value: 0.0 (mínimo) a 1.0 (máximo)
        """
        with self.lock:
            self.throttle = max(0.0, min(1.0, value))
    
    def set_yaw(self, value: float):
        """
        Establece el yaw (rotación)
        Args:
            value: -1.0 (izquierda) a 1.0 (derecha)
        """
        with self.lock:
            self.yaw = max(-1.0, min(1.0, value))
    
    def set_pitch(self, value: float):
        """
        Establece el pitch (adelante/atrás)
        Args:
            value: -1.0 (atrás) a 1.0 (adelante)
        """
        with self.lock:
            self.pitch = max(-1.0, min(1.0, value))
    
    def set_roll(self, value: float):
        """
        Establece el roll (izquierda/derecha)
        Args:
            value: -1.0 (izquierda) a 1.0 (derecha)
        """
        with self.lock:
            self.roll = max(-1.0, min(1.0, value))
    
    def set_controls(self, throttle: float = None, yaw: float = None, 
                     pitch: float = None, roll: float = None):
        """
        Establece múltiples controles a la vez
        """
        with self.lock:
            if throttle is not None:
                self.throttle = max(0.0, min(1.0, throttle))
            if yaw is not None:
                self.yaw = max(-1.0, min(1.0, yaw))
            if pitch is not None:
                self.pitch = max(-1.0, min(1.0, pitch))
            if roll is not None:
                self.roll = max(-1.0, min(1.0, roll))
    
    def reset_controls(self):
        """Resetea todos los controles a neutral"""
        with self.lock:
            self.throttle = 0.0
            self.yaw = 0.0
            self.pitch = 0.0
            self.roll = 0.0
    
    def get_current_values(self) -> dict:
        """Retorna los valores actuales de los controles"""
        with self.lock:
            return {
                "throttle": self.throttle,
                "yaw": self.yaw,
                "pitch": self.pitch,
                "roll": self.roll,
                "throttle_pwm": self._map_to_pwm_throttle(self.throttle),
                "yaw_pwm": self._map_to_pwm(self.yaw),
                "pitch_pwm": self._map_to_pwm(self.pitch),
                "roll_pwm": self._map_to_pwm(self.roll),
            }
