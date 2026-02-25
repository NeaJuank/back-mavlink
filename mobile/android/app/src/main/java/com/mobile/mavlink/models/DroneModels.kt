package com.mobile.mavlink.models

import com.google.gson.annotations.SerializedName

data class Telemetry(
    val armed: Boolean,
    val mode: String,
    val altitude: Double,
    val latitude: Double,
    val longitude: Double,
    val roll: Double,
    val pitch: Double,
    val yaw: Double,
    @SerializedName("battery_voltage") val batteryVoltage: Double,
    @SerializedName("battery_remaining") val batteryRemaining: Double,
    @SerializedName("ground_speed") val groundSpeed: Double,
    @SerializedName("vertical_speed") val verticalSpeed: Double,
    val satellites: Int,
    val hdop: Double
)

data class DroneCommand(
    val type: String,
    val params: Map<String, Any?>? = null
)

data class WebSocketMessage(
    val type: String,
    val data: Any? = null,
    val command: String? = null,
    val result: Any? = null
)

enum class EmergencyAction {
    STOP, RTL, LAND
}
