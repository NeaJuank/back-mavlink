import React, { useState } from 'react';
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
} from 'react-native';
import { Joystick } from '../components/Joystick';
import { useDrone } from '../context/DroneContext';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');
const API_URL = 'http://192.168.1.100:8000'; // ⚠️ Cambiar a IP de Raspberry Pi

export const DroneControlScreen: React.FC = () => {
  const { telemetry, connected, armDrone, disarmDrone, takeoff, land, emergency, setJoystick } =
    useDrone();

  const [videoUrl] = useState(`${API_URL}/api/camera/stream`);
  const [showEmergency, setShowEmergency] = useState(false);

  const handleLeftJoystick = (x: number, y: number) => {
    const throttle = (y + 1) / 2;
    const yaw = x;
    setJoystick(throttle, yaw, undefined, undefined);
  };

  const handleRightJoystick = (x: number, y: number) => {
    const roll = x;
    const pitch = y;
    setJoystick(undefined, undefined, pitch, roll);
  };

  const handleTakeoff = () => {
    Alert.alert(
      'Despegue',
      '¿Despegar a 10 metros?',
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Despegar',
          onPress: () => takeoff(10),
          style: 'default',
        },
      ]
    );
  };

  const handleEmergency = (action: 'STOP' | 'RTL' | 'LAND') => {
    Alert.alert(
      '⚠️ EMERGENCIA',
      `¿Ejecutar ${action}?`,
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'CONFIRMAR',
          onPress: () => {
            emergency(action);
            setShowEmergency(false);
          },
          style: 'destructive',
        },
      ]
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor="#0a0a0f" />

      {/* Video Stream */}
      <View style={styles.videoContainer}>
        <Image
          source={{ uri: videoUrl }}
          style={styles.video}
          resizeMode="cover"
        />

        {/* HUD Overlay */}
        <View style={styles.hudOverlay}>
          {/* Top Bar */}
          <View style={styles.topBar}>
            <View style={styles.statusBadge}>
              <View style={[styles.statusDot, { backgroundColor: connected ? '#00ff88' : '#ff0044' }]} />
              <Text style={styles.statusText}>{connected ? 'CONECTADO' : 'DESCONECTADO'}</Text>
            </View>

            <View style={styles.modeBadge}>
              <Text style={styles.modeText}>{telemetry.mode}</Text>
            </View>

            <View style={[styles.armedBadge, { backgroundColor: telemetry.armed ? '#ff0044' : '#444' }]}>
              <Text style={styles.armedText}>{telemetry.armed ? 'ARMADO' : 'DESARMADO'}</Text>
            </View>
          </View>

          {/* Telemetría */}
          <View style={styles.telemetryHUD}>
            <View style={styles.hudItem}>
              <Text style={styles.hudLabel}>ALT</Text>
              <Text style={styles.hudValue}>{telemetry.altitude.toFixed(1)}m</Text>
            </View>

            <View style={styles.hudItem}>
              <Text style={styles.hudLabel}>SPD</Text>
              <Text style={styles.hudValue}>{telemetry.ground_speed.toFixed(1)}m/s</Text>
            </View>

            <View style={styles.hudItem}>
              <Text style={styles.hudLabel}>BAT</Text>
              <Text
                style={[
                  styles.hudValue,
                  { color: telemetry.battery_remaining > 30 ? '#00ff88' : '#ff0044' },
                ]}
              >
                {telemetry.battery_remaining.toFixed(0)}%
              </Text>
            </View>

            <View style={styles.hudItem}>
              <Text style={styles.hudLabel}>SAT</Text>
              <Text style={styles.hudValue}>{telemetry.satellites}</Text>
            </View>
          </View>

          {/* Crosshair */}
          <View style={styles.crosshair}>
            <View style={styles.crosshairH} />
            <View style={styles.crosshairV} />
            <View style={styles.crosshairCenter} />
          </View>
        </View>
      </View>

      {/* Controles */}
      <View style={styles.controlsContainer}>
        {/* Botones */}
        <View style={styles.buttonRow}>
          {!telemetry.armed ? (
            <TouchableOpacity style={[styles.controlButton, styles.armButton]} onPress={armDrone}>
              <Text style={styles.buttonText}>ARMAR</Text>
            </TouchableOpacity>
          ) : (
            <TouchableOpacity style={[styles.controlButton, styles.disarmButton]} onPress={disarmDrone}>
              <Text style={styles.buttonText}>DESARMAR</Text>
            </TouchableOpacity>
          )}

          <TouchableOpacity style={[styles.controlButton, styles.takeoffButton]} onPress={handleTakeoff}>
            <Text style={styles.buttonText}>DESPEGUE</Text>
          </TouchableOpacity>

          <TouchableOpacity style={[styles.controlButton, styles.landButton]} onPress={land}>
            <Text style={styles.buttonText}>ATERRIZAJE</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.controlButton, styles.emergencyButton]}
            onPress={() => setShowEmergency(!showEmergency)}
          >
            <Text style={styles.buttonText}>⚠️</Text>
          </TouchableOpacity>
        </View>

        {/* Panel de emergencia */}
        {showEmergency && (
          <View style={styles.emergencyPanel}>
            <TouchableOpacity
              style={[styles.emergencyOption, { backgroundColor: '#ff6600' }]}
              onPress={() => handleEmergency('STOP')}
            >
              <Text style={styles.emergencyText}>DETENER</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={[styles.emergencyOption, { backgroundColor: '#ffaa00' }]}
              onPress={() => handleEmergency('RTL')}
            >
              <Text style={styles.emergencyText}>RTL</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={[styles.emergencyOption, { backgroundColor: '#ff0044' }]}
              onPress={() => handleEmergency('LAND')}
            >
              <Text style={styles.emergencyText}>ATERRIZAJE</Text>
            </TouchableOpacity>
          </View>
        )}

        {/* Joysticks */}
        <View style={styles.joystickContainer}>
          <View style={styles.joystickWrapper}>
            <Joystick
              onMove={handleLeftJoystick}
              size={SCREEN_WIDTH * 0.35}
              mode="both"
              color="#00ff88"
            />
            <Text style={styles.joystickLabel}>THROTTLE / YAW</Text>
          </View>

          <View style={styles.joystickWrapper}>
            <Joystick
              onMove={handleRightJoystick}
              size={SCREEN_WIDTH * 0.35}
              mode="both"
              color="#00aaff"
            />
            <Text style={styles.joystickLabel}>PITCH / ROLL</Text>
          </View>
        </View>
      </View>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0a0a0f',
  },
  videoContainer: {
    width: SCREEN_WIDTH,
    height: SCREEN_HEIGHT * 0.5,
    backgroundColor: '#000',
    position: 'relative',
  },
  video: {
    width: '100%',
    height: '100%',
  },
  hudOverlay: {
    position: 'absolute',
    width: '100%',
    height: '100%',
    padding: 15,
  },
  topBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: 6,
  },
  statusText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '700',
  },
  modeBadge: {
    backgroundColor: 'rgba(0, 170, 255, 0.8)',
    paddingHorizontal: 16,
    paddingVertical: 6,
    borderRadius: 20,
  },
  modeText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '800',
  },
  armedBadge: {
    paddingHorizontal: 16,
    paddingVertical: 6,
    borderRadius: 20,
  },
  armedText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '800',
  },
  telemetryHUD: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginTop: 20,
  },
  hudItem: {
    alignItems: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 10,
    minWidth: 70,
  },
  hudLabel: {
    color: '#888',
    fontSize: 10,
    fontWeight: '600',
    marginBottom: 2,
  },
  hudValue: {
    color: '#00ff88',
    fontSize: 16,
    fontWeight: '800',
  },
  crosshair: {
    position: 'absolute',
    top: '50%',
    left: '50%',
    transform: [{ translateX: -25 }, { translateY: -25 }],
  },
  crosshairH: {
    position: 'absolute',
    width: 50,
    height: 2,
    backgroundColor: '#00ff88',
    opacity: 0.6,
  },
  crosshairV: {
    position: 'absolute',
    width: 2,
    height: 50,
    backgroundColor: '#00ff88',
    opacity: 0.6,
    left: 24,
  },
  crosshairCenter: {
    position: 'absolute',
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#00ff88',
    left: 21,
    top: 21,
  },
  controlsContainer: {
    flex: 1,
    padding: 15,
  },
  buttonRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 15,
  },
  controlButton: {
    flex: 1,
    paddingVertical: 12,
    marginHorizontal: 4,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  armButton: {
    backgroundColor: '#00ff88',
  },
  disarmButton: {
    backgroundColor: '#888',
  },
  takeoffButton: {
    backgroundColor: '#00aaff',
  },
  landButton: {
    backgroundColor: '#ffaa00',
  },
  emergencyButton: {
    backgroundColor: '#ff0044',
  },
  buttonText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '800',
  },
  emergencyPanel: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginBottom: 15,
    padding: 10,
    backgroundColor: 'rgba(255, 0, 68, 0.1)',
    borderRadius: 10,
    borderWidth: 2,
    borderColor: '#ff0044',
  },
  emergencyOption: {
    flex: 1,
    paddingVertical: 10,
    marginHorizontal: 5,
    borderRadius: 8,
    alignItems: 'center',
  },
  emergencyText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '800',
  },
  joystickContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 10,
    flex: 1,
  },
  joystickWrapper: {
    alignItems: 'center',
  },
  joystickLabel: {
    color: '#888',
    fontSize: 10,
    fontWeight: '600',
    marginTop: 10,
    textAlign: 'center',
  },
});
