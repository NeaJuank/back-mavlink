package com.mobile.mavlink.repository

import com.mobile.mavlink.models.DroneCommand
import com.mobile.mavlink.models.EmergencyAction
import com.mobile.mavlink.network.DroneApiService
import com.mobile.mavlink.network.DroneWebSocketClient
import com.mobile.mavlink.network.EmergencyParams
import com.mobile.mavlink.network.TakeoffParams
import kotlinx.coroutines.flow.StateFlow

class DroneRepository(
    private val apiService: DroneApiService,
    private val wsClient: DroneWebSocketClient
) {
    val telemetry = wsClient.telemetry
    val isConnected = wsClient.isConnected

    fun connect() {
        wsClient.connect()
    }

    fun disconnect() {
        wsClient.disconnect()
    }

    suspend fun arm() = runCatching { apiService.arm() }

    suspend fun disarm() = runCatching { apiService.disarm() }

    suspend fun takeoff(altitude: Double) = runCatching { 
        apiService.takeoff(TakeoffParams(altitude)) 
    }

    suspend fun land() = runCatching { apiService.land() }

    suspend fun emergency(action: EmergencyAction) = runCatching {
        apiService.emergency(EmergencyParams(action.name))
    }

    fun setJoystick(throttle: Double? = null, yaw: Double? = null, pitch: Double? = null, roll: Double? = null) {
        val params = mutableMapOf<String, Any?>()
        throttle?.let { params["throttle"] = it }
        yaw?.let { params["yaw"] = it }
        pitch?.let { params["pitch"] = it }
        roll?.let { params["roll"] = it }
        
        wsClient.sendCommand(DroneCommand("RC_CONTROL", params))
    }
}
