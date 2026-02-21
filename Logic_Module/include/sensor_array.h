#pragma once

#include <Arduino.h>
#include "config.h"
#include "pin_def.h"
#include "global_state.h"

inline void setMuxAddress(uint8_t addr)
{
    digitalWrite(PINS::A0, addr & 0x01);
    digitalWrite(PINS::A1, addr & 0x02);
    digitalWrite(PINS::A2, addr & 0x04);
}

void poll_sensors()
{
    sensor_idx++;
    sensor_idx = (sensor_idx == SENSORS_PER_MODULE) ? 0 : sensor_idx;
    setMuxAddress(sensor_idx);
    esp_rom_delay_us(20); // Short delay to allow mux to stabilize

    ir_raw[0 * SENSORS_PER_MODULE + sensor_idx] = analogRead(PINS::S4);
    ir_raw[1 * SENSORS_PER_MODULE + sensor_idx] = analogRead(PINS::S3);
    ir_raw[2 * SENSORS_PER_MODULE + sensor_idx] = analogRead(PINS::S2);
    ir_raw[3 * SENSORS_PER_MODULE + sensor_idx] = analogRead(PINS::S1);
    ir_raw[4 * SENSORS_PER_MODULE + sensor_idx] = analogRead(PINS::S0);
}

void process_ir_data()
{
    uint16_t filtered[TOTAL_SENSORS];

    if (TOTAL_SENSORS == 0)
        return;

    if (TOTAL_SENSORS == 1)
    {
        filtered[0] = ir_raw[0];
    }
    else
    {
        // First element
        filtered[0] = (ir_raw[0] + ir_raw[1]) / 2;

        // Middle elements
        for (uint8_t i = 1; i < TOTAL_SENSORS - 1; i++)
        {
            filtered[i] = (ir_raw[i - 1] + ir_raw[i] + ir_raw[i + 1]) / 3;
        }

        // Last element
        filtered[TOTAL_SENSORS - 1] =
            (ir_raw[TOTAL_SENSORS - 2] + ir_raw[TOTAL_SENSORS - 1]) / 2;
    }

    // Threshold masking
    for (uint8_t i = 0; i < TOTAL_SENSORS; i++)
    {
        ir_processed[i] = (filtered[i] > IR_THRESHOLD);
    }
}

int8_t get_error()
{
    if (TOTAL_SENSORS == 0)
        return INT8_MAX;

    int8_t found_index = -1;

    // Define the two center positions
    int8_t center_left = (TOTAL_SENSORS - 1) / 2;
    int8_t center_right = TOTAL_SENSORS / 2;

    // Search outward symmetrically
    for (int8_t offset = 0; offset <= center_right; offset++)
    {
        if (center_left - offset >= 0 &&
            ir_processed[center_left - offset])
        {
            found_index = center_left - offset;
            break;
        }

        if (center_right + offset < TOTAL_SENSORS &&
            ir_processed[center_right + offset])
        {
            found_index = center_right + offset;
            break;
        }
    }

    if (found_index == -1)
        return INT8_MAX; // No line detected

    // Expand left
    int8_t left = found_index;
    while (left > 0 && ir_processed[left - 1])
        left--;

    // Expand right
    int8_t right = found_index;
    while (right < TOTAL_SENSORS - 1 && ir_processed[right + 1])
        right++;

    // Midpoint of detected span
    int16_t midpoint_times2 = left + right;
    // (left + right) = 2 * midpoint

    // True center scaled by 2
    int16_t center_times2 = TOTAL_SENSORS - 1;

    // Signed error
    int16_t error = midpoint_times2 - center_times2;

    return (int8_t)(error / 2);
}

float pid_update(float error, float dt)
{
    static float integral = 0.0f;
    static float prev_error = 0.0f;

    integral += error * dt;
    float derivative = (error - prev_error) / dt;
    prev_error = error;

    return KP * error + KI * integral + KD * derivative;
}
