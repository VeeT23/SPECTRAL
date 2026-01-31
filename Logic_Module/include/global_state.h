#pragma once
#include "Radio.h"
#include "packet.h"
#include "config.h"


// ========== GLOBAL DATA ==========

static uint8_t sensor_idx = 0; // Current selected sensor
static uint16_t ir_raw[TOTAL_SENSORS];

// ---------- RADIO ----------

using GlobalRadio = Radio<TelemetryPacket, ControlPacket>;

inline GlobalRadio& RadioInstance() {
    return GlobalRadio::instance();
}
