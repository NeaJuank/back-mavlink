import React, { useRef } from 'react';
import {
  View,
  Dimensions,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  Text,
} from 'react-native';
import { DroneProvider } from './src/context/DroneContext';
import { DroneControlScreen } from './src/screens/DroneControlScreen';
import { TelemetryScreen } from './src/screens/TelemetryScreen';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

const SCREENS = [
  { id: 'control', title: 'Control', component: DroneControlScreen },
  { id: 'telemetry', title: 'Telemetría', component: TelemetryScreen },
];

export default function App() {
  const flatListRef = useRef<FlatList>(null);

  const renderScreen = ({ item }: { item: (typeof SCREENS)[0] }) => {
    const ScreenComponent = item.component;
    return (
      <View style={styles.screen}>
        <ScreenComponent />
      </View>
    );
  };

  return (
    <DroneProvider>
      <View style={styles.tabs}>
        {SCREENS.map((screen, index) => (
          <TouchableOpacity
            key={screen.id}
            style={styles.tab}
            onPress={() =>
              flatListRef.current?.scrollToIndex({ index, animated: true })
            }
          >
            <Text style={styles.tabText}>{screen.title}</Text>
          </TouchableOpacity>
        ))}
      </View>
      <FlatList
        ref={flatListRef}
        data={SCREENS}
        renderItem={renderScreen}
        keyExtractor={(item) => item.id}
        horizontal
        pagingEnabled
        showsHorizontalScrollIndicator={false}
        bounces={false}
      />
    </DroneProvider>
  );
}

const styles = StyleSheet.create({
  screen: {
    width: SCREEN_WIDTH,
    flex: 1,
  },
  tabs: {
    flexDirection: 'row',
    backgroundColor: '#0a0a0f',
    paddingTop: 8,
    paddingBottom: 8,
    paddingHorizontal: 16,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(0, 255, 136, 0.2)',
  },
  tab: {
    flex: 1,
    paddingVertical: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  tabText: {
    color: '#00ff88',
    fontSize: 14,
    fontWeight: '700',
  },
});
