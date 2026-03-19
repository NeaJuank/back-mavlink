import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View,
  StyleSheet,
  Dimensions,
  Image,
  TouchableOpacity,
  Text,
  StatusBar,
  Alert,
  SafeAreaView,
  Animated,
  ScrollView,
  PanResponder,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Joystick } from '../components/Joystick';
import { useDrone } from '../context/DroneContext';
import { API_URL } from '../config';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');
const PANEL_WIDTH = SCREEN_WIDTH * 0.72;

// WS URL derivada del API_URL (http -> ws)
const WS_URL = API_URL.replace(/^http/, 'ws') + '/api/camera/ws';

// ── Metadatos de modos ArduPilot ──────────────────────────────────────────────
const MODE_META: Record<string, { color: string; icon: string; desc: string; requiresGPS?: boolean }> = {
  STABILIZE: { color: '#00ff88', icon: '◈', desc: 'Control manual básico' },
  ALT_HOLD:  { color: '#00d4ff', icon: '⇳', desc: 'Altura automática' },
  LOITER:    { color: '#00aaff', icon: '⊙', desc: 'Posición fija GPS', requiresGPS: true },
  POSHOLD:   { color: '#00ccaa', icon: '⊕', desc: 'Posición + altitud', requiresGPS: true },
  AUTO:      { color: '#aa88ff', icon: '⟳', desc: 'Misión automática', requiresGPS: true },
  GUIDED:    { color: '#cc88ff', icon: '➤', desc: 'Control por GCS', requiresGPS: true },
  RTL:       { color: '#ff8800', icon: '⌂', desc: 'Retorno a casa', requiresGPS: true },
  LAND:      { color: '#ffaa00', icon: '↓', desc: 'Aterrizaje automático' },
  CIRCLE:    { color: '#88aaff', icon: '○', desc: 'Círculo automático', requiresGPS: true },
  BRAKE:     { color: '#ff4400', icon: '⊗', desc: 'Freno en GPS', requiresGPS: true },
  SPORT:     { color: '#ffcc00', icon: '⚡', desc: 'Velocidad mejorada' },
  ACRO:      { color: '#ff6688', icon: '✦', desc: 'Acrobático puro' },
  DRIFT:     { color: '#ff99aa', icon: '〜', desc: 'Vuelo tipo avión' },
  FLIP:      { color: '#ff66cc', icon: '↺', desc: 'Flips automáticos' },
  THROW:     { color: '#ffdd88', icon: '⤴', desc: 'Lanzamiento manual' },
  SMARTRTL:  { color: '#ff9944', icon: '⟲', desc: 'RTL inteligente', requiresGPS: true },
};

const getMeta = (mode: string) => MODE_META[mode] ?? { color: '#555', icon: '?', desc: 'Modo desconocido' };

const MODE_GROUPS = [
  { label: 'MANUAL',              modes: ['STABILIZE', 'ACRO', 'SPORT', 'DRIFT'] },
  { label: 'ASISTIDO',            modes: ['ALT_HOLD', 'POSHOLD', 'LOITER', 'BRAKE'] },
  { label: 'AUTOMÁTICO',          modes: ['AUTO', 'GUIDED', 'CIRCLE', 'FLIP', 'THROW'] },
  { label: 'EMERGENCIA / RETORNO',modes: ['RTL', 'SMARTRTL', 'LAND'] },
];

export const DroneControlScreen: React.FC = () => {
  const { telemetry, connected, armDrone, disarmDrone, takeoff, land, emergency, setJoystick, sendCommand } =
    useDrone();
  const insets = useSafeAreaInsets();

  // ── Camera — WebSocket streaming ──────────────────────────
  const [frameUri, setFrameUri]   = useState<string | null>(null);
  const [cameraOk, setCameraOk]   = useState(false);
  const wsRef                     = useRef<WebSocket | null>(null);
  const reconnectTimer            = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connectWS = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setCameraOk(true);
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
    };

    ws.onmessage = (e) => {
      // El servidor manda base64 del frame JPEG
      setFrameUri(`data:image/jpeg;base64,${e.data}`);
    };

    ws.onerror = () => {
      setCameraOk(false);
    };

    ws.onclose = () => {
      setCameraOk(false);
      // Reconectar en 2 segundos
      reconnectTimer.current = setTimeout(connectWS, 2000);
    };
  }, []);

  useEffect(() => {
    connectWS();
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connectWS]);

  // ── Estado UI ─────────────────────────────────────────────
  const [showEmergency, setShowEmergency] = useState(false);
  const [panelOpen, setPanelOpen]         = useState(false);

  // ── Resetear joystick izquierdo al fondo cuando se arma ──
  const [leftJoystickReset, setLeftJoystickReset] = useState(false);
  const prevArmed = useRef<boolean>(false);

  useEffect(() => {
    const isArmed = telemetry?.armed ?? false;
    if (isArmed && !prevArmed.current) {
      setLeftJoystickReset(true);
      setTimeout(() => setLeftJoystickReset(false), 150);
    }
    prevArmed.current = isArmed;
  }, [telemetry?.armed]);

  // ── PWM display ───────────────────────────────────────────
  const [normalizedValues, setNormalizedValues] = useState({ thrNorm: 0, yaw: 0, pitch: 0, roll: 0 });

  const toPWM         = (v: number): number => Math.round(1500 + v * 500);
  const toThrottlePWM = (v: number): number => Math.round(1000 + v * 1000);

  const pwmDisplay = {
    thr:   toThrottlePWM(normalizedValues.thrNorm),
    yaw:   toPWM(normalizedValues.yaw),
    pitch: toPWM(normalizedValues.pitch),
    roll:  toPWM(normalizedValues.roll),
  };

  const pulseAnim    = useRef(new Animated.Value(1)).current;
  const batteryBlink = useRef(new Animated.Value(1)).current;
  const panelX       = useRef(new Animated.Value(-PANEL_WIDTH)).current;
  const backdropOp   = useRef(new Animated.Value(0)).current;

  // ── Panel slide ───────────────────────────────────────────
  const openPanel = () => {
    setPanelOpen(true);
    Animated.parallel([
      Animated.spring(panelX,     { toValue: 0,            useNativeDriver: true, tension: 65, friction: 11 }),
      Animated.timing(backdropOp, { toValue: 1, duration: 250, useNativeDriver: true }),
    ]).start();
  };

  const closePanel = () => {
    Animated.parallel([
      Animated.spring(panelX,     { toValue: -PANEL_WIDTH, useNativeDriver: true, tension: 65, friction: 11 }),
      Animated.timing(backdropOp, { toValue: 0, duration: 200, useNativeDriver: true }),
    ]).start(() => setPanelOpen(false));
  };

  const edgePanResponder = useRef(
    PanResponder.create({
      onMoveShouldSetPanResponder: (_, g) => g.dx > 8 && Math.abs(g.dy) < 40,
      onPanResponderRelease:       (_, g) => { if (g.dx > 30) openPanel(); },
    })
  ).current;

  const panelPanResponder = useRef(
    PanResponder.create({
      onMoveShouldSetPanResponder: (_, g) => g.dx < -8 && Math.abs(g.dy) < 40,
      onPanResponderRelease:       (_, g) => { if (g.dx < -30) closePanel(); },
    })
  ).current;

  // ── Animaciones ───────────────────────────────────────────
  useEffect(() => {
    if (telemetry?.armed) {
      Animated.loop(Animated.sequence([
        Animated.timing(pulseAnim, { toValue: 1.15, duration: 600, useNativeDriver: true }),
        Animated.timing(pulseAnim, { toValue: 1,    duration: 600, useNativeDriver: true }),
      ])).start();
    } else {
      pulseAnim.setValue(1);
    }
  }, [telemetry?.armed]);

  useEffect(() => {
    const pct = Number(telemetry?.battery_remaining ?? 100);
    if (pct < 20) {
      Animated.loop(Animated.sequence([
        Animated.timing(batteryBlink, { toValue: 0.2, duration: 400, useNativeDriver: true }),
        Animated.timing(batteryBlink, { toValue: 1,   duration: 400, useNativeDriver: true }),
      ])).start();
    } else {
      batteryBlink.setValue(1);
    }
  }, [telemetry?.battery_remaining]);

  // ── Handlers joystick ─────────────────────────────────────
  const handleLeftJoystick = (x: number, y: number) => {
    setNormalizedValues(prev => ({ ...prev, thrNorm: y, yaw: x }));
    setJoystick(y, x, undefined, undefined);
  };

  const handleRightJoystick = (x: number, y: number) => {
    setNormalizedValues(prev => ({ ...prev, pitch: y, roll: x }));
    setJoystick(undefined, undefined, y, x);
  };

  // ── Helper ────────────────────────────────────────────────
  const runCommand = async (fn: () => Promise<{ success: boolean; message: string }>) => {
    const result = await fn();
    if (!result.success) Alert.alert('Error', result.message);
    return result;
  };

  const handleTakeoff = () =>
    Alert.alert('Despegue', '¿Despegar a 10 metros?', [
      { text: 'Cancelar', style: 'cancel' },
      { text: 'Despegar', onPress: () => runCommand(() => takeoff(10)) },
    ]);

  const handleEmergency = (action: 'STOP' | 'RTL' | 'LAND') =>
    Alert.alert('⚠️ EMERGENCIA', `¿Ejecutar ${action}?`, [
      { text: 'Cancelar', style: 'cancel' },
      {
        text: 'CONFIRMAR', style: 'destructive',
        onPress: async () => {
          setShowEmergency(false);
          await runCommand(() => emergency(action));
        },
      },
    ]);

  const handleModeChange = (mode: string) => {
    const meta = getMeta(mode);
    const gpsWarning = meta.requiresGPS && Number(telemetry?.satellites ?? 0) < 6
      ? '\n⚠️ GPS insuficiente (< 6 satélites)' : '';
    Alert.alert(`Cambiar modo`, `¿Cambiar a ${mode}?\n${meta.desc}${gpsWarning}`, [
      { text: 'Cancelar', style: 'cancel' },
      {
        text: 'Confirmar',
        onPress: async () => {
          closePanel();
          await runCommand(() => sendCommand('SET_MODE', { mode }));
        },
      },
    ]);
  };

  const handleArmToggle = () => {
    if (telemetry?.armed) {
      Alert.alert('Desarmar', '¿Desarmar el dron?', [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Desarmar', style: 'destructive',
          onPress: async () => { closePanel(); await runCommand(disarmDrone); },
        },
      ]);
    } else {
      Alert.alert('Armar', '¿Armar el dron?', [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Armar',
          onPress: async () => { closePanel(); await runCommand(armDrone); },
        },
      ]);
    }
  };

  const handleAction = (id: string) => {
    const map: Record<string, () => void> = {
      TAKEOFF: () => { handleTakeoff(); closePanel(); },
      LAND: () => Alert.alert('Aterrizar', '¿Iniciar aterrizaje?', [
        { text: 'Cancelar', style: 'cancel' },
        { text: 'Aterrizar', onPress: async () => { closePanel(); await runCommand(land); } },
      ]),
      RTL: () => Alert.alert('RTL', '¿Retornar a casa?', [
        { text: 'Cancelar', style: 'cancel' },
        { text: 'RTL', onPress: async () => { closePanel(); await runCommand(() => sendCommand('SET_MODE', { mode: 'RTL' })); } },
      ]),
      BRAKE: () => { closePanel(); runCommand(() => sendCommand('SET_MODE', { mode: 'BRAKE' })); },
      HOLD_POS: () => {
        const sat = Number(telemetry?.satellites ?? 0);
        if (sat < 6) { Alert.alert('Sin GPS', `Solo ${sat} satélites. LOITER requiere mínimo 6.`); return; }
        closePanel();
        runCommand(() => sendCommand('SET_MODE', { mode: 'LOITER' }));
      },
      REBOOT: () => Alert.alert('Reboot', '¿Reiniciar autopiloto?', [
        { text: 'Cancelar', style: 'cancel' },
        { text: 'Reiniciar', style: 'destructive', onPress: () => runCommand(() => sendCommand('REBOOT', {})) },
      ]),
    };
    map[id]?.();
  };

  // ── Valores telemetría ────────────────────────────────────
  const batPct   = Number(telemetry?.battery_remaining ?? 0);
  const batColor = batPct > 50 ? '#00ff88' : batPct > 20 ? '#ffaa00' : '#ff0044';
  const sat      = Number(telemetry?.satellites ?? 0);
  const satColor = sat >= 8 ? '#00ff88' : sat >= 5 ? '#ffaa00' : '#ff4444';
  const meta     = getMeta(telemetry?.mode ?? 'UNKNOWN');

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor="#050508" />

      <View style={styles.edgeZone} {...edgePanResponder.panHandlers} />

      {/* ══ VIDEO — WebSocket streaming fluido ══ */}
      <View style={styles.videoContainer}>
        {frameUri ? (
          <Image
            source={{ uri: frameUri }}
            style={styles.video}
            resizeMode="cover"
            fadeDuration={0}
          />
        ) : (
          <View style={styles.cameraOverlay}>
            <Text style={styles.cameraOverlayIcon}>📷</Text>
            <Text style={styles.cameraOverlayText}>
              {cameraOk ? 'CARGANDO...' : 'CÁMARA NO DISPONIBLE'}
            </Text>
          </View>
        )}

        <View style={styles.vignette} />

        <TouchableOpacity
          style={[styles.menuBtn, { top: insets.top + 8 }]}
          onPress={openPanel}
          activeOpacity={0.75}
        >
          <View style={styles.menuLine} />
          <View style={[styles.menuLine, { width: 14 }]} />
          <View style={styles.menuLine} />
        </TouchableOpacity>

        <View style={[styles.hudOverlay, { paddingTop: insets.top + 8 }]}>
          <View style={styles.topBar}>
            <View style={[styles.pill, { borderColor: connected ? '#00ff8840' : '#ff004440', marginLeft: 44 }]}>
              <View style={[styles.statusDot, { backgroundColor: connected ? '#00ff88' : '#ff0044' }]} />
              <Text style={[styles.pillText, { color: connected ? '#00ff88' : '#ff4444' }]}>
                {connected ? 'ONLINE' : 'OFFLINE'}
              </Text>
            </View>

            <View style={[styles.modePill, { borderColor: meta.color + '60', backgroundColor: meta.color + '20' }]}>
              <Text style={[styles.modeIcon, { color: meta.color }]}>{meta.icon}</Text>
              <Text style={[styles.modeText, { color: meta.color }]}>{telemetry?.mode ?? 'UNKNOWN'}</Text>
            </View>

            <Animated.View style={[
              styles.pill,
              telemetry?.armed
                ? { borderColor: '#ff004460', backgroundColor: '#ff000020', transform: [{ scale: pulseAnim }] }
                : { borderColor: '#33333360' },
            ]}>
              <Text style={[styles.pillText, { color: telemetry?.armed ? '#ff4466' : '#555' }]}>
                {telemetry?.armed ? '⚡ ARMADO' : '● STAND-BY'}
              </Text>
            </Animated.View>
          </View>

          <View style={styles.telemetryRow}>
            {[
              { label: 'ALT', value: (Number(telemetry?.altitude ?? 0)).toFixed(1), unit: 'm' },
              { label: 'SPD', value: (Number(telemetry?.ground_speed ?? 0)).toFixed(1), unit: 'm/s' },
            ].map(c => (
              <View key={c.label} style={styles.hudChip}>
                <Text style={styles.hudChipLabel}>{c.label}</Text>
                <Text style={styles.hudChipValue}>{c.value}</Text>
                <Text style={styles.hudChipUnit}>{c.unit}</Text>
              </View>
            ))}
            <Animated.View style={[styles.hudChip, { opacity: batteryBlink }]}>
              <Text style={styles.hudChipLabel}>BAT</Text>
              <Text style={[styles.hudChipValue, { color: batColor }]}>{batPct.toFixed(0)}</Text>
              <Text style={[styles.hudChipUnit, { color: batColor }]}>%</Text>
            </Animated.View>
            <View style={styles.hudChip}>
              <Text style={styles.hudChipLabel}>SAT</Text>
              <Text style={[styles.hudChipValue, { color: satColor }]}>{sat}</Text>
              <Text style={[styles.hudChipUnit, { color: satColor }]}>🛰</Text>
            </View>
          </View>

          <View style={styles.crosshairWrap}>
            <View style={styles.crosshairH} />
            <View style={styles.crosshairV} />
            <View style={styles.crosshairCenter} />
            <View style={[styles.corner, styles.cornerTL]} />
            <View style={[styles.corner, styles.cornerTR]} />
            <View style={[styles.corner, styles.cornerBL]} />
            <View style={[styles.corner, styles.cornerBR]} />
          </View>

          <View style={styles.altBar}>
            <View style={[styles.altFill, { height: `${Math.min((Number(telemetry?.altitude ?? 0) / 100) * 100, 100)}%` }]} />
          </View>
        </View>
      </View>

      {/* ══ CONTROLES ══ */}
      <View style={styles.controlsContainer}>
        <View style={styles.buttonRow}>
          {!telemetry?.armed ? (
            <TouchableOpacity style={[styles.controlButton, styles.armButton]} onPress={handleArmToggle} activeOpacity={0.75}>
              <Text style={styles.btnIcon}>⚡</Text>
              <Text style={styles.buttonText}>ARMAR</Text>
            </TouchableOpacity>
          ) : (
            <TouchableOpacity style={[styles.controlButton, styles.disarmButton]} onPress={handleArmToggle} activeOpacity={0.75}>
              <Text style={styles.btnIcon}>🔒</Text>
              <Text style={styles.buttonText}>DESARMAR</Text>
            </TouchableOpacity>
          )}
          <TouchableOpacity style={[styles.controlButton, styles.takeoffButton]} onPress={handleTakeoff} activeOpacity={0.75}>
            <Text style={styles.btnIcon}>▲</Text>
            <Text style={styles.buttonText}>DESPEGUE</Text>
          </TouchableOpacity>
          <TouchableOpacity style={[styles.controlButton, styles.landButton]} onPress={() =>
            Alert.alert('Aterrizar', '¿Iniciar aterrizaje?', [
              { text: 'Cancelar', style: 'cancel' },
              { text: 'Aterrizar', onPress: () => runCommand(land) },
            ])
          } activeOpacity={0.75}>
            <Text style={styles.btnIcon}>▼</Text>
            <Text style={styles.buttonText}>ATERRIZAJE</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.controlButton, styles.emergencyButton, showEmergency && styles.emergencyButtonActive]}
            onPress={() => setShowEmergency(!showEmergency)}
            activeOpacity={0.75}
          >
            <Text style={[styles.btnIcon, { fontSize: 16 }]}>☢</Text>
            <Text style={styles.buttonText}>SOS</Text>
          </TouchableOpacity>
        </View>

        {showEmergency && (
          <View style={styles.emergencyPanel}>
            <View style={styles.emergencyHeader}>
              <View style={styles.emergencyHeaderLine} />
              <Text style={styles.emergencyHeaderText}>ACCIÓN DE EMERGENCIA</Text>
              <View style={styles.emergencyHeaderLine} />
            </View>
            <View style={styles.emergencyButtons}>
              {[
                { label: 'DETENER',    desc: 'Motores OFF',   color: '#ff6600', action: 'STOP' as const, icon: '■' },
                { label: 'RTL',        desc: 'Volver a casa', color: '#ffaa00', action: 'RTL'  as const, icon: '⌂' },
                { label: 'ATERRIZAJE', desc: 'Descenso auto', color: '#ff0044', action: 'LAND' as const, icon: '↓' },
              ].map(e => (
                <TouchableOpacity
                  key={e.action}
                  style={[styles.emergencyOption, { backgroundColor: e.color + '22', borderColor: e.color }]}
                  onPress={() => handleEmergency(e.action)}
                  activeOpacity={0.75}
                >
                  <Text style={[styles.emergencyIcon, { color: e.color }]}>{e.icon}</Text>
                  <Text style={[styles.emergencyText, { color: e.color }]}>{e.label}</Text>
                  <Text style={styles.emergencyDesc}>{e.desc}</Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        )}

        {/* ══ JOYSTICKS ══ */}
        <View style={styles.joystickContainer}>
          <View style={styles.joystickWrapper}>
            <Text style={styles.joystickLabelTop}>THR / YAW</Text>
            <Joystick
              onMove={handleLeftJoystick}
              size={SCREEN_WIDTH * 0.35}
              mode="mode2"
              color="#00ff88"
              resetToBottom={leftJoystickReset}
            />
            <View style={styles.pwmRow}>
              <View style={styles.pwmChip}>
                <Text style={styles.pwmLabel}>THR</Text>
                <Text style={[styles.pwmValue, {
                  color: pwmDisplay.thr >= 1800 ? '#ff4444'
                       : pwmDisplay.thr >= 1500 ? '#00ff88'
                       : pwmDisplay.thr >= 1200 ? '#ffaa00'
                       : '#555'
                }]}>
                  {pwmDisplay.thr}
                </Text>
              </View>
              <View style={styles.pwmChip}>
                <Text style={styles.pwmLabel}>YAW</Text>
                <Text style={[styles.pwmValue, { color: pwmDisplay.yaw !== 1500 ? '#ffcc00' : '#555' }]}>
                  {pwmDisplay.yaw}
                </Text>
              </View>
            </View>
          </View>

          <View style={styles.centerInfo}>
            <Text style={styles.centerInfoLabel}>V/S</Text>
            <Text style={[styles.centerInfoValue, { color: (Number(telemetry?.vertical_speed ?? 0)) >= 0 ? '#00ff88' : '#ff6644' }]}>
              {(Number(telemetry?.vertical_speed ?? 0)).toFixed(1)}
            </Text>
            <Text style={styles.centerInfoUnit}>m/s</Text>
            <View style={styles.centerDivider} />
            <Text style={styles.centerInfoLabel}>YAW</Text>
            <Text style={styles.centerInfoValue2}>{(Number(telemetry?.yaw ?? 0)).toFixed(0)}°</Text>
          </View>

          <View style={styles.joystickWrapper}>
            <Text style={styles.joystickLabelTop}>PITCH / ROLL</Text>
            <Joystick
              onMove={handleRightJoystick}
              size={SCREEN_WIDTH * 0.35}
              mode="both"
              color="#00aaff"
            />
            <View style={styles.pwmRow}>
              <View style={styles.pwmChip}>
                <Text style={styles.pwmLabel}>PIT</Text>
                <Text style={[styles.pwmValue, { color: pwmDisplay.pitch !== 1500 ? '#00aaff' : '#555' }]}>
                  {pwmDisplay.pitch}
                </Text>
              </View>
              <View style={styles.pwmChip}>
                <Text style={styles.pwmLabel}>RLL</Text>
                <Text style={[styles.pwmValue, { color: pwmDisplay.roll !== 1500 ? '#00aaff' : '#555' }]}>
                  {pwmDisplay.roll}
                </Text>
              </View>
            </View>
          </View>
        </View>
      </View>

      {/* ══ BACKDROP ══ */}
      {panelOpen && (
        <Animated.View style={[styles.backdrop, { opacity: backdropOp }]}>
          <TouchableOpacity style={{ flex: 1 }} activeOpacity={1} onPress={closePanel} />
        </Animated.View>
      )}

      {/* ══ PANEL LATERAL ══ */}
      <Animated.View
        style={[styles.sidePanel, { transform: [{ translateX: panelX }] }]}
        {...panelPanResponder.panHandlers}
      >
        <View style={[styles.panelHeader, { paddingTop: insets.top + 12 }]}>
          <View>
            <Text style={styles.panelTitle}>CONTROL</Text>
            <Text style={styles.panelSubtitle}>ArduPilot · {telemetry?.mode ?? '—'}</Text>
          </View>
          <TouchableOpacity onPress={closePanel} style={styles.closeBtn} activeOpacity={0.75}>
            <Text style={styles.closeBtnText}>✕</Text>
          </TouchableOpacity>
        </View>

        <View style={[styles.connBar, {
          backgroundColor: connected ? '#00ff8815' : '#ff004415',
          borderColor:     connected ? '#00ff8830' : '#ff004430',
        }]}>
          <View style={[styles.connDot, { backgroundColor: connected ? '#00ff88' : '#ff0044' }]} />
          <Text style={[styles.connText, { color: connected ? '#00ff88' : '#ff4444' }]}>
            {connected ? 'Conectado al dron' : 'Sin conexión con el dron'}
          </Text>
        </View>

        <ScrollView style={styles.panelScroll} showsVerticalScrollIndicator={false}>
          <Text style={styles.sectionLabel}>ACCIONES RÁPIDAS</Text>

          <TouchableOpacity
            style={[styles.armBigBtn, telemetry?.armed
              ? { backgroundColor: '#ff000018', borderColor: '#ff004460' }
              : { backgroundColor: '#00ff8818', borderColor: '#00ff8860' }]}
            onPress={handleArmToggle}
            activeOpacity={0.75}
          >
            <Text style={[styles.armBigIcon, { color: telemetry?.armed ? '#ff4466' : '#00ff88' }]}>
              {telemetry?.armed ? '🔒' : '⚡'}
            </Text>
            <View style={{ flex: 1 }}>
              <Text style={[styles.armBigLabel, { color: telemetry?.armed ? '#ff4466' : '#00ff88' }]}>
                {telemetry?.armed ? 'DESARMAR DRON' : 'ARMAR DRON'}
              </Text>
              <Text style={styles.armBigDesc}>
                {telemetry?.armed ? 'Armado — toca para desarmar' : 'Stand-by — toca para armar'}
              </Text>
            </View>
          </TouchableOpacity>

          <View style={styles.quickGrid}>
            {[
              { id: 'TAKEOFF',  label: 'DESPEGUE', icon: '▲', color: '#00aaff' },
              { id: 'LAND',     label: 'ATERRIZAR', icon: '▼', color: '#ffaa00' },
              { id: 'RTL',      label: 'RTL',       icon: '⌂', color: '#ff8800' },
              { id: 'BRAKE',    label: 'FRENO',     icon: '⊗', color: '#ff4400' },
              { id: 'HOLD_POS', label: 'HOLD POS',  icon: '⊙', color: '#00ccaa' },
              { id: 'REBOOT',   label: 'REBOOT FC', icon: '↺', color: '#777' },
            ].map(a => (
              <TouchableOpacity
                key={a.id}
                style={[styles.quickBtn, { borderColor: a.color + '40', backgroundColor: a.color + '12' }]}
                onPress={() => handleAction(a.id)}
                activeOpacity={0.75}
              >
                <Text style={[styles.quickBtnIcon, { color: a.color }]}>{a.icon}</Text>
                <Text style={[styles.quickBtnLabel, { color: a.color }]}>{a.label}</Text>
              </TouchableOpacity>
            ))}
          </View>

          {MODE_GROUPS.map(group => (
            <View key={group.label}>
              <Text style={styles.sectionLabel}>{group.label}</Text>
              <View style={styles.modeGroup}>
                {group.modes.map(modeName => {
                  const m = getMeta(modeName);
                  const isActive = (telemetry?.mode ?? '') === modeName;
                  return (
                    <TouchableOpacity
                      key={modeName}
                      style={[styles.modeBtn, {
                        borderColor:     isActive ? m.color        : m.color + '25',
                        backgroundColor: isActive ? m.color + '22' : m.color + '08',
                      }]}
                      onPress={() => handleModeChange(modeName)}
                      activeOpacity={0.75}
                    >
                      <View style={styles.modeBtnLeft}>
                        <Text style={[styles.modeBtnIcon, { color: m.color }]}>{m.icon}</Text>
                        <View>
                          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                            <Text style={[styles.modeBtnName, { color: isActive ? m.color : '#ccc' }]}>
                              {modeName}
                            </Text>
                            {m.requiresGPS && (
                              <View style={styles.gpsBadge}>
                                <Text style={styles.gpsBadgeText}>GPS</Text>
                              </View>
                            )}
                          </View>
                          <Text style={styles.modeBtnDesc}>{m.desc}</Text>
                        </View>
                      </View>
                      {isActive && <View style={[styles.activeModeDot, { backgroundColor: m.color }]} />}
                    </TouchableOpacity>
                  );
                })}
              </View>
            </View>
          ))}

          <Text style={styles.sectionLabel}>BATERÍA</Text>
          <View style={styles.batteryPanel}>
            <View style={styles.batteryTop}>
              <Text style={[styles.batteryPct, { color: batColor }]}>{batPct.toFixed(0)}%</Text>
              <Text style={[styles.batteryV, { color: batColor + 'aa' }]}>
                {(Number(telemetry?.battery_voltage ?? 0)).toFixed(2)} V
              </Text>
            </View>
            <View style={styles.batteryBar}>
              <View style={[styles.batteryFill, { width: `${batPct}%`, backgroundColor: batColor }]} />
            </View>
          </View>

          <View style={{ height: 32 }} />
        </ScrollView>
      </Animated.View>
    </SafeAreaView>
  );
};

// ══════════════════════════════════════════════════════════════════════════════
const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#050508' },
  edgeZone:  { position: 'absolute', left: 0, top: 0, bottom: 0, width: 18, zIndex: 10 },

  videoContainer: { width: SCREEN_WIDTH, height: SCREEN_HEIGHT * 0.48, backgroundColor: '#000' },
  video:          { width: '100%', height: '100%' },
  vignette:       { position: 'absolute', width: '100%', height: '100%', borderWidth: 40, borderColor: 'rgba(0,0,0,0.6)', pointerEvents: 'none' },
  hudOverlay:     { position: 'absolute', width: '100%', height: '100%', padding: 12, pointerEvents: 'none' },

  cameraOverlay:     { width: '100%', height: '100%', justifyContent: 'center', alignItems: 'center', backgroundColor: '#000', gap: 8 },
  cameraOverlayIcon: { fontSize: 32 },
  cameraOverlayText: { color: '#333', fontSize: 11, fontWeight: '800', letterSpacing: 2 },

  menuBtn: {
    position: 'absolute', left: 12,
    width: 34, height: 34,
    backgroundColor: 'rgba(0,0,0,0.75)',
    borderRadius: 8, borderWidth: 1, borderColor: '#00ff8830',
    justifyContent: 'center', alignItems: 'center', gap: 4, zIndex: 5,
  },
  menuLine: { width: 18, height: 2, backgroundColor: '#00ff88', borderRadius: 1 },

  topBar:   { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  pill:     { flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(0,0,0,0.75)', paddingHorizontal: 10, paddingVertical: 5, borderRadius: 20, borderWidth: 1, gap: 6 },
  statusDot:{ width: 6, height: 6, borderRadius: 3 },
  pillText: { fontSize: 10, fontWeight: '800', letterSpacing: 1, color: '#aaa' },
  modePill: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 14, paddingVertical: 6, borderRadius: 20, borderWidth: 1.5, gap: 6, backgroundColor: 'rgba(0,0,0,0.6)' },
  modeIcon: { fontSize: 14 },
  modeText: { fontSize: 12, fontWeight: '900', letterSpacing: 1.5 },

  telemetryRow: { flexDirection: 'row', justifyContent: 'center', gap: 8, marginTop: 4 },
  hudChip:      { flexDirection: 'row', alignItems: 'baseline', backgroundColor: 'rgba(0,0,0,0.72)', borderRadius: 8, paddingHorizontal: 10, paddingVertical: 5, gap: 3, borderWidth: 1, borderColor: 'rgba(0,255,136,0.12)' },
  hudChipLabel: { color: '#555', fontSize: 9, fontWeight: '700', letterSpacing: 0.5, marginRight: 2 },
  hudChipValue: { color: '#00ff88', fontSize: 15, fontWeight: '900' },
  hudChipUnit:  { color: '#446', fontSize: 9, fontWeight: '600' },

  crosshairWrap:   { position: 'absolute', top: '50%', left: '50%', width: 60, height: 60, marginLeft: -30, marginTop: -30, justifyContent: 'center', alignItems: 'center' },
  crosshairH:      { position: 'absolute', width: 60, height: 1, backgroundColor: 'rgba(0,255,136,0.5)' },
  crosshairV:      { position: 'absolute', width: 1, height: 60, backgroundColor: 'rgba(0,255,136,0.5)' },
  crosshairCenter: { width: 6, height: 6, borderRadius: 3, backgroundColor: '#00ff88' },
  corner:          { position: 'absolute', width: 10, height: 10, borderColor: 'rgba(0,255,136,0.8)' },
  cornerTL:        { top: 0, left: 0, borderTopWidth: 2, borderLeftWidth: 2 },
  cornerTR:        { top: 0, right: 0, borderTopWidth: 2, borderRightWidth: 2 },
  cornerBL:        { bottom: 0, left: 0, borderBottomWidth: 2, borderLeftWidth: 2 },
  cornerBR:        { bottom: 0, right: 0, borderBottomWidth: 2, borderRightWidth: 2 },

  altBar:  { position: 'absolute', right: 14, top: '20%', bottom: '15%', width: 4, backgroundColor: 'rgba(0,255,136,0.1)', borderRadius: 2, justifyContent: 'flex-end', overflow: 'hidden' },
  altFill: { width: '100%', backgroundColor: '#00ff88', borderRadius: 2, minHeight: 4 },

  controlsContainer: { flex: 1, paddingHorizontal: 12, paddingTop: 10, paddingBottom: 4 },
  buttonRow:         { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 8, gap: 6 },
  controlButton:     { flex: 1, paddingVertical: 9, paddingHorizontal: 4, borderRadius: 10, alignItems: 'center', justifyContent: 'center', borderWidth: 1, gap: 2 },
  btnIcon:           { fontSize: 13, lineHeight: 16 },
  armButton:         { backgroundColor: '#00ff8818', borderColor: '#00ff8860' },
  disarmButton:      { backgroundColor: '#44444418', borderColor: '#66666660' },
  takeoffButton:     { backgroundColor: '#00aaff18', borderColor: '#00aaff60' },
  landButton:        { backgroundColor: '#ffaa0018', borderColor: '#ffaa0060' },
  emergencyButton:   { backgroundColor: '#ff004418', borderColor: '#ff004460' },
  emergencyButtonActive: { backgroundColor: '#ff004430', borderColor: '#ff0044' },
  buttonText:        { color: '#ccc', fontSize: 9, fontWeight: '800', letterSpacing: 0.5 },

  emergencyPanel:     { marginBottom: 8, padding: 10, backgroundColor: '#0d0005', borderRadius: 12, borderWidth: 1, borderColor: '#ff004440' },
  emergencyHeader:    { flexDirection: 'row', alignItems: 'center', marginBottom: 8, gap: 8 },
  emergencyHeaderLine:{ flex: 1, height: 1, backgroundColor: '#ff004440' },
  emergencyHeaderText:{ color: '#ff0044', fontSize: 9, fontWeight: '800', letterSpacing: 2 },
  emergencyButtons:   { flexDirection: 'row', gap: 8 },
  emergencyOption:    { flex: 1, paddingVertical: 10, borderRadius: 10, alignItems: 'center', borderWidth: 1, gap: 2 },
  emergencyIcon:      { fontSize: 18, lineHeight: 22 },
  emergencyText:      { fontSize: 10, fontWeight: '900', letterSpacing: 0.5 },
  emergencyDesc:      { fontSize: 8, color: '#666', fontWeight: '600' },

  joystickContainer: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', flex: 1 },
  joystickWrapper:   { alignItems: 'center', gap: 6 },
  joystickLabelTop:  { color: '#444', fontSize: 9, fontWeight: '700', letterSpacing: 1.5 },
  pwmRow:   { flexDirection: 'row', gap: 6, marginTop: 6 },
  pwmChip:  { alignItems: 'center', backgroundColor: '#0a0a14', borderRadius: 6, paddingHorizontal: 8, paddingVertical: 4, borderWidth: 1, borderColor: '#1a1a2a' },
  pwmLabel: { color: '#333', fontSize: 7, fontWeight: '800', letterSpacing: 1 },
  pwmValue: { fontSize: 12, fontWeight: '900', letterSpacing: 0.5 },
  centerInfo:        { alignItems: 'center', gap: 2 },
  centerInfoLabel:   { color: '#444', fontSize: 9, fontWeight: '700', letterSpacing: 1 },
  centerInfoValue:   { color: '#00ff88', fontSize: 16, fontWeight: '900' },
  centerInfoUnit:    { color: '#333', fontSize: 8, fontWeight: '600' },
  centerDivider:     { width: 24, height: 1, backgroundColor: '#222', marginVertical: 4 },
  centerInfoValue2:  { color: '#888', fontSize: 14, fontWeight: '800' },

  backdrop: { position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.6)', zIndex: 20 },

  sidePanel: {
    position: 'absolute', top: 0, bottom: 0, left: 0,
    width: PANEL_WIDTH,
    backgroundColor: '#07070d',
    borderRightWidth: 1, borderRightColor: '#00ff8820',
    zIndex: 30,
  },
  panelHeader:   { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 18, paddingTop: 18, paddingBottom: 14, borderBottomWidth: 1, borderBottomColor: '#0d0d1a' },
  panelTitle:    { color: '#fff', fontSize: 18, fontWeight: '900', letterSpacing: 2 },
  panelSubtitle: { color: '#444', fontSize: 10, fontWeight: '600', letterSpacing: 1, marginTop: 2 },
  closeBtn:      { width: 30, height: 30, borderRadius: 15, backgroundColor: '#1a1a2a', justifyContent: 'center', alignItems: 'center' },
  closeBtnText:  { color: '#666', fontSize: 14, fontWeight: '700' },

  connBar:  { flexDirection: 'row', alignItems: 'center', marginHorizontal: 14, marginTop: 10, marginBottom: 4, paddingHorizontal: 12, paddingVertical: 8, borderRadius: 10, borderWidth: 1, gap: 8 },
  connDot:  { width: 6, height: 6, borderRadius: 3 },
  connText: { fontSize: 11, fontWeight: '700', letterSpacing: 0.5 },

  panelScroll:  { flex: 1, paddingHorizontal: 14 },
  sectionLabel: { color: '#2a2a3a', fontSize: 9, fontWeight: '800', letterSpacing: 2, marginTop: 18, marginBottom: 8 },

  armBigBtn:   { flexDirection: 'row', alignItems: 'center', padding: 14, borderRadius: 12, borderWidth: 1.5, marginBottom: 10, gap: 12 },
  armBigIcon:  { fontSize: 26 },
  armBigLabel: { fontSize: 15, fontWeight: '900', letterSpacing: 1 },
  armBigDesc:  { color: '#555', fontSize: 10, fontWeight: '600', marginTop: 2 },

  quickGrid:     { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  quickBtn:      { width: '30.5%', aspectRatio: 1.2, borderRadius: 10, borderWidth: 1, justifyContent: 'center', alignItems: 'center', gap: 4 },
  quickBtnIcon:  { fontSize: 20 },
  quickBtnLabel: { fontSize: 8, fontWeight: '800', letterSpacing: 0.5, textAlign: 'center' },

  modeGroup:      { gap: 6, marginBottom: 4 },
  modeBtn:        { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 12, paddingVertical: 10, borderRadius: 10, borderWidth: 1 },
  modeBtnLeft:    { flexDirection: 'row', alignItems: 'center', gap: 10 },
  modeBtnIcon:    { fontSize: 18, width: 24, textAlign: 'center' },
  modeBtnName:    { fontSize: 13, fontWeight: '800', letterSpacing: 0.5 },
  modeBtnDesc:    { color: '#444', fontSize: 9, fontWeight: '600', marginTop: 2 },
  gpsBadge:       { backgroundColor: '#00aaff20', borderWidth: 1, borderColor: '#00aaff40', borderRadius: 4, paddingHorizontal: 4, paddingVertical: 1 },
  gpsBadgeText:   { color: '#00aaff', fontSize: 7, fontWeight: '800', letterSpacing: 0.5 },
  activeModeDot:  { width: 8, height: 8, borderRadius: 4 },

  batteryPanel: { backgroundColor: '#0a0a14', borderRadius: 12, padding: 14, borderWidth: 1, borderColor: '#1a1a2a' },
  batteryTop:   { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 10 },
  batteryPct:   { fontSize: 32, fontWeight: '900' },
  batteryV:     { fontSize: 16, fontWeight: '700' },
  batteryBar:   { height: 8, backgroundColor: '#0d0d1a', borderRadius: 4, overflow: 'hidden' },
  batteryFill:  { height: '100%', borderRadius: 4 },
});
