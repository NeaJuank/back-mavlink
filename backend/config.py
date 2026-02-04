# backend/config.py
import os
from dotenv import load_dotenv

load_dotenv()

# MAVLink
# If MAVLINK_DEVICE env var is set use it; otherwise perform runtime detection and fall back to 'SIM'.
MAVLINK_DEVICE = os.getenv('MAVLINK_DEVICE', '').strip()
MAVLINK_BAUD = int(os.getenv('MAVLINK_BAUD', 57600))


def detect_mavlink_device() -> str:
    """Auto-detect MAVLink serial device at runtime.

    Priority:
    1. `MAVLINK_DEVICE` environment var (can be 'SIM').
    2. Common device paths (/dev/ttyACM*, /dev/ttyUSB*).
    3. /dev/serial/by-id entries.
    4. Fallback to 'SIM'.

    This function *probes* candidate device nodes and only returns paths
    that appear openable to avoid selecting devices that exist but are
    inaccessible from within the container (which caused noisy startup
    errors). If pyserial is not available, a safe os.open probe is used.
    """
    import logging
    logger = logging.getLogger(__name__)

    # Respect explicit env value (validate accessibility unless it's 'SIM')
    if MAVLINK_DEVICE:
        if MAVLINK_DEVICE.upper() == 'SIM':
            return 'SIM'
        if os.path.exists(MAVLINK_DEVICE):
            # Probe the device to ensure it can be opened
            try:
                try:
                    # Prefer pyserial if available
                    import serial
                    s = serial.Serial(MAVLINK_DEVICE, MAVLINK_BAUD, timeout=0.5)
                    s.close()
                    return MAVLINK_DEVICE
                except Exception:
                    # Fallback to os.open probe
                    fd = os.open(MAVLINK_DEVICE, os.O_RDWR | getattr(os, 'O_NONBLOCK', 0))
                    os.close(fd)
                    return MAVLINK_DEVICE
            except Exception as e:
                logger.warning(f"MAVLINK_DEVICE set to '{MAVLINK_DEVICE}' but it is not accessible: {e}. Falling back to detection.")
        else:
            logger.warning(f"MAVLINK_DEVICE set to '{MAVLINK_DEVICE}' but path does not exist. Falling back to detection.")

    # Helper to probe a candidate device
    def _probe(path: str) -> bool:
        if not os.path.exists(path):
            return False
        try:
            try:
                import serial
                s = serial.Serial(path, MAVLINK_BAUD, timeout=0.5)
                s.close()
                return True
            except Exception:
                fd = os.open(path, os.O_RDWR | getattr(os, 'O_NONBLOCK', 0))
                os.close(fd)
                return True
        except Exception:
            return False

    # Common device file candidates
    candidates = ['/dev/ttyACM0', '/dev/ttyACM1', '/dev/ttyUSB0', '/dev/ttyUSB1']
    for c in candidates:
        if _probe(c):
            return c

    # Try /dev/serial/by-id for persistent names
    try:
        import glob
        byid = glob.glob('/dev/serial/by-id/*')
        for b in byid:
            if _probe(b):
                return b
    except Exception:
        pass

    # No accessible device found -- use simulator
    return 'SIM'
# API
API_HOST = os.getenv('API_HOST', '0.0.0.0')
API_PORT = int(os.getenv('API_PORT', 8000))

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Database URL
DEFAULT_DB = 'postgresql://dronix_user:DronixSecure2024!@postgres:5432/drones'
DB_URL = os.getenv('DB_URL', DEFAULT_DB)

# Safety: prefer PostgreSQL only (no SQLite)
if not DB_URL.startswith('postgres'):
    import logging
    logger = logging.getLogger(__name__)
    logger.warning("DB_URL does not look like a PostgreSQL URL. Ensure DB_URL points to a Postgres database.")