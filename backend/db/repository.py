from db.database import SessionLocal
from db.models import Telemetry
import logging

logger = logging.getLogger(__name__)

def save_telemetry(data):
    try:
        db = SessionLocal()
        t = Telemetry(**data)
        db.add(t)
        db.commit()
        db.close()
        logger.info("Telemetry saved to database")
    except Exception as e:
        logger.error(f"Error saving telemetry: {e}")
        if 'db' in locals():
            db.rollback()
            db.close()
