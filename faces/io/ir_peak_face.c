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

#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include "ir_peak_face.h"
#include "adc.h"

#ifdef HAS_IR_SENSOR

static uint16_t _ir_peak_sample(void) {
    return adc_get_analog_value(HAL_GPIO_IRSENSE_pin());
}

static void _ir_peak_reset(ir_peak_state_t *state) {
    state->last = _ir_peak_sample();
    state->min = state->last;
    state->max = state->last;
}

static void _ir_peak_display(ir_peak_state_t *state) {
    char buf[7];
    uint16_t value;

    switch (state->mode) {
        case IR_PEAK_MAX:
            watch_display_text_with_fallback(WATCH_POSITION_TOP, "MAX  ", "Hi");
            value = state->max;
            break;
        case IR_PEAK_MIN:
            watch_display_text_with_fallback(WATCH_POSITION_TOP, "MIN  ", "Lo");
            value = state->min;
            break;
        case IR_PEAK_LIVE:
        default:
            watch_display_text_with_fallback(WATCH_POSITION_TOP, "LIVE ", "Li");
            value = state->last;
            break;
    }
    snprintf(buf, sizeof(buf), "%-6u", (unsigned int)value);
    watch_display_text(WATCH_POSITION_BOTTOM, buf);
}

void ir_peak_face_setup(uint8_t watch_face_index, void ** context_ptr) {
    (void) watch_face_index;
    if (*context_ptr == NULL) {
        *context_ptr = malloc(sizeof(ir_peak_state_t));
        memset(*context_ptr, 0, sizeof(ir_peak_state_t));
    }
}

void ir_peak_face_activate(void *context) {
    ir_peak_state_t *state = (ir_peak_state_t *)context;

    HAL_GPIO_IR_ENABLE_out();
    HAL_GPIO_IR_ENABLE_clr();
    HAL_GPIO_IRSENSE_pmuxen(HAL_GPIO_PMUX_ADC);
    adc_init();
    adc_enable();
    movement_request_tick_frequency(8);

    state->mode = IR_PEAK_LIVE;
    _ir_peak_reset(state);
}

bool ir_peak_face_loop(movement_event_t event, void *context) {
    ir_peak_state_t *state = (ir_peak_state_t *)context;

    switch (event.event_type) {
        case EVENT_ACTIVATE:
            watch_clear_display();
            _ir_peak_display(state);
            break;
        case EVENT_TICK:
            state->last = _ir_peak_sample();
            if (state->last < state->min) state->min = state->last;
            if (state->last > state->max) state->max = state->last;
            _ir_peak_display(state);
            break;
        case EVENT_ALARM_BUTTON_UP:
            state->mode = (state->mode + 1) % IR_PEAK_NUM_MODES;
            _ir_peak_display(state);
            break;
        case EVENT_LIGHT_BUTTON_DOWN:
            // Swallow it: the LED would add light to the reading.
            break;
        case EVENT_LIGHT_BUTTON_UP:
            _ir_peak_reset(state);
            _ir_peak_display(state);
            break;
        case EVENT_TIMEOUT:
            movement_move_to_face(0);
            break;
        default:
            return movement_default_loop_handler(event);
    }

    return true;
}

void ir_peak_face_resign(void *context) {
    (void) context;

    adc_disable();
    HAL_GPIO_IRSENSE_pmuxdis();
    HAL_GPIO_IRSENSE_off();
    HAL_GPIO_IR_ENABLE_off();
}

#endif // HAS_IR_SENSOR
