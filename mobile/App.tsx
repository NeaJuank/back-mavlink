/**
 * Sample React Native App
 * https://github.com/facebook/react-native
 *
 * @format
 */

import React, { useEffect, useState } from 'react';
import { StatusBar, StyleSheet, Text, View, ScrollView } from 'react-native';
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
    const ws = new WebSocket('ws://10.0.2.2:8000/ws/telemetry'); // Para emulador Android

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setTelemetry(data);
    };

    ws.onopen = () => {
      console.log('Connected to WebSocket');
    };

    ws.onclose = () => {
      console.log('WebSocket closed');
    };

    return () => {
      ws.close();
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
