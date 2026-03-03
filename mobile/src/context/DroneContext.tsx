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
  // Todos los comandos devuelven Promise<CommandResult> para poder mostrar errores
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

  const ws                 = useRef<WebSocket | null>(null);
  const reconnectTimeout   = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Mapa de comandos pendientes: type → resolve de la Promise
  const pendingCommands    = useRef<Map<string, (result: CommandResult) => void>>(new Map());

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
            // Resolver la Promise del comando que estaba esperando
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

        // Rechazar todos los comandos pendientes
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

  // ── sendCommand — único canal de comandos ────────────────────────────────────
  // Todos los comandos van por WebSocket y devuelven Promise<CommandResult>
  // con timeout de 5 segundos para no quedar esperando indefinidamente.

  const sendCommand = useCallback((type: string, params: any = {}): Promise<CommandResult> => {
    return new Promise((resolve) => {
      if (!ws.current || ws.current.readyState !== WebSocket.OPEN) {
        resolve({ success: false, message: 'Sin conexión con el dron' });
        return;
      }

      // RC_CONTROL y RC_RESET no reciben ACK del backend (son continuos a 10Hz)
      // Se resuelven inmediatamente sin esperar respuesta
      const NO_ACK_COMMANDS = ['RC_CONTROL', 'RC_RESET'];
      if (NO_ACK_COMMANDS.includes(type)) {
        ws.current.send(JSON.stringify({ type, params }));
        resolve({ success: true, message: 'RC enviado' });
        return;
      }

      // Timeout de 5 segundos para comandos que sí esperan ACK
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

  // ── Comandos de alto nivel ────────────────────────────────────────────────────

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

  // RC Control — no necesita ACK, es continuo a 10Hz
  const setJoystick = useCallback((
    throttle?: number, yaw?: number, pitch?: number, roll?: number
  ) => {
    if (!ws.current || ws.current.readyState !== WebSocket.OPEN) return;
    ws.current.send(JSON.stringify({
      type:   'RC_CONTROL',
      params: { throttle, yaw, pitch, roll },
    }));
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