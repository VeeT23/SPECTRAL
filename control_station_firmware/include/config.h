#pragma once
#include <Arduino.h>

static const uint8_t ROBOT_MAC[6] = {0x6C, 0xC8, 0x40, 0x3A, 0x1D, 0x64};

constexpr uint32_t TX_FREQUENCY_HZ = 60; // 60 Hz control update rate

constexpr float BASE_VELOCITY = 0.75; // Default max velocity (m/s)

constexpr uint32_t TX_PERIOD = 1000 / TX_FREQUENCY_HZ;
constexpr uint32_t RX_TIMEOUT_MS = 100;
constexpr bool RADIO_DEBUG = false;

// ================= SERIAL =====================

constexpr uint16_t TELEMETRY_HEADER = 0xAA55;