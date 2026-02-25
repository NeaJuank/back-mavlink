package com.mobile.mavlink.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mobile.mavlink.models.Telemetry
import com.mobile.mavlink.repository.DroneRepository
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

class DroneViewModel(private val repository: DroneRepository) : ViewModel() {
    val telemetry: StateFlow<Telemetry?> = repository.telemetry
    val isConnected: StateFlow<Boolean> = repository.isConnected

    init {
        repository.connect()
    }

    override fun onCleared() {
        super.onCleared()
        repository.disconnect()
    }

    fun arm() = viewModelScope.launch {
        repository.arm()
    }

    fun disarm() = viewModelScope.launch {
        repository.disarm()
    }

    fun takeoff(altitude: Double) = viewModelScope.launch {
        repository.takeoff(altitude)
    }

    fun land() = viewModelScope.launch {
        repository.land()
    }

    fun setJoystick(throttle: Double? = null, yaw: Double? = null, pitch: Double? = null, roll: Double? = null) {
        repository.setJoystick(throttle, yaw, pitch, roll)
    }
}
