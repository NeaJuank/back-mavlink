from pymavlink import mavutil
import logging

logger = logging.getLogger(__name__)

class MAVLinkConnection:
    def __init__(self, device, baud):
        try:
            self.master = mavutil.mavlink_connection(device, baud=baud)
            msg = self.master.wait_heartbeat(timeout=5)
            if msg:
                logger.info("✔ Pixhawk conectada")
            else:
                logger.warning("⚠ No se recibió heartbeat, continuando sin conexión")
        except Exception as e:
            logger.error(f"Error connecting to MAVLink: {e}")
            self.master = None

    def recv(self):
        if self.master:
            try:
                return self.master.recv_match(blocking=False)
            except Exception as e:
                logger.error(f"Error receiving MAVLink message: {e}")
                return None
        return None

    def arm(self):
        if self.master:
            try:
                self.master.arducopter_arm()
                logger.info("Arm command sent")
            except Exception as e:
                logger.error(f"Error sending arm command: {e}")

    def disarm(self):
        if self.master:
            try:
                self.master.arducopter_disarm()
                logger.info("Disarm command sent")
            except Exception as e:
                logger.error(f"Error sending disarm command: {e}")

    def takeoff(self, altitude):
        if self.master:
            try:
                self.master.mav.command_long_send(
                    self.master.target_system,
                    self.master.target_component,
                    mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
                    0, 0, 0, 0, 0, 0, 0, altitude
                )
                logger.info(f"Takeoff command sent with altitude {altitude}")
            except Exception as e:
                logger.error(f"Error sending takeoff command: {e}")
