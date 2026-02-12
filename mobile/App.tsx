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
    );
  };

  return (
    <DroneProvider>
      <View style={styles.container}>
        <FlatList
          ref={flatListRef}
          data={SCREENS}
          renderItem={renderScreen}
          keyExtractor={(item) => item.id}
          horizontal
          pagingEnabled
          showsHorizontalScrollIndicator={false}
          bounces={false}
          scrollEventThrottle={16}
          decelerationRate="fast"
        />
      </View>
    </DroneProvider>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0a0a0f',
  },
  screen: {
    width: SCREEN_WIDTH,
  },
});
