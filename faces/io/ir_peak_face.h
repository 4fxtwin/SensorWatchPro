/*
 * MIT License
 *
 * Copyright (c) 2026 SensorWatchPro contributors
 *
 * Based on light_sensor_face.c, Copyright (c) 2024 Joey Castillo
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

#pragma once

#include "movement.h"

#ifdef HAS_IR_SENSOR

/*
 * IR PEAK HOLD
 *
 * Test face for the IR phototransistor. Reads the same ADC value as the
 * Light Sensor face, at the same 8 Hz rate, and keeps the lowest and
 * highest values seen since the last reset. Cover or flash the sensor,
 * then read the result once the display is visible again.
 *
 * ALARM: cycle the display between LIVE, MAX and MIN.
 * LIGHT: reset MIN and MAX to the current reading (the LED stays off).
 *
 * Classic LCD shows Li / Hi / Lo in the top left.
 * MIN and MAX are also reset each time the face is opened.
 */

typedef enum {
    IR_PEAK_LIVE = 0,
    IR_PEAK_MAX,
    IR_PEAK_MIN,
    IR_PEAK_NUM_MODES
} ir_peak_mode_t;

typedef struct {
    uint16_t min;
    uint16_t max;
    uint16_t last;
    ir_peak_mode_t mode;
} ir_peak_state_t;

void ir_peak_face_setup(uint8_t watch_face_index, void ** context_ptr);
void ir_peak_face_activate(void *context);
bool ir_peak_face_loop(movement_event_t event, void *context);
void ir_peak_face_resign(void *context);

#define ir_peak_face ((const watch_face_t){ \
    ir_peak_face_setup, \
    ir_peak_face_activate, \
    ir_peak_face_loop, \
    ir_peak_face_resign, \
    NULL, \
})

#endif // HAS_IR_SENSOR
