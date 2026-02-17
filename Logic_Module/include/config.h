#pragma once
#include <Arduino.h>

// ---------------- CONTROL ----------------
constexpr uint32_t CONTROL_HZ = 1000;
constexpr TickType_t CONTROL_PERIOD = pdMS_TO_TICKS(1000 / CONTROL_HZ);
constexpr TickType_t DRAW_PERIOD = pdMS_TO_TICKS(40);
constexpr TickType_t TELEMETRY_PERIOD = pdMS_TO_TICKS(50);

constexpr uint8_t WHEEL_DIAMETER_MM = 60;

constexpr float WHEEL_CIRCUMFERENCE_M =
    (WHEEL_DIAMETER_MM * PI) / 1000.0f;

constexpr float MAX_VELOCITY = 0.5f;   // m/s

constexpr float MAX_REV = MAX_VELOCITY / WHEEL_CIRCUMFERENCE_M; // rev/s

constexpr float KP = 1.0f; // Proportional gain for line following
constexpr float KI = 0.01f; // Integral gain for line following
constexpr float KD = 0.01f; // Derivative gain for line following


// ---------------- IR SENSORS ----------------
constexpr uint8_t NUM_MODULES = 5;
constexpr uint8_t SENSORS_PER_MODULE = 8;
constexpr uint8_t TOTAL_SENSORS = NUM_MODULES * SENSORS_PER_MODULE;
constexpr uint16_t IR_THRESHOLD = 2000; // Example threshold value


// ---------------- RADIO ----------------

const uint8_t CONTROLLER_MAC[6] = {0xD8, 0x3B, 0xDA, 0x46, 0x57, 0x80};
constexpr uint32_t RX_TIMEOUT_MS = 100;
// ---------------- CAN ----------------
constexpr uint32_t CAN_TX_TIMEOUT_MS = 40;

// ---------------- ODRIVE ----------------
constexpr uint32_t ODRIVE_CMD_HEARTBEAT = 0x01;
constexpr uint32_t ODRIVE_CMD_ESTOP = 0x02;
constexpr uint32_t ODRIVE_CMD_SET_AXIS_STATE = 0x07;
constexpr uint32_t ODRIVE_CMD_GET_ENCODER_EST = 0x09;
constexpr uint32_t ODRIVE_CMD_SET_INPUT_VEL = 0x0D;
constexpr uint32_t ODRIVE_CMD_CLEAR_ERRORS = 0x18;

constexpr uint32_t AXIS_STATE_CLOSED_LOOP = 8;

constexpr uint32_t HEARTBEAT_TIMEOUT_MS = 200;