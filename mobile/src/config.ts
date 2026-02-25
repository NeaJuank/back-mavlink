/**
 * Configuración de conexión al backend (Raspberry Pi).
 * Cambia RASPBERRY_IP por la IP de tu Raspberry en la red local.
 */
const RASPBERRY_IP = '192.168.137.95';

export const API_URL = `https://${RASPBERRY_IP}:8000`;
export const WS_URL = `wss://${RASPBERRY_IP}:8000/ws/telemetry`;
