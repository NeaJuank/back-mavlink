# 🚁 Raspberry Pi Companion - MAVLink Module

Módulo minimalista para Raspberry Pi que se conecta a Pixhawk vía USB/UART.

## 📋 Requisitos

- Raspberry Pi 3B+ o superior
- Pixhawk/ArduCopter
- Cable USB (Pixhawk-to-RPi) o conexión UART

## 🚀 Instalación rápida

```bash
# Clonar/descargar este módulo en la Pi
cd /home/pi/drone/
git clone <repo> .

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar prueba
python3 main.py
```

## 📁 Estructura

```
raspberry/
├── connection.py      # Clase MAVLinkConnection (núcleo)
├── main.py           # Script de prueba
├── requirements.txt   # Dependencias
└── README.md         # Este archivo
```

## ⚙️ Configurar puerto y baudrate

Edita `main.py` línea 26-27:

```python
PORT = "/dev/ttyUSB0"  # Ajusta si es diferente
BAUD = 57600           # Ajusta según tu config
```

### Detectar puerto en Raspberry

```bash
ls /dev/tty*
```

Busca `/dev/ttyUSB*` o `/dev/ttyAMA*`

## 💻 Uso en código

```python
from connection import MAVLinkConnection

# Conectar
drone = MAVLinkConnection("/dev/ttyUSB0", 57600)

# Verificar conexión
if drone.is_connected():
    print("✅ Conectado")
    
    # Iniciar lectura de telemetría
    drone.start_telemetry_loop()
    
    # Enviar comando
    drone.send_arm()
    drone.send_mode("GUIDED")
    
    # Limpiar
    drone.stop_telemetry_loop()
    drone.disconnect()
```

## 📡 Métodos disponibles

### Conexión

- `connect()` - Conectar (se llama automático en __init__)
- `disconnect()` - Desconectar
- `is_connected()` - Verificar estado

### Telemetría

- `recv_match(msg_type, blocking=False, timeout=None)` - Recibir mensaje específico
- `start_telemetry_loop()` - Iniciar thread de lectura (no bloqueante)
- `stop_telemetry_loop()` - Detener thread

### Comandos

- `send_arm()` - Armar motores
- `send_disarm()` - Desarmar motores
- `send_mode(mode_name)` - Cambiar modo (GUIDED, RTL, LOITER, etc)
- `wait_ack(command_id, timeout=3)` - Esperar confirmación de comando

## 🔧 Logs

El módulo usa logging estándar de Python:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Niveles disponibles: DEBUG, INFO, WARNING, ERROR, CRITICAL

## ⚠️ Notas importantes

- El heartbeat se espera con timeout=10s
- Los reintentos de conexión son automáticos (exponential backoff)
- El telemetry loop es **no bloqueante** (corre en thread separado)
- Los mensajes se procesan cada 0.01s por defecto

## 🚀 Próximos pasos

Después puedes agregar:
- Guardado de logs en archivo
- API REST simple en puerto local
- Sincronización con backend PC
- Grabación de misiones

## 📝 Licencia

Parte del proyecto `back-mavlink`
