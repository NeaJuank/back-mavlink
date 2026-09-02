/**
 * Configuración de conexión al backend (Raspberry Pi).
 * Cambia RASPBERRY_IP por la IP de tu Raspberry en la red local.
 */
const RASPBERRY_IP = '10.0.2.2';

export const API_URL = `http://${RASPBERRY_IP}:8000`;
export const WS_URL = `ws://${RASPBERRY_IP}:8000/ws/telemetry`;
