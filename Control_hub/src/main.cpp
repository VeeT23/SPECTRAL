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
    false
);

Joystick joy_right(
    PINS::JOY_RIGHT::X,
    PINS::JOY_RIGHT::Y,
    PINS::JOY_RIGHT::BUTTON,
    false,
    true
);

// ================= RADIO =======================

using ControllerRadio = Radio<ControlPacket, TelemetryPacket>;
ControllerRadio& radio = ControllerRadio::instance();

// ================= SETUP =======================

void setup()
{
    delay(2000);
    Serial.begin(115200);
    Wire.begin();

    Screen::instance().init(0x3C);

    if (!radio.begin(ROBOT_MAC, 1)) {
        Serial.println("Radio init failed!");
        while (true) { delay(1000); }
    }

    // ---- Telemetry from robot ----
    radio.onPacket = [](const TelemetryPacket& pkt)
    {
        static uint32_t lastPrint = 0;
        if (millis() - lastPrint > 500) {
            lastPrint = millis();
            Serial.print("Battery: ");
            Serial.println(pkt.battery_v);
        }
    };

    // ---- Link timeout ----
    radio.onTimeout = []()
    {
        Serial.println("Robot link lost!");
    };
}

// ================= LOOP ========================

void loop()
{
    joy_left.poll();
    joy_right.poll();

    static uint32_t lastSend = 0;

    // ---- Send commands at 100 Hz ----
    if (millis() - lastSend >= 10) {
        lastSend = millis();

        ControlPacket cmd{};
        cmd.left_vel  = joy_left.y();
        cmd.right_vel = joy_right.y();

        radio.send(cmd, false); // explicit: no ACK
        Serial.println("Sent command");
    }

    radio.update();

    // ---- UI ----
    auto& gfx = Screen::instance().gfx();
    gfx.clearDisplay();
    joy_left.draw(0, 0);
    joy_right.draw(64, 0);
    gfx.display();
}
