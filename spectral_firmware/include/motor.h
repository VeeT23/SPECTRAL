#pragma once

#include <stdint.h>
#include <string.h>
#include <Arduino.h>
#include "can_bus.h"
#include "config.h"      // Defines ODrive commands
#include "driver/twai.h" // ESP32 TWAI types

// ---------------- Telemetry ----------------
struct MotorTelemetry
{
    float revolutions = 0.0f; // turns
    float velocity = 0.0f; // turns/s
    uint8_t axis_state = 0;
    uint32_t axis_error = 0;
    uint32_t last_heartbeat_ms = 0;
    bool encoder_received = false;
};

// ---------------- Motor Class ----------------
class Motor
{
public:
    explicit Motor(uint8_t node_id, bool inverted = false)
        : node_id_(node_id), inverted_(inverted) {}

    // ---------- Commands ----------
    void clearErrors()
    {
        sendFrame(ODRIVE_CMD_CLEAR_ERRORS, nullptr, 0);
    }

    void enterClosedLoop()
    {
        sendU32(ODRIVE_CMD_SET_AXIS_STATE, AXIS_STATE_CLOSED_LOOP);
    }

    void zeroPosition()
    {
        revolution_offset_ = telemetry_.revolutions;
    }

    void setVelocity(float vel, float torque_ff = 0.0f)
    {
        if (inverted_)
        {
            vel = -vel;
        }
        uint8_t data[8];
        memcpy(&data[0], &vel, sizeof(float));
        memcpy(&data[4], &torque_ff, sizeof(float));
        sendFrame(ODRIVE_CMD_SET_INPUT_VEL, data, sizeof(data));
    }

    void requestEncoder()
    {
        sendFrame(ODRIVE_CMD_GET_ENCODER_EST, nullptr, 0);
    }

    // ---------- TWAI RX Handling ----------
    // Process an incoming TWAI frame, update telemetry if relevant
    void processTwaiFrame(const twai_message_t &msg, uint32_t now_ms)
    {
        const uint32_t cmd = msg.identifier & 0x1F;
        const uint8_t src_node = msg.identifier >> 5;

        if (src_node != node_id_)
            return;

        switch (cmd)
        {
        case ODRIVE_CMD_HEARTBEAT:
            if (msg.data_length_code >= 5)
            {
                memcpy(&telemetry_.axis_error, &msg.data[0], sizeof(uint32_t));
                telemetry_.axis_state = msg.data[4];
                telemetry_.last_heartbeat_ms = now_ms;
            }
            break;

        case ODRIVE_CMD_GET_ENCODER_EST:
            if (msg.data_length_code >= 8)
            {
                float pos, vel;
                memcpy(&pos, &msg.data[0], sizeof(float));
                memcpy(&vel, &msg.data[4], sizeof(float));

                if (inverted_)
                {
                    pos = -pos;
                    vel = -vel;
                }

                pos -= revolution_offset_;

                telemetry_.revolutions = pos;
                telemetry_.velocity = vel;
                telemetry_.encoder_received = true; // mark fresh data
            }
            break;

        default:
            break;
        }
    }

    // ---------- Safety ----------
    [[nodiscard]]
    bool alive(uint32_t now_ms) const
    {
        return (now_ms - telemetry_.last_heartbeat_ms) < HEARTBEAT_TIMEOUT_MS;
    }

    bool waitForEncoder(uint32_t timeout_ms)
    {
        uint32_t start = millis();
        telemetry_.encoder_received = false;

        requestEncoder();

        while (!telemetry_.encoder_received)
        {
            twai_message_t msg;
            uint32_t now_ms = millis();

            while (CANBus::instance().receive(msg, 0))
            {
                processTwaiFrame(msg, now_ms);
            }

            if ((millis() - start) > timeout_ms)
            {
                return false; // timeout
            }

            vTaskDelay(pdMS_TO_TICKS(1)); // yield
        }

        return true;
    }

    const MotorTelemetry &telemetry() const
    {
        return telemetry_;
    }

private:
    float revolution_offset_ = 0.0f;
    const bool inverted_;
    uint8_t node_id_;
    MotorTelemetry telemetry_{};

    // ---------- CAN Helpers ----------
    constexpr uint32_t makeCanID(uint32_t cmd) const
    {
        return (static_cast<uint32_t>(node_id_) << 5) | cmd;
    }

    void sendU32(uint32_t cmd, uint32_t value)
    {
        uint8_t data[4];
        memcpy(data, &value, sizeof(value));
        sendFrame(cmd, data, sizeof(data));
    }

    void sendFrame(uint32_t cmd, const uint8_t *data, uint8_t len)
    {
        const uint32_t id = makeCanID(cmd);
        if (!CANBus::instance().canSend(id, data, len))
        {
            Serial.print("[CAN TX FAIL] node=");
            Serial.print(node_id_);
            Serial.print(" cmd=0x");
            Serial.println(cmd, HEX);
        }
    }
};
