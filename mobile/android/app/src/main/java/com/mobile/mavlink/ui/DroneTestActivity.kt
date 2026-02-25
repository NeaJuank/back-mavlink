package com.mobile.mavlink.ui

import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.google.gson.Gson
import com.mobile.mavlink.network.DroneApiService
import com.mobile.mavlink.network.DroneWebSocketClient
import com.mobile.mavlink.repository.DroneRepository
import com.mobile.mavlink.models.EmergencyAction
import com.mobile.R
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.launch
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

class DroneTestActivity : AppCompatActivity() {

    private lateinit var repository: DroneRepository
    private lateinit var viewModel: DroneViewModel

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_drone_test)

        val statusText = findViewById<TextView>(R.id.statusText)
        val telemetryText = findViewById<TextView>(R.id.telemetryText)
        val btnArm = findViewById<Button>(R.id.btnArm)
        val btnTakeoff = findViewById<Button>(R.id.btnTakeoff)
        val btnLand = findViewById<Button>(R.id.btnLand)
        val btnEmergency = findViewById<Button>(R.id.btnEmergency)

        // Inicialización manual (en una app real usarías Inyección de Dependencias como Hilt)
        val raspberryIp = "192.168.137.22"
        val retrofit = Retrofit.Builder()
            .baseUrl("http://$raspberryIp:8000")
            .addConverterFactory(GsonConverterFactory.create())
            .build()

        val apiService = retrofit.create(DroneApiService::class.java)
        val wsClient = DroneWebSocketClient("ws://$raspberryIp:8000/ws/telemetry")
        
        repository = DroneRepository(apiService, wsClient)
        viewModel = DroneViewModel(repository)

        // Observar estado de conexión
        lifecycleScope.launchWhenStarted {
            viewModel.isConnected.collect { connected ->
                statusText.text = if (connected) "Status: CONECTADO" else "Status: DESCONECTADO"
                statusText.setTextColor(if (connected) 0xFF00FF88.toInt() else 0xFFFF0044.toInt())
            }
        }

        // Observar telemetría
        lifecycleScope.launchWhenStarted {
            viewModel.telemetry.collect { telemetry ->
                telemetry?.let {
                    telemetryText.text = """
                        MODO: ${it.mode}
                        ARMADO: ${it.armed}
                        ALTITUD: ${"%.1f".format(it.altitude)}m
                        BATERÍA: ${it.batteryRemaining.toInt()}%
                        GPS: ${it.satellites} sats
                        LAT: ${it.latitude}
                        LON: ${it.longitude}
                    """.trimIndent()
                }
            }
        }

        // Configurar botones
        btnArm.setOnClickListener { viewModel.arm() }
        btnTakeoff.setOnClickListener { viewModel.takeoff(10.0) }
        btnLand.setOnClickListener { viewModel.land() }
        btnEmergency.setOnClickListener {
            lifecycleScope.launch {
                repository.emergency(EmergencyAction.RTL)
            }
        }
    }
}
