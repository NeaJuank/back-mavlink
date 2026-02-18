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
   - Desde un navegador: `http://<IP_Raspberry>:3000` (o `http://192.168.137.43:4545` si usas el frontend en Docker).
   - App React Native y frontend ya apuntan por defecto a la Raspberry **192.168.137.43** (ver más abajo para cambiar la IP).

### IP de la Raspberry (pruebas)
Para las pruebas el proyecto está configurado con la IP **192.168.137.43**. Si tu Raspberry tiene otra IP:
- **App móvil:** edita `mobile/src/config.ts` → `RASPBERRY_IP`.
- **Frontend:** variable de entorno `NEXT_PUBLIC_BACKEND_URL=http://<IP>:8000` o edita `frontend/app/config.ts`.

5. **Monitoreo**:
   - Logs: `docker-compose logs`.
   - Estadísticas: `docker stats`.

## Base de datos (PostgreSQL)

### Para qué sirve
La base de datos guarda **historial de telemetría** del dron: altitud, velocidad, actitud (pitch/roll/yaw), batería, etc. El backend va guardando un snapshot cada varios segundos (cuando hay conexión MAVLink y telemetría activa). No es obligatoria para pilotar en tiempo real; el control y la telemetría en vivo van por MAVLink y WebSocket.

### Cómo funciona

1. **PostgreSQL** es el motor. Puede estar:
   - **En Docker** (recomendado): el `docker-compose` levanta un contenedor `postgres` con la base `drones`, usuario `dronix_user` y contraseña `DronixSecure2024!`.
   - **Instalado en tu PC/Raspberry**: creas tú la base y el usuario y configuras `DB_URL` en `.env`.

2. **Crear las tablas** (solo la primera vez o tras borrar la BD):
   - Si usas **todo con Docker** (`docker-compose up`): el backend ya ejecuta `python create_tables.py` al arrancar y crea la tabla `telemetry`.
   - Si corres el **backend a mano** (en tu PC o en la Raspberry):
     - Asegúrate de que Postgres esté corriendo y que `DB_URL` en tu `.env` apunte a esa instancia (ver abajo).
     - Desde la raíz del proyecto:
       ```bash
       python create_tables.py
       ```
     - Debe imprimir `Tables created`. Si da error de conexión, revisa usuario, contraseña, host y nombre de la base en `DB_URL`.

3. **Dónde se configura la conexión**
   - **Backend en Docker:** usa la variable de entorno `DB_URL` que define el `docker-compose` (apunta al servicio `postgres:5432`, base `drones`). No necesitas tocar nada.
   - **Backend en local** (por ejemplo en Windows, conectando a Postgres en tu máquina o en Docker solo Postgres):
     - En la **raíz del proyecto** pon un archivo `.env` con algo como:
       ```
       DB_URL=postgresql://dronix_user:DronixSecure2024!@localhost:5432/drones
       ```
     - Si Postgres está en **otra máquina** (p. ej. la Raspberry), cambia `localhost` por la IP:
       ```
       DB_URL=postgresql://dronix_user:DronixSecure2024!@192.168.137.43:5432/drones
       ```
     - El `.env` de ejemplo del repo ya usa la base `drones` y el usuario anterior para que coincida con lo que crea el `docker-compose`.

### Resumen rápido

| Situación | Qué hacer |
|----------|-----------|
| Todo en Docker (`docker-compose up`) | Nada. Postgres y tablas se gestionan solos. |
| Solo Postgres en Docker, backend en tu PC | 1) `docker-compose up -d postgres` 2) `python create_tables.py` desde la raíz 3) Arrancar el backend (usa `.env` con `DB_URL=...@localhost:5432/drones`). |
| Postgres instalado en tu dispositivo | Crear base `drones` y usuario `dronix_user` (contraseña `DronixSecure2024!`), poner `DB_URL` en `.env`, ejecutar `python create_tables.py`. |

Si no quieres usar base de datos (solo control en vivo), el backend puede arrancar igual; la parte que guarda telemetría en BD fallará y se registra un warning, pero el resto sigue funcionando.

## Conexiones
- Backend conecta a PostgreSQL (según `DB_URL` en config o `.env`).
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