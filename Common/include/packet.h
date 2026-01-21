#pragma once
#include <stdint.h>

struct __attribute__((packed)) ControlPacket {
    uint32_t seq;
    uint8_t  flags;
    float left_vel;
    float right_vel;
};

struct __attribute__((packed)) TelemetryPacket {
    uint32_t seq;
    uint8_t  flags;
    float battery_v;
};