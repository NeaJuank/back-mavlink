import React, { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import { API_URL, WS_URL } from '../config';

interface Telemetry {
  armed: boolean;
  mode: string;
  altitude: number;
  latitude: number;
  longitude: number;
  roll: number;
  pitch: number;
  yaw: number;
  battery_voltage: number;
  battery_remaining: number;
  ground_speed: number;
  vertical_speed: number;
  satellites: number;
  hdop: number;
}

interface DroneContextType {
  telemetry: Telemetry;
  connected: boolean;
  sendCommand: (type: string, params?: any) => Promise<void>;
  armDrone: () => Promise<void>;
  disarmDrone: () => Promise<void>;
  takeoff: (altitude: number) => Promise<void>;
  land: () => Promise<void>;
  emergency: (action: 'STOP' | 'RTL' | 'LAND') => Promise<void>;
  setJoystick: (throttle?: number, yaw?: number, pitch?: number, roll?: number) => void;
}

const DroneContext = createContext<DroneContextType | undefined>(undefined);

export const useDrone = () => {
  const context = useContext(DroneContext);
  if (!context) {
    throw new Error('useDrone debe usarse dentro de DroneProvider');
  }
  return context;
};

export const DroneProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [telemetry, setTelemetry] = useState<Telemetry>({
    armed: false,
    mode: 'UNKNOWN',
    altitude: 0,
    latitude: 0,
    longitude: 0,
    roll: 0,
    pitch: 0,
    yaw: 0,
    battery_voltage: 0,
    battery_remaining: 0,
    ground_speed: 0,
    vertical_speed: 0,
    satellites: 0,
    hdop: 0,
  });

  const [connected, setConnected] = useState(false);
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connectWebSocket = useCallback(() => {
    try {
      console.log(`[WS] Conectando a ${WS_URL} ...`);
      ws.current = new WebSocket(WS_URL);

      ws.current.onopen = () => {
        console.log('[WS] ✅ Conexión establecida');
        setConnected(true);
      };

      ws.current.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);

          if (message.type === 'telemetry') {
            setTelemetry(message.data);
          } else if (message.type === 'command_ack') {
            console.log('[WS] ACK recibido:', message.command, '→', JSON.stringify(message.result));
          } else {
            console.log('[WS] Mensaje desconocido:', message.type);
          }
        } catch (error) {
          console.error('[WS] Error parseando mensaje:', error, '| raw:', event.data?.slice?.(0, 100));
        }
      };

      ws.current.onerror = (error) => {
        // En React Native el evento de error no incluye detalles, pero lo registramos
        console.error('[WS] ❌ Error de WebSocket (ver logs del backend para detalles):', error);
        setConnected(false);
      };

      ws.current.onclose = (event) => {
        console.warn(
          `[WS] ⚠️ Conexión cerrada — code=${event.code} reason='${event.reason}'`
        );
        /*
         * Códigos de cierre comunes:
         *   1000 = cierre normal
         *   1001 = el servidor se fue (going away)
         *   1006 = cierre anormal (sin frame de cierre — error de red o excepción en el servidor)
         *   1011 = error interno del servidor
         */
        setConnected(false);

        // Reconectar después de 3 segundos
        reconnectTimeout.current = setTimeout(() => {
          console.log('[WS] 🔄 Intentando reconectar...');
          connectWebSocket();
        }, 3000);
      };
    } catch (error) {
      console.error('[WS] Error creando WebSocket:', error);
    }
  }, []);

  useEffect(() => {
    connectWebSocket();

    return () => {
      if (ws.current) {
        ws.current.close();
      }
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
      }
    };
  }, [connectWebSocket]);

  const sendCommand = async (type: string, params: any = {}) => {
    if (!ws.current || ws.current.readyState !== WebSocket.OPEN) {
      const stateMap: Record<number, string> = {
        [WebSocket.CONNECTING]: 'CONNECTING',
        [WebSocket.OPEN]: 'OPEN',
        [WebSocket.CLOSING]: 'CLOSING',
        [WebSocket.CLOSED]: 'CLOSED',
      };
      const state = ws.current ? stateMap[ws.current.readyState] ?? ws.current.readyState : 'null';
      console.error(`[WS] No se puede enviar '${type}' — estado actual: ${state}`);
      return;
    }

    const command = { type, params };
    console.log(`[WS] Enviando comando: ${type}`, params);
    ws.current.send(JSON.stringify(command));
  };

  const armDrone = async () => {
    try {
      const response = await axios.post(`${API_URL}/api/arm`, { force: false });
      console.log('Armar:', response.data);
    } catch (error) {
      console.error('Error armando:', error);
    }
  };

  const disarmDrone = async () => {
    try {
      const response = await axios.post(`${API_URL}/api/disarm`);
      console.log('Desarmar:', response.data);
    } catch (error) {
      console.error('Error desarmando:', error);
    }
  };

  const takeoff = async (altitude: number) => {
    try {
      const response = await axios.post(`${API_URL}/api/takeoff`, { altitude });
      console.log('Despegue:', response.data);
    } catch (error) {
      console.error('Error despegando:', error);
    }
  };

  const land = async () => {
    try {
      const response = await axios.post(`${API_URL}/api/land`);
      console.log('Aterrizaje:', response.data);
    } catch (error) {
      console.error('Error aterrizando:', error);
    }
  };

  const emergency = async (action: 'STOP' | 'RTL' | 'LAND') => {
    try {
      const response = await axios.post(`${API_URL}/api/emergency`, { action });
      console.log('Emergencia:', response.data);
    } catch (error) {
      console.error('Error en emergencia:', error);
    }
  };

  const setJoystick = (throttle?: number, yaw?: number, pitch?: number, roll?: number) => {
    sendCommand('RC_CONTROL', { throttle, yaw, pitch, roll });
  };

  return (
    <DroneContext.Provider
      value={{
        telemetry,
        connected,
        sendCommand,
        armDrone,
        disarmDrone,
        takeoff,
        land,
        emergency,
        setJoystick,
      }}
    >
      {children}
    </DroneContext.Provider>
  );
};
