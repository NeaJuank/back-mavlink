/**
 * Sample React Native App
 * https://github.com/facebook/react-native
 *
 * @format
 */

import React, { useEffect, useState } from 'react';
import { StatusBar, StyleSheet, Text, View, ScrollView, Platform } from 'react-native';
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
    // dispositivos reales (ej. '192.168.1.10').
    // - Android emulator: use 10.0.2.2 to reach host localhost
    // - iOS simulator: use localhost
    // - Physical device: set BACKEND_HOST to the dev machine or Pi IP on the LAN
    const BACKEND_HOST = '<REPLACE_WITH_BACKEND_HOST_OR_IP>';

    const host =
      BACKEND_HOST && BACKEND_HOST !== '<REPLACE_WITH_BACKEND_HOST_OR_IP>'
        ? BACKEND_HOST
        : Platform.OS === 'android'
        ? '10.0.2.2'
        : 'localhost';

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
