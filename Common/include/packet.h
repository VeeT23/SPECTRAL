#pragma once

#include <cstdint>
#include "config.h"

struct __attribute__((packed)) ControlPacket
{
    uint8_t control_mode;
    float throttle_left;  // Desired velocity in m/s
    float throttle_right; // Desired steering angle in degrees
};

struct __attribute__((packed)) TelemetryPacket
{
    uint32_t ticks_since_idle;
    float velocity;               // Current velocity in m/s
    float steering;               // Current steering angle in degrees
    uint16_t ir_raw[40];          // Raw IR sensor readings
    uint64_t packed_ir_processed; // Processed IR sensor states (e.g., line detected)
    float line_error;
    float pid_output;

    float distance; // Total distance traveled
    float approx_x; // Relative position in meters
    float approx_y;
};