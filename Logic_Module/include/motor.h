#pragma once

#include <stdint.h>
#include <string.h>
#include "can_bus.h"

// ---------------- CANSimple Commands ----------------
constexpr uint32_t ODRIVE_CMD_HEARTBEAT          = 0x01;
constexpr uint32_t ODRIVE_CMD_ESTOP              = 0x02;
constexpr uint32_t ODRIVE_CMD_SET_AXIS_STATE     = 0x07;
constexpr uint32_t ODRIVE_CMD_GET_ENCODER_EST    = 0x09;
constexpr uint32_t ODRIVE_CMD_SET_INPUT_VEL      = 0x0D;
constexpr uint32_t ODRIVE_CMD_CLEAR_ERRORS       = 0x18;

// ---------------- Axis States ----------------
constexpr uint32_t AXIS_STATE_CLOSED_LOOP = 8;

// ---------------- Timing ----------------
constexpr uint32_t HEARTBEAT_TIMEOUT_MS = 200;

// ---------------- Telemetry ----------------
struct MotorTelemetry
{
    float position = 0.0f;     // turns
    float velocity = 0.0f;     // turns/s
    uint8_t axis_state = 0;
    uint32_t axis_error = 0;
    uint32_t last_heartbeat_ms = 0;
};

// ---------------- Motor Class ----------------
class Motor
{
public:
    explicit Motor(uint8_t node_id)
        : node_id_(node_id) {}

    // ---------- Commands ----------

    void clearErrors()
    {
        sendFrame(ODRIVE_CMD_CLEAR_ERRORS, nullptr, 0);
    }

    void enterClosedLoop()
    {
        sendU32(ODRIVE_CMD_SET_AXIS_STATE, AXIS_STATE_CLOSED_LOOP);
    }

    // CANSimple Set_Input_Vel:
    // float velocity [turns/s]
    // float torque_ff [Nm]
    void setVelocity(float vel, float torque_ff = 0.0f)
    {
        uint8_t data[8];
        memcpy(&data[0], &vel, sizeof(float));
        memcpy(&data[4], &torque_ff, sizeof(float));
        sendFrame(ODRIVE_CMD_SET_INPUT_VEL, data, 8);
    }

    void requestEncoder()
    {
        sendFrame(ODRIVE_CMD_GET_ENCODER_EST, nullptr, 0);
    }

    // ---------- RX Handling ----------

    void handleFrame(uint32_t can_id,
                     const uint8_t* data,
                     uint8_t len,
                     uint32_t now_ms)
    {
        uint32_t cmd = can_id & 0x1F;
        uint8_t src_node = can_id >> 5;

        if (src_node != node_id_) return;

        switch (cmd)
        {
            case ODRIVE_CMD_HEARTBEAT:
            {
                telemetry_.axis_error = *(uint32_t*)&data[0];
                telemetry_.axis_state = data[4];
                telemetry_.last_heartbeat_ms = now_ms;
            } break;

            case ODRIVE_CMD_GET_ENCODER_EST:
            {
                memcpy(&telemetry_.position, &data[0], sizeof(float));
                memcpy(&telemetry_.velocity, &data[4], sizeof(float));
            } break;

            default:
                break;
        }
    }

    // ---------- Safety ----------

    bool alive(uint32_t now_ms) const
    {
        return (now_ms - telemetry_.last_heartbeat_ms) < HEARTBEAT_TIMEOUT_MS;
    }

    const MotorTelemetry& telemetry() const
    {
        return telemetry_;
    }

private:
    uint8_t node_id_;
    MotorTelemetry telemetry_{};

    // ---------- CAN Helpers ----------

    inline uint32_t makeCanID(uint32_t cmd) const
    {
        return (node_id_ << 5) | cmd;
    }

    void sendU32(uint32_t cmd, uint32_t value)
    {
        uint8_t data[4];
        memcpy(data, &value, sizeof(uint32_t));
        sendFrame(cmd, data, 4);
    }

    void sendFrame(uint32_t cmd, const uint8_t* data, uint8_t len)
    {
        uint32_t id = makeCanID(cmd);
        bool ok = CANBus::instance().canSend(id, data, len);

        if (!ok)
        {
            Serial.print("[CAN TX FAIL] node=");
            Serial.print(node_id_);
            Serial.print(" cmd=0x");
            Serial.println(cmd, HEX);
        }
    }
};
