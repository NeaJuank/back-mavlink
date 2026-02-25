package com.mobile.mavlink.network

import com.mobile.mavlink.models.EmergencyAction
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.POST

interface DroneApiService {
    @POST("/api/arm")
    suspend fun arm(): Response<Unit>

    @POST("/api/disarm")
    suspend fun disarm(): Response<Unit>

    @POST("/api/takeoff")
    suspend fun takeoff(@Body params: TakeoffParams): Response<Unit>

    @POST("/api/land")
    suspend fun land(): Response<Unit>

    @POST("/api/emergency")
    suspend fun emergency(@Body params: EmergencyParams): Response<Unit>
}

data class TakeoffParams(val altitude: Double)
data class EmergencyParams(val action: String)
