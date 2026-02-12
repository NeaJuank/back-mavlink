/**
 * Sample React Native App
 * https://github.com/facebook/react-native
 *
 * @format
 */

import React, { useEffect, useState } from 'react';
import { StatusBar, StyleSheet, Text, View, ScrollView, Platform, useColorScheme } from 'react-native';
import {
  SafeAreaProvider,
  useSafeAreaInsets,
} from 'react-native-safe-area-context';

function App() {
  const isDarkMode = useColorScheme() === 'dark';

  return (
    <SafeAreaProvider>
      <StatusBar barStyle={isDarkMode ? 'light-content' : 'dark-content'} />
      <AppContent />
    </SafeAreaProvider>
  );
}

function AppContent() {
  const safeAreaInsets = useSafeAreaInsets();
  const [telemetry, setTelemetry] = useState<any>({});

  useEffect(() => {
    // Construir URL del WebSocket según entorno. Ajusta BACKEND_HOST para
    // dispositivos reales (ej. '192.168.1.10'). Si no se reemplaza el marcador,
    // usamos telemetría simulada para poder ver la app sin backend.
    const BACKEND_HOST = '<REPLACE_WITH_BACKEND_HOST_OR_IP>';

    const useMock = BACKEND_HOST === '<REPLACE_WITH_BACKEND_HOST_OR_IP>';

    if (useMock) {
      // Telemetría simulada para preview rápido
      let counter = 0;
      const iv = setInterval(() => {
        counter += 1;
        setTelemetry({
          connected: true,
          altitude: 1.0 + Math.sin(counter / 5) * 0.5,
          speed: 2.0 + Math.abs(Math.cos(counter / 5)),
          climb_rate: Math.sin(counter / 3) * 0.1,
          gps: { lat: 4.123 + counter * 0.00001, lon: -74.456 - counter * 0.00001, alt: 100 },
          battery: { voltage: 12.3, current: 0.5, remaining: Math.max(0, 100 - (counter % 100)) }
        });
      }, 1000);

      return () => clearInterval(iv);
    }

    const host = Platform.OS === 'android' ? '10.0.2.2' : 'localhost';
    const wsUrl = `ws://${host}:8000/api/ws/telemetry`;
    const ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setTelemetry(data);
    };

    ws.onopen = () => {
      console.log('Connected to WebSocket', wsUrl);
    };

    ws.onclose = () => {
      console.log('WebSocket closed');
    };

    return () => {
      try {
        ws.close();
      } catch (e) {}
    };
  }, []);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Drone Telemetry Mobile</Text>
      <ScrollView>
        <Text style={styles.data}>{JSON.stringify(telemetry, null, 2)}</Text>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 20,
  },
  data: {
    fontSize: 16,
  },
});

export default App;
