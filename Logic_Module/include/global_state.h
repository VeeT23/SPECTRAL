#pragma once
#include "Radio.h"
#include "config.h"
#include "packet.h"

// ========== GLOBAL DATA ==========

static uint8_t sensor_idx = 0; // Current selected sensor
static uint16_t ir_raw[TOTAL_SENSORS];
static bool ir_processed[TOTAL_SENSORS];

// ---------- RADIO ----------

using GlobalRadio = ESPNowRadio<TelemetryPacket, ControlPacket>;

// Use 'static' here instead of 'inline' to avoid requiring C++17 inline variables.
static GlobalRadio& RadioInstance() {
    return GlobalRadio::instance();
}
