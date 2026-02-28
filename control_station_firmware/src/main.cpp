#include <Arduino.h>
#include <Wire.h>

#include "screen.h"
#include "joystick.h"
#include "pin_def.h"
#include "config.h"
#include "radio.h"
#include "packet.h"

// ================= INPUT DEVICES ===============

Joystick joy_left(
    PINS::JOY_LEFT::X,
    PINS::JOY_LEFT::Y,
    PINS::JOY_LEFT::BUTTON,
    true,
    false);

Joystick joy_right(
    PINS::JOY_RIGHT::X,
    PINS::JOY_RIGHT::Y,
    PINS::JOY_RIGHT::BUTTON,
    false,
    true);

// ================= RADIO =======================

using ControllerRadio = ESPNowRadio<ControlPacket, TelemetryPacket>;
ControllerRadio &radio = ControllerRadio::instance();

// ================= SERIAL =====================

constexpr uint16_t TELEMETRY_HEADER = 0xAA55;

// ================= SETUP =======================

void setup()
{
    delay(2000);
    Serial.begin(576000);
    while (!Serial)
    {
        delay(100);
    }

    Wire.begin();

    Screen::instance().init(0x3C);
    Serial.println("Controller starting...");
    if (!radio.begin(ROBOT_MAC, RX_TIMEOUT_MS, RADIO_DEBUG))
    {
        Serial.println("Radio init failed!");
        while (true)
        {
            delay(1000);
        }
    }
}

// ================= LOOP ========================

void loop()
{

    joy_left.poll();
    joy_right.poll();

    static uint32_t lastSend = 0;
    static uint8_t control_mode = 0; // 0: IDLE, 1: MANUAL, 2: AUTO

    if (joy_left.just_released())
    {
        if (control_mode != 0)
        {
            control_mode = 0;
        }
        else
        {
            control_mode = 1;
        }
    }

    if (joy_right.just_released())
    {
        if (control_mode != 0)
        {
            control_mode = 0;
        }
        else
        {
            control_mode = 2;
        }
    }

    if (millis() - lastSend >= TX_PERIOD)
    {
        lastSend = millis();

        ControlPacket cmd{};
        cmd.control_mode = control_mode;
        cmd.throttle_left = joy_left.y();   // Forward/backward on left stick
        cmd.throttle_right = joy_right.y(); // Left/right on right stick
        radio.send(cmd);
    }

    radio.update();

    TelemetryPacket pkt;

    if (radio.recieve(pkt))
    {
        const uint16_t size = sizeof(pkt);

        Serial.write((uint8_t *)&TELEMETRY_HEADER, sizeof(TELEMETRY_HEADER));
        Serial.write((uint8_t *)&size, sizeof(size));
        Serial.write((uint8_t *)&pkt, size);
    }

    // ---- UI ----
    auto &gfx = Screen::instance().gfx();
    gfx.clearDisplay();
    joy_left.draw(0, 0);
    joy_right.draw(64, 0);
    gfx.setCursor(0, 32);
    gfx.println(control_mode);

    gfx.display();
    delay(10);
}
