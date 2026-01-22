# Drone Telemetry System

Este proyecto incluye un backend FastAPI para telemetría de drones, simulación SITL de Pixhawk, base de datos PostgreSQL, frontend Next.js, app móvil React Native, y Dockerización completa.

## Estructura
- `backend/`: API FastAPI con MAVLink y WebSocket
- `frontend/`: Dashboard Next.js
- `mobile/`: App React Native
- `scripts/`: Scripts para SITL
- `docker-compose.yml`: Configuración Docker

## Inicio Rápido

### Despliegue en Raspberry Pi con Pixhawk
1. **Prepara la Raspberry Pi**:
   - Instala Raspberry Pi OS (64-bit) en una tarjeta SD.
   - Conecta la Pixhawk a la Raspberry Pi vía USB.
   - Actualiza el sistema: `sudo apt update && sudo apt upgrade`.
   - Instala Docker: Sigue https://docs.docker.com/engine/install/raspberry-pi/.
   - Instala Git: `sudo apt install git`.
   - Clona el proyecto: `git clone <tu-repo> && cd back-mavlink`.

2. **Configura el Proyecto**:
   - Verifica el puerto de la Pixhawk: `ls /dev/tty*` (debe ser `/dev/ttyACM0`).
   - Si es diferente, edita `backend/config.py` o establece la variable de entorno `MAVLINK_DEVICE`.

3. **Ejecuta con Docker**:
   ```
   docker-compose up --build -d
   ```
   - PostgreSQL: En contenedor `postgres`.
   - Backend: `http://localhost:8000` (accesible en `http://<IP_Raspberry>:8000`).
   - Frontend: `http://localhost:3000` (accesible en `http://<IP_Raspberry>:3000`).

4. **Acceso Remoto**:
   - Desde un navegador: `http://<IP_Raspberry>:3000` para el dashboard.
   - App React Native: Cambia la IP en el código a `<IP_Raspberry>:8000` para WebSocket.

5. **Monitoreo**:
   - Logs: `docker-compose logs`.
   - Estadísticas: `docker stats`.

## Conexiones
- Backend conecta a PostgreSQL en Docker.
- MAVLink via USB a Pixhawk (`/dev/ttyACM0`).
- WebSocket en /ws/telemetry para datos en tiempo real.
- Next.js y React Native se conectan al backend.

## Mejoras
- Manejo de errores en MAVLink con try-except.
- Docker para aislamiento en ARM64 (Raspberry Pi).

## Notas para Raspberry Pi
- Asegúrate de que Docker tenga acceso a dispositivos USB (`privileged: true`).
- Si hay problemas con el puerto, verifica permisos: `sudo usermod -aG dialout $USER` y reinicia.
- Para producción, configura un dominio o VPN para acceso seguro.