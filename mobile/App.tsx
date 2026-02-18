import React, { useRef } from 'react';
import { View, Dimensions, StyleSheet, FlatList } from 'react-native';
import { DroneProvider } from './src/context/DroneContext';
import { DroneControlScreen } from './src/screens/DroneControlScreen';
import { TelemetryScreen } from './src/screens/TelemetryScreen';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

const SCREENS = [
  { id: 'control', component: DroneControlScreen },
  { id: 'telemetry', component: TelemetryScreen },
];

export default function App() {
  const flatListRef = useRef<FlatList>(null);

  const renderScreen = ({ item }: { item: typeof SCREENS[0] }) => {
    const ScreenComponent = item.component;
    return (
      <View style={styles.screen}>
        <ScreenComponent />
      </View>
    useEffect(() => {
      /*
        Configuración automática de backend según plataforma y entorno:
        - Emulador Android: 10.0.2.2
        - Emulador iOS: localhost
        - Dispositivo físico: IP de WSL2 (ajusta si cambia)
      */
      const WSL2_IP = '172.21.171.70'; // Cambia si tu WSL2 IP cambia

      let host = WSL2_IP;
      if (Platform.OS === 'android') {
        host = '10.0.2.2';
      } else if (Platform.OS === 'ios') {
        host = 'localhost';
      }

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
