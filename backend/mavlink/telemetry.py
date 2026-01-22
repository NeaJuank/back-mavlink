import time

class TelemetryBuffer:
    def __init__(self):
        self.data = {}
        self.last_save = time.time()

    def update(self, msg):
        if msg.get_type() == "VFR_HUD":
            self.data["altitude"] = msg.alt
            self.data["speed"] = msg.airspeed

        if msg.get_type() == "ATTITUDE":
            self.data["pitch"] = msg.pitch
            self.data["roll"] = msg.roll
            self.data["yaw"] = msg.yaw

        if msg.get_type() == "SYS_STATUS":
            self.data["battery"] = msg.battery_remaining

        self.data["timestamp"] = time.time()

    def should_persist(self):
        return time.time() - self.last_save > 1
