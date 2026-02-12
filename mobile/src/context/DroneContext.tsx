import React, { createContext, useContext, useState, useEffect, useRef } from 'react';
import axios from 'axios';

// ⚠️ CONFIGURACIÓN - Cambiar a la IP de tu Raspberry Pi
const API_URL = 'http://192.168.1.100:8000';
const WS_URL = 'ws://192.168.1.100:8000/ws/telemetry';

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
  const reconnectTimeout = useRef<NodeJS.Timeout | null>(null);

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
  }, []);

  const connectWebSocket = () => {
    try {
      ws.current = new WebSocket(WS_URL);

      ws.current.onopen = () => {
        console.log('✅ WebSocket conectado');
        setConnected(true);
      };

      ws.current.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);

          if (message.type === 'telemetry') {
            setTelemetry(message.data);
          } else if (message.type === 'command_ack') {
            console.log('Comando ACK:', message.command, message.result);
          }
        } catch (error) {
          console.error('Error parseando mensaje WebSocket:', error);
        }
      };

      ws.current.onerror = (error) => {
        console.error('❌ Error WebSocket:', error);
        setConnected(false);
      };

      ws.current.onclose = () => {
        console.log('⚠️ WebSocket desconectado');
        setConnected(false);

        // Reconectar después de 3 segundos
        reconnectTimeout.current = setTimeout(() => {
          console.log('🔄 Intentando reconectar...');
          connectWebSocket();
        }, 3000);
      };
    } catch (error) {
      console.error('Error creando WebSocket:', error);
    }
  };

  const sendCommand = async (type: string, params: any = {}) => {
    if (!ws.current || ws.current.readyState !== WebSocket.OPEN) {
      console.error('WebSocket no conectado');
      return;
    }

    const command = {
      type,
      params,
    };

    ws.current.send(JSON.stringify(command));
  };

  const armDrone = async () => {
    try {
      const response = await axios.post(`${API_URL}/api/arm`);
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
