# backend/config.py
import os
from dotenv import load_dotenv

load_dotenv()

# MAVLink
MAVLINK_DEVICE = os.getenv('MAVLINK_DEVICE', '/dev/ttyUSB0')
MAVLINK_BAUD = int(os.getenv('MAVLINK_BAUD', 57600))

# API
API_HOST = os.getenv('API_HOST', '0.0.0.0')
API_PORT = int(os.getenv('API_PORT', 8000))

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')