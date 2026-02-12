import React, { useRef, useState } from 'react';
import { View, PanResponder, StyleSheet, Dimensions } from 'react-native';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

interface JoystickProps {
  onMove: (x: number, y: number) => void;
  size?: number;
  mode?: 'vertical' | 'horizontal' | 'both';
  color?: string;
}

export const Joystick: React.FC<JoystickProps> = ({
  onMove,
  size = SCREEN_WIDTH * 0.35,
  mode = 'both',
  color = '#00ff88',
}) => {
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const centerRadius = size / 2;
  const stickRadius = size / 4;

  const panResponder = useRef(
    PanResponder.create({
      onStartShouldSetPanResponder: () => true,
      onMoveShouldSetPanResponder: () => true,
      
      onPanResponderGrant: () => {
        // Inicio del toque
      },
      
      onPanResponderMove: (_, gesture) => {
        let newX = gesture.dx;
        let newY = gesture.dy;

        // Restringir según el modo
        if (mode === 'vertical') {
          newX = 0;
        } else if (mode === 'horizontal') {
          newY = 0;
        }

        // Limitar al área circular
        const distance = Math.sqrt(newX * newX + newY * newY);
        const maxDistance = centerRadius - stickRadius;

        if (distance > maxDistance) {
          const angle = Math.atan2(newY, newX);
          newX = Math.cos(angle) * maxDistance;
          newY = Math.sin(angle) * maxDistance;
        }

        setPosition({ x: newX, y: newY });

        // Normalizar valores a -1.0 ... 1.0
        const normalizedX = newX / maxDistance;
        const normalizedY = -newY / maxDistance; // Invertir Y para que arriba sea positivo

        onMove(normalizedX, normalizedY);
      },
      
      onPanResponderRelease: () => {
        // Volver al centro
        setPosition({ x: 0, y: 0 });
        onMove(0, 0);
      },
    })
  ).current;

  return (
    <View style={[styles.container, { width: size, height: size }]}>
      {/* Base del joystick */}
      <View style={[styles.base, { 
        width: size, 
        height: size, 
        borderRadius: size / 2,
        borderColor: color + '4D', // 30% opacity
      }]}>
        {/* Líneas de guía */}
        {mode !== 'horizontal' && (
          <View style={[styles.guideLine, styles.verticalLine, { backgroundColor: color + '33' }]} />
        )}
        {mode !== 'vertical' && (
          <View style={[styles.guideLine, styles.horizontalLine, { backgroundColor: color + '33' }]} />
        )}

        {/* Centro */}
        <View style={[styles.centerDot, { backgroundColor: color }]} />
      </View>

      {/* Stick móvil */}
      <View
        {...panResponder.panHandlers}
        style={[
          styles.stick,
          {
            width: stickRadius * 2,
            height: stickRadius * 2,
            borderRadius: stickRadius,
            backgroundColor: color,
            transform: [
              { translateX: position.x },
              { translateY: position.y },
            ],
          },
        ]}
      >
        <View style={styles.stickInner} />
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  base: {
    position: 'absolute',
    backgroundColor: 'rgba(20, 20, 30, 0.9)',
    borderWidth: 3,
    justifyContent: 'center',
    alignItems: 'center',
  },
  guideLine: {
    position: 'absolute',
  },
  verticalLine: {
    width: 2,
    height: '80%',
  },
  horizontalLine: {
    width: '80%',
    height: 2,
  },
  centerDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  stick: {
    position: 'absolute',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: 'rgba(255, 255, 255, 0.3)',
    elevation: 15,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
  },
  stickInner: {
    width: '60%',
    height: '60%',
    borderRadius: 100,
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
  },
});
