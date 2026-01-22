import os
from dotenv import load_dotenv

# Cargar variables del archivo .env
load_dotenv()

MAVLINK_DEVICE = os.getenv("MAVLINK_DEVICE", "/dev/ttyACM0")  # Puerto USB de la Pixhawk en Raspberry Pi
MAVLINK_BAUD = int(os.getenv("MAVLINK_BAUD", "57600"))

DB_URL = os.getenv("DB_URL", "postgresql://user:password@postgres:5432/drones")
