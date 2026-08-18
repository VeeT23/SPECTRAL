#pragma once
#include "Radio.h"
#include "config.h"
#include "packet.h"

// ========== GLOBAL DATA ==========

// ---------- RADIO ----------

using GlobalRadio = ESPNowRadio<TelemetryPacket, ControlPacket>;

// Use 'static' here instead of 'inline' to avoid requiring C++17 inline variables.
static GlobalRadio& RadioInstance() {
    return GlobalRadio::instance();
}
