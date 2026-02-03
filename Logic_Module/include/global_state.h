#pragma once
#include "Radio.h"
#include "config.h"


// ========== GLOBAL DATA ==========

static uint8_t sensor_idx = 0; // Current selected sensor
static uint16_t ir_raw[TOTAL_SENSORS];

// ---------- RADIO ----------

// ---- Control packet from controller ----
static volatile bool control_pkt_pending = false;
static ControlPacket latest_control_pkt{};


using GlobalRadio = Radio<TelemetryPacket, ControlPacket>;

// Use 'static' here instead of 'inline' to avoid requiring C++17 inline variables.
static GlobalRadio& RadioInstance() {
    return GlobalRadio::instance();
}
