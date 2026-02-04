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
- MAVLink via USB a Pixhawk (`/dev/ttyACM0`) o por TCP si expones el puerto.
- WebSocket en `/ws/telemetry` para datos en tiempo real.
- Next.js y React Native se conectan al backend (ej. `http://<HOST>:8000`).

### Endpoint útil
- `GET /api/device` — devuelve `{ device, connected, simulated }`. Útil para la UI para mostrar si el backend está en modo `SIM` o usando un dispositivo real.

### Desarrollo sin Pixhawk (SIM)
Si estás desarrollando sin la Pi conectada, el backend detecta automáticamente la ausencia de `/dev/ttyACM0` y hace *fallback* a un controlador simulado. También puedes forzar el simulador con:

```bash
export MAVLINK_DEVICE=SIM    # Linux/macOS
set MAVLINK_DEVICE=SIM       # Windows (cmd)
$Env:MAVLINK_DEVICE = 'SIM'  # PowerShell
```

### Ejecutar backend desde Windows (WSL2)
Si deseas usar el hardware conectado a tu máquina Windows desde Docker, la forma más sencilla es ejecutar el backend desde WSL2:

1. Habilita WSL2 y actualiza: `wsl --update` (ejecuta desde PowerShell como admin).
2. Conecta la Pi o USB; en WSL comprueba que `/dev/ttyACM*` aparece: `ls /dev/ttyACM*`.
3. Ejecuta `docker compose up --build` desde WSL (asegúrate Docker Desktop está integrado con WSL2). El contenedor podrá acceder a `/dev/ttyACM0`.

Si no puedes exponer el device a WSL, usa el modo `SIM` o expón el puerto de la Pi por red (ver abajo).

### Exponer `/dev/ttyACM0` desde la Raspberry Pi por red (ser2net / socat)
Si quieres ejecutar el backend en Windows pero mantener la Pixhawk en la Raspberry Pi, expón el puerto serial por TCP:

- Con `ser2net` (recomendado):
  1. `sudo apt update && sudo apt install ser2net`
  2. Añade en `/etc/ser2net.conf` una línea, p. ej.:
     ```
     6000:telnet:0:/dev/ttyACM0:57600 8DATABITS NONE 1STOPBIT
     ```
  3. `sudo systemctl restart ser2net`
  4. En tu backend usa `MAVLINK_DEVICE='tcp:PI_IP:6000'`.

- Con `socat` (manualmente):
  - En la Pi: `socat -d -d PTY,link=/tmp/ttyV0,raw,echo=0 TCP-LISTEN:6000,reuseaddr`
  - En la máquina Windows (o container): `socat -d -d /tmp/ttyV0,raw,echo=0 TCP:PI_IP:6000` y apunta el backend al `/tmp/ttyV0` o a `tcp:PI_IP:6000`.

### Qué consume el Frontend
El dashboard Next.js (`/app/page.tsx`) ahora consume:
- WebSocket: `ws://<BACKEND>:8000/ws/telemetry` — telemetría en tiempo real
- `GET /api/device` — estado del dispositivo (simulado/real)
- `GET /api/status` — estado general del dron
- `GET /api/battery` — estado de la batería
- `POST /api/command/{arm|disarm|takeoff|land}` — acciones rápidas desde UI

Se añadió además un endpoint UI para mostrar `device` y un panel de controles rápidos en el frontend para probar comandos.



## Mejoras
- Manejo de errores en MAVLink con try-except.
- Docker para aislamiento en ARM64 (Raspberry Pi).

## Notas para Raspberry Pi
- Asegúrate de que Docker tenga acceso a dispositivos USB (`privileged: true`).
- Si hay problemas con el puerto, verifica permisos: `sudo usermod -aG dialout $USER` y reinicia.
- Para producción, configura un dominio o VPN para acceso seguro.