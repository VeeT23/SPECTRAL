#pragma once
#include "radio.h"
#include "packet.h"

using Radio_t = Radio<TelemetryPacket, ControlPacket>;

void setup_control(Radio_t* radio);