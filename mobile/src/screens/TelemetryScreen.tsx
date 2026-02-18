import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Dimensions,
  SafeAreaView,
} from 'react-native';
import { useDrone } from '../context/DroneContext';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

export const TelemetryScreen: React.FC = () => {
  const { telemetry, connected } = useDrone();
  // Valores por defecto por si el backend envía datos incompletos
  const alt = Number(telemetry?.altitude ?? 0);
  const lat = Number(telemetry?.latitude ?? 0);
  const lon = Number(telemetry?.longitude ?? 0);
  const sat = Number(telemetry?.satellites ?? 0);
  const hdop = Number(telemetry?.hdop ?? 0);
  const roll = Number(telemetry?.roll ?? 0);
  const pitch = Number(telemetry?.pitch ?? 0);
  const yaw = Number(telemetry?.yaw ?? 0);
  const gs = Number(telemetry?.ground_speed ?? 0);
  const vs = Number(telemetry?.vertical_speed ?? 0);
  const batV = Number(telemetry?.battery_voltage ?? 0);
  const batPct = Number(telemetry?.battery_remaining ?? 0);
  const mode = String(telemetry?.mode ?? 'UNKNOWN');
  const armed = Boolean(telemetry?.armed);

  const renderDataCard = (
    title: string,
    value: string | number,
    unit: string,
    color: string = '#00ff88'
  ) => (
    <View style={styles.dataCard}>
      <Text style={styles.dataLabel}>{title}</Text>
      <View style={styles.dataValueContainer}>
        <Text style={[styles.dataValue, { color }]}>{value}</Text>
        <Text style={styles.dataUnit}>{unit}</Text>
      </View>
    </View>
  );

  const renderDataRow = (
    label: string,
    value: string | number,
    unit: string = '',
    color: string = '#00ff88'
  ) => (
    <View style={styles.dataRow}>
      <Text style={styles.rowLabel}>{label}</Text>
      <View style={styles.rowValueContainer}>
        <Text style={[styles.rowValue, { color }]}>
          {value} {unit}
        </Text>
      </View>
    </View>
  );

  const getBatteryColor = (percentage: number) => {
    if (percentage > 50) return '#00ff88';
    if (percentage > 20) return '#ffaa00';
    return '#ff0044';
  };

  const getSignalColor = (satellites: number) => {
    if (satellites >= 8) return '#00ff88';
    if (satellites >= 5) return '#ffaa00';
    return '#ff0044';
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.gradient}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.title}>TELEMETRÍA</Text>
          <View style={[styles.connectionStatus, { backgroundColor: connected ? '#00ff88' : '#ff0044' }]}>
            <Text style={styles.connectionText}>{connected ? 'ONLINE' : 'OFFLINE'}</Text>
          </View>
        </View>

        <ScrollView
          style={styles.scrollView}
          showsVerticalScrollIndicator={false}
        >
          {/* Estado General */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>ESTADO GENERAL</Text>
            <View style={styles.cardGrid}>
              {renderDataCard(
                'MODO',
                mode,
                '',
                '#00aaff'
              )}
              {renderDataCard(
                'ESTADO',
                armed ? 'ARMADO' : 'DESARMADO',
                '',
                armed ? '#ff0044' : '#888'
              )}
            </View>
          </View>

          {/* Posición */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>POSICIÓN & NAVEGACIÓN</Text>
            <View style={styles.dataContainer}>
              {renderDataRow('Altitud', alt.toFixed(2), 'm')}
              {renderDataRow('Latitud', lat.toFixed(6), '°')}
              {renderDataRow('Longitud', lon.toFixed(6), '°')}
              {renderDataRow(
                'Satélites',
                sat,
                '',
                getSignalColor(sat)
              )}
              {renderDataRow('HDOP', hdop.toFixed(2), '')}
            </View>
          </View>

          {/* Actitud */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>ACTITUD</Text>
            <View style={styles.cardGrid}>
              {renderDataCard('ROLL', roll.toFixed(1), '°', '#00aaff')}
              {renderDataCard('PITCH', pitch.toFixed(1), '°', '#00ff88')}
              {renderDataCard('YAW', yaw.toFixed(1), '°', '#ffaa00')}
            </View>
          </View>

          {/* Velocidad */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>VELOCIDAD</Text>
            <View style={styles.cardGrid}>
              {renderDataCard(
                'HORIZONTAL',
                gs.toFixed(2),
                'm/s',
                '#00ff88'
              )}
              {renderDataCard(
                'VERTICAL',
                vs.toFixed(2),
                'm/s',
                vs >= 0 ? '#00ff88' : '#ff0044'
              )}
            </View>
          </View>

          {/* Batería */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>BATERÍA</Text>
            <View style={styles.batteryContainer}>
              <View style={styles.batteryBar}>
                <View
                  style={[
                    styles.batteryFill,
                    {
                      width: `${batPct}%`,
                      backgroundColor: getBatteryColor(batPct),
                    },
                  ]}
                />
              </View>
              <Text
                style={[
                  styles.batteryPercentage,
                  { color: getBatteryColor(batPct) },
                ]}
              >
                {batPct.toFixed(0)}%
              </Text>
            </View>
            <View style={styles.dataContainer}>
              {renderDataRow(
                'Voltaje',
                batV.toFixed(2),
                'V',
                getBatteryColor(batPct)
              )}
              {renderDataRow(
                'Restante',
                batPct.toFixed(1),
                '%',
                getBatteryColor(batPct)
              )}
            </View>
          </View>

          <View style={{ height: 30 }} />
        </ScrollView>
      </View>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0a0a0f',
  },
  gradient: {
    flex: 1,
    backgroundColor: '#0a0a0f',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    paddingBottom: 15,
  },
  title: {
    fontSize: 28,
    fontWeight: '900',
    color: '#fff',
    letterSpacing: 2,
  },
  connectionStatus: {
    paddingHorizontal: 16,
    paddingVertical: 6,
    borderRadius: 20,
  },
  connectionText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '800',
  },
  scrollView: {
    flex: 1,
    paddingHorizontal: 20,
  },
  section: {
    marginBottom: 25,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: '800',
    color: '#888',
    letterSpacing: 1.5,
    marginBottom: 12,
  },
  cardGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  dataCard: {
    backgroundColor: 'rgba(20, 20, 30, 0.8)',
    borderRadius: 15,
    padding: 15,
    marginBottom: 12,
    minWidth: (SCREEN_WIDTH - 55) / 2,
    borderWidth: 1,
    borderColor: 'rgba(0, 255, 136, 0.2)',
  },
  dataLabel: {
    fontSize: 12,
    fontWeight: '700',
    color: '#888',
    marginBottom: 8,
    letterSpacing: 1,
  },
  dataValueContainer: {
    flexDirection: 'row',
    alignItems: 'baseline',
  },
  dataValue: {
    fontSize: 24,
    fontWeight: '900',
    marginRight: 6,
  },
  dataUnit: {
    fontSize: 14,
    fontWeight: '600',
    color: '#666',
  },
  dataContainer: {
    backgroundColor: 'rgba(20, 20, 30, 0.6)',
    borderRadius: 12,
    padding: 12,
    borderWidth: 1,
    borderColor: 'rgba(0, 255, 136, 0.1)',
  },
  dataRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.05)',
  },
  rowLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#aaa',
  },
  rowValueContainer: {
    flexDirection: 'row',
    alignItems: 'baseline',
  },
  rowValue: {
    fontSize: 16,
    fontWeight: '800',
  },
  batteryContainer: {
    marginBottom: 15,
  },
  batteryBar: {
    height: 40,
    backgroundColor: 'rgba(20, 20, 30, 0.8)',
    borderRadius: 20,
    overflow: 'hidden',
    borderWidth: 2,
    borderColor: 'rgba(0, 255, 136, 0.3)',
    marginBottom: 10,
  },
  batteryFill: {
    height: '100%',
    borderRadius: 18,
  },
  batteryPercentage: {
    fontSize: 32,
    fontWeight: '900',
    textAlign: 'center',
  },
});
