from fastapi import APIRouter, HTTPException
from mavlink.connection import MAVLinkConnection
from config import MAVLINK_DEVICE, MAVLINK_BAUD
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
mav = MAVLinkConnection(MAVLINK_DEVICE, MAVLINK_BAUD)

@router.post("/command/arm")
def arm():
    try:
        mav.arm()
        return {"status": "armed"}
    except Exception as e:
        logger.error(f"Error arming: {e}")
        raise HTTPException(status_code=500, detail="Failed to arm")

@router.post("/command/takeoff")
def takeoff(altitude: float):
    try:
        mav.takeoff(altitude)
        return {"status": "taking off"}
    except Exception as e:
        logger.error(f"Error taking off: {e}")
        raise HTTPException(status_code=500, detail="Failed to takeoff")
