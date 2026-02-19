#pragma once

#include <cstdint>
#include "config.h"

struct __attribute__((packed)) ControlPacket {
    float velocity; // Desired velocity in m/s
    float steering; // Desired steering angle in degrees
};

struct __attribute__((packed)) TelemetryPacket {
    float velocity; // Current velocity in m/s
    float steering; // Current steering angle in degrees
    uint16_t ir_raw[40]; // Raw IR sensor readings
    bool ir_processed[40]; // Processed IR sensor states (e.g., line detected)
};