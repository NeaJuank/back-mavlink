import React, { useRef } from 'react';
import { View, PanResponder, StyleSheet, Dimensions, Animated } from 'react-native';

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
  const centerRadius = size / 2;
  const stickRadius  = size / 4;
  const maxDistance  = centerRadius - stickRadius;

  // ── Animated.ValueXY corre en el UI thread — sin pasar por el bridge JS ──
  const animPos = useRef(new Animated.ValueXY({ x: 0, y: 0 })).current;

  // Guardamos los valores crudos para el callback onMove sin setState
  const rawPos = useRef({ x: 0, y: 0 });

  const panResponder = useRef(
    PanResponder.create({
      onStartShouldSetPanResponder: () => true,
      onMoveShouldSetPanResponder:  () => true,

      onPanResponderMove: (_, gesture) => {
        let dx = gesture.dx;
        let dy = gesture.dy;

        // Restringir según modo
        if (mode === 'vertical')   dx = 0;
        if (mode === 'horizontal') dy = 0;

        // Limitar al círculo
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist > maxDistance) {
          const angle = Math.atan2(dy, dx);
          dx = Math.cos(angle) * maxDistance;
          dy = Math.sin(angle) * maxDistance;
        }

        // Actualizar posición animada directamente (sin setState → sin re-render)
        animPos.setValue({ x: dx, y: dy });

        // Guardar raw y llamar callback
        rawPos.current = { x: dx, y: dy };
        const nx =  dx / maxDistance;
        const ny = -dy / maxDistance; // Y invertido: arriba = positivo
        onMove(nx, ny);
      },

      onPanResponderRelease: () => {
        // Spring de vuelta al centro — animado en UI thread
        Animated.spring(animPos, {
          toValue:         { x: 0, y: 0 },
          useNativeDriver: true,
          tension:         120,
          friction:        8,
        }).start();

        rawPos.current = { x: 0, y: 0 };
        onMove(0, 0);
      },

      onPanResponderTerminate: () => {
        Animated.spring(animPos, {
          toValue:         { x: 0, y: 0 },
          useNativeDriver: true,
          tension:         120,
          friction:        8,
        }).start();
        rawPos.current = { x: 0, y: 0 };
        onMove(0, 0);
      },
    })
  ).current;

  return (
    <View style={[styles.container, { width: size, height: size }]}>
      {/* Base */}
      <View style={[styles.base, {
        width:        size,
        height:       size,
        borderRadius: size / 2,
        borderColor:  color + '4D',
      }]}>
        {mode !== 'horizontal' && (
          <View style={[styles.guideLine, styles.verticalLine,   { backgroundColor: color + '33' }]} />
        )}
        {mode !== 'vertical' && (
          <View style={[styles.guideLine, styles.horizontalLine, { backgroundColor: color + '33' }]} />
        )}
        <View style={[styles.centerDot, { backgroundColor: color }]} />
      </View>

      {/* Stick — transform manejado por Animated en el UI thread */}
      <Animated.View
        {...panResponder.panHandlers}
        style={[
          styles.stick,
          {
            width:        stickRadius * 2,
            height:       stickRadius * 2,
            borderRadius: stickRadius,
            backgroundColor: color,
            transform: [
              { translateX: animPos.x },
              { translateY: animPos.y },
            ],
          },
        ]}
      >
        <View style={styles.stickInner} />
      </Animated.View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    justifyContent: 'center',
    alignItems:     'center',
  },
  base: {
    position:        'absolute',
    backgroundColor: 'rgba(20, 20, 30, 0.9)',
    borderWidth:     3,
    justifyContent:  'center',
    alignItems:      'center',
  },
  guideLine:      { position: 'absolute' },
  verticalLine:   { width: 2, height: '80%' },
  horizontalLine: { width: '80%', height: 2 },
  centerDot: {
    width:        8,
    height:       8,
    borderRadius: 4,
  },
  stick: {
    position:        'absolute',
    justifyContent:  'center',
    alignItems:      'center',
    borderWidth:     2,
    borderColor:     'rgba(255, 255, 255, 0.3)',
    elevation:       15,
    shadowColor:     '#000',
    shadowOffset:    { width: 0, height: 4 },
    shadowOpacity:   0.3,
    shadowRadius:    8,
  },
  stickInner: {
    width:           '60%',
    height:          '60%',
    borderRadius:    100,
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
  },
});