package com.mobile.mavlink.network

import android.util.Log
import com.google.gson.Gson
import com.mobile.mavlink.models.DroneCommand
import com.mobile.mavlink.models.Telemetry
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import okhttp3.*
import java.util.concurrent.TimeUnit

class DroneWebSocketClient(
    private val wsUrl: String,
    private val gson: Gson = Gson()
) {
    private val client = OkHttpClient.Builder()
        .readTimeout(0, TimeUnit.MILLISECONDS)
        .build()

    private var webSocket: WebSocket? = null
    private val _telemetry = MutableStateFlow<Telemetry?>(null)
    val telemetry: StateFlow<Telemetry?> = _telemetry

    private val _isConnected = MutableStateFlow(false)
    val isConnected: StateFlow<Boolean> = _isConnected

    private val scope = CoroutineScope(Dispatchers.IO)

    fun connect() {
        val request = Request.Builder().url(wsUrl).build()
        webSocket = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                Log.d("DroneWS", "✅ Conexión establecida")
                _isConnected.value = true
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                try {
                    val map = gson.fromJson(text, Map::class.java)
                    val type = map["type"] as? String
                    if (type == "telemetry") {
                        val dataJson = gson.toJson(map["data"])
                        val telemetry = gson.fromJson(dataJson, Telemetry::class.java)
                        _telemetry.value = telemetry
                    } else if (type == "command_ack") {
                        Log.d("DroneWS", "ACK recibido: ${map["command"]}")
                    }
                } catch (e: Exception) {
                    Log.e("DroneWS", "Error parseando mensaje: ${e.message}")
                }
            }

            override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
                Log.w("DroneWS", "⚠️ Cerrando: $code / $reason")
                _isConnected.value = false
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                Log.e("DroneWS", "❌ Error: ${t.message}")
                _isConnected.value = false
                reconnect()
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                Log.w("DroneWS", "🚫 Cerrado: $code / $reason")
                _isConnected.value = false
                reconnect()
            }
        })
    }

    private fun reconnect() {
        scope.launch {
            delay(3000)
            Log.d("DroneWS", "🔄 Intentando reconectar...")
            connect()
        }
    }

    fun sendCommand(command: DroneCommand) {
        val json = gson.toJson(command)
        webSocket?.send(json) ?: Log.e("DroneWS", "No se puede enviar, el WebSocket no está conectado")
    }

    fun disconnect() {
        webSocket?.close(1000, "Desconectado por el usuario")
    }
}
