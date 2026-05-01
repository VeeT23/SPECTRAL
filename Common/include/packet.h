#pragma once

#include <cstdint>
#include "config.h"

struct __attribute__((packed)) ControlPacket
{
    uint8_t control_mode;
    float throttle_left;  // Desired velocity in m/s
    float throttle_right; // Desired velocity in m/s
    float max_velocity;   // Maximum velocity in m/s for line following
};

struct __attribute__((packed)) TelemetryPacket
{
    uint32_t ticks_since_idle;
    float velocity;               // Current velocity in m/s
    float relative_heading;       // Current relative heading from origin angle in degrees
    uint16_t ir_raw[40];          // Raw IR sensor readings
    uint64_t packed_ir_processed; // Processed IR sensor states (e.g., line detected)
    float line_error;             // Pre pid line error (e.g., deviation from line center in number of sensors)
    float pid_output;             // PID controller output (e.g., correction to apply to motors)

    float distance; // Total distance traveled in meters
};