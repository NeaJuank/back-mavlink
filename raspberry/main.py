#!/usr/bin/env python3
"""
Main entry point para Raspberry Pi Companion
Ajusta el puerto y baudrate según tu setup
"""

import logging
import sys
import time
from connection import MAVLinkConnection

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Función main para prueba básica de conexión"""
    
    # ========================================
    # AJUSTA ESTOS VALORES SEGÚN TU HARDWARE
    # ========================================
    PORT = "/dev/ttyUSB0"  # Cambia si es diferente
    BAUD = 57600           # Cambiar según tu configuración
    
    logger.info("=" * 60)
    logger.info("🚁 Raspberry Pi Companion - MAVLink Test")
    logger.info("=" * 60)
    logger.info(f"Puerto: {PORT}")
    logger.info(f"Baudrate: {BAUD}")
    logger.info("=" * 60)
    
    try:
        # Conectar
        drone = MAVLinkConnection(PORT, BAUD)
        
        if not drone.is_connected():
            logger.error("❌ No se pudo conectar al Pixhawk")
            sys.exit(1)
        
        logger.info("✅ Conexión establecida")
        
        # Iniciar lectura de telemetría
        drone.start_telemetry_loop(interval=0.1)
        
        logger.info("📡 Leyendo telemetría por 30 segundos...")
        logger.info("Presiona Ctrl+C para detener")
        
        try:
            # Mantener el programa corriendo
            for i in range(300):  # 30 segundos
                time.sleep(0.1)
                if not drone.is_connected():
                    logger.warning("⚠️ Conexión perdida")
                    break
        except KeyboardInterrupt:
            logger.info("\n⏹️ Deteniendo...")
        
        # Limpiar
        drone.stop_telemetry_loop()
        drone.disconnect()
        
        logger.info("✅ Desconectado")
    
    except ConnectionError as e:
        logger.error(f"❌ Error de conexión: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Error inesperado: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
