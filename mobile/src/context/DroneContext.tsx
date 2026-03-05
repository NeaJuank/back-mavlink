import React, { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react';
import { API_URL, WS_URL } from '../config';

// ── Tipos ──────────────────────────────────────────────────────────────────────

interface Telemetry {
  armed:              boolean;
  mode:               string;
  altitude:           number;
  latitude:           number;
  longitude:          number;
  roll:               number;
  pitch:              number;
  yaw:                number;
  battery_voltage:    number;
  battery_remaining:  number;
  ground_speed:       number;
  vertical_speed:     number;
  satellites:         number;
  hdop:               number;
}

export interface CommandResult {
  success: boolean;
  message: string;
}

interface DroneContextType {
  telemetry:   Telemetry;
  connected:   boolean;
  sendCommand: (type: string, params?: any) => Promise<CommandResult>;
  armDrone:    () => Promise<CommandResult>;
  disarmDrone: () => Promise<CommandResult>;
  takeoff:     (altitude: number) => Promise<CommandResult>;
  land:        () => Promise<CommandResult>;
  emergency:   (action: 'STOP' | 'RTL' | 'LAND') => Promise<CommandResult>;
  setJoystick: (throttle?: number, yaw?: number, pitch?: number, roll?: number) => void;
}

const DroneContext = createContext<DroneContextType | undefined>(undefined);

export const useDrone = () => {
  const ctx = useContext(DroneContext);
  if (!ctx) throw new Error('useDrone debe usarse dentro de DroneProvider');
  return ctx;
};

// ── Telemetría por defecto ─────────────────────────────────────────────────────

const DEFAULT_TELEMETRY: Telemetry = {
  armed:             false,
  mode:              'UNKNOWN',
  altitude:          0,
  latitude:          0,
  longitude:         0,
  roll:              0,
  pitch:             0,
  yaw:               0,
  battery_voltage:   0,
  battery_remaining: 0,
  ground_speed:      0,
  vertical_speed:    0,
  satellites:        0,
  hdop:              0,
};

// ── Provider ───────────────────────────────────────────────────────────────────

export const DroneProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [telemetry, setTelemetry] = useState<Telemetry>(DEFAULT_TELEMETRY);
  const [connected, setConnected] = useState(false);

  const ws               = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pendingCommands  = useRef<Map<string, (result: CommandResult) => void>>(new Map());

  // ── Estado RC persistente ─────────────────────────────────────────────────
  // Guarda los últimos valores de todos los canales para poder reenviarlos
  // a 10 Hz aunque el usuario no mueva los joysticks.
  // ArduPilot tiene un RC override timeout de ~500 ms: si no recibe paquetes
  // en ese tiempo libera el control, lo que haría caer el throttle a 0.
  const rcValues = useRef({ throttle: 0, yaw: 0, pitch: 0, roll: 0 });

  // ── WebSocket ────────────────────────────────────────────────────────────────

  const connectWebSocket = useCallback(() => {
    try {
      console.log(`[WS] Conectando a ${WS_URL}...`);
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
            const cmdType = message.command as string;
            const result: CommandResult = {
              success: message.result?.success ?? false,
              message: message.result?.message ?? '',
            };
            const resolve = pendingCommands.current.get(cmdType);
            if (resolve) {
              resolve(result);
              pendingCommands.current.delete(cmdType);
            }
            console.log(`[WS] ACK ${cmdType}:`, result);

          } else {
            console.log('[WS] Mensaje desconocido:', message.type);
          }
        } catch (err) {
          console.error('[WS] Error parseando mensaje:', err);
        }
      };

      ws.current.onerror = () => {
        console.error('[WS] ❌ Error de WebSocket');
        setConnected(false);
      };

      ws.current.onclose = (event) => {
        console.warn(`[WS] ⚠️ Cerrado — code=${event.code}`);
        setConnected(false);

        pendingCommands.current.forEach((resolve) => {
          resolve({ success: false, message: 'Conexión perdida' });
        });
        pendingCommands.current.clear();

        reconnectTimeout.current = setTimeout(() => {
          console.log('[WS] 🔄 Reconectando...');
          connectWebSocket();
        }, 3000);
      };

    } catch (err) {
      console.error('[WS] Error creando WebSocket:', err);
    }
  }, []);

  useEffect(() => {
    connectWebSocket();
    return () => {
      ws.current?.close();
      if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
    };
  }, [connectWebSocket]);

  // ── RC Heartbeat a 10 Hz ──────────────────────────────────────────────────
  // Reenvía los valores RC actuales cada 100 ms para evitar que ArduPilot
  // libere el RC override por timeout (~500 ms sin paquetes).
  // Esto garantiza que el throttle se mantenga estable aunque el usuario
  // no mueva ningún joystick.
  useEffect(() => {
    const interval = setInterval(() => {
      if (ws.current?.readyState === WebSocket.OPEN) {
        ws.current.send(JSON.stringify({
          type:   'RC_CONTROL',
          params: { ...rcValues.current },
        }));
      }
    }, 100); // 10 Hz

    return () => clearInterval(interval);
  }, []);

  // ── sendCommand ───────────────────────────────────────────────────────────

  const sendCommand = useCallback((type: string, params: any = {}): Promise<CommandResult> => {
    return new Promise((resolve) => {
      if (!ws.current || ws.current.readyState !== WebSocket.OPEN) {
        resolve({ success: false, message: 'Sin conexión con el dron' });
        return;
      }

      // RC_CONTROL y RC_RESET no esperan ACK — se envían directo
      const NO_ACK_COMMANDS = ['RC_CONTROL', 'RC_RESET'];
      if (NO_ACK_COMMANDS.includes(type)) {
        ws.current.send(JSON.stringify({ type, params }));
        resolve({ success: true, message: 'RC enviado' });
        return;
      }

      const timer = setTimeout(() => {
        if (pendingCommands.current.has(type)) {
          pendingCommands.current.delete(type);
          resolve({ success: false, message: 'Timeout — el dron no respondió' });
        }
      }, 5000);

      pendingCommands.current.set(type, (result) => {
        clearTimeout(timer);
        resolve(result);
      });

      ws.current.send(JSON.stringify({ type, params }));
      console.log(`[WS] → ${type}`, params);
    });
  }, []);

  // ── Comandos de alto nivel ────────────────────────────────────────────────

  const armDrone = useCallback(() =>
    sendCommand('ARM'), [sendCommand]);

  const disarmDrone = useCallback(() =>
    sendCommand('DISARM'), [sendCommand]);

  const takeoff = useCallback((altitude: number) =>
    sendCommand('TAKEOFF', { altitude }), [sendCommand]);

  const land = useCallback(() =>
    sendCommand('LAND'), [sendCommand]);

  const emergency = useCallback((action: 'STOP' | 'RTL' | 'LAND') =>
    sendCommand('EMERGENCY', { action }), [sendCommand]);

  // ── setJoystick ───────────────────────────────────────────────────────────
  // Actualiza solo los canales que recibe (undefined = no cambiar).
  // El RC heartbeat se encarga de reenviar los 4 valores a 10 Hz,
  // así que aquí solo necesitamos actualizar el estado interno.
  const setJoystick = useCallback((
    throttle?: number,
    yaw?:      number,
    pitch?:    number,
    roll?:     number,
  ) => {
    if (throttle !== undefined) rcValues.current.throttle = throttle;
    if (yaw      !== undefined) rcValues.current.yaw      = yaw;
    if (pitch    !== undefined) rcValues.current.pitch    = pitch;
    if (roll     !== undefined) rcValues.current.roll     = roll;

    // Envío inmediato además del heartbeat periódico — reduce latencia
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({
        type:   'RC_CONTROL',
        params: { ...rcValues.current },
      }));
    }
  }, []);

  return (
    <DroneContext.Provider value={{
      telemetry,
      connected,
      sendCommand,
      armDrone,
      disarmDrone,
      takeoff,
      land,
      emergency,
      setJoystick,
    }}>
      {children}
    </DroneContext.Provider>
  );
};