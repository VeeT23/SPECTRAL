#include <Arduino.h>
#include <Wire.h>

#include "screen.h"
#include "joystick.h"
#include "pin_def.h"
#include "radio.h"
#include "packet.h"

// ================= MAC ADDRESS =================
constexpr uint8_t robotMAC[] = {0x78, 0x42, 0x1C, 0x1F, 0xE9, 0xBC};

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

// ================= SETUP =======================
void setup()
{
    delay(1000);

    Wire.begin();
    Serial.begin(115200);

    Screen::instance().init(0x3C);

    // ---- Radio singleton ----
    auto& radio = Radio<ControlPacket, TelemetryPacket>::instance();

    if (!radio.begin(robotMAC))
    {
        Serial.println("Radio init failed!");
        while (true) { delay(1000); }
    }

    // ---- Telemetry received from robot ----
    radio.onPacket = [](const TelemetryPacket& pkt)
    {
        Serial.print("Battery: ");
        Serial.println(pkt.battery_v);
    };

    // ---- Robot timeout ----
    radio.onTimeout = []()
    {
        Serial.println("Robot link lost!");
    };
}

// ================= LOOP ========================
void loop()
{
    auto& radio = Radio<ControlPacket, TelemetryPacket>::instance();

    joy_left.poll();
    joy_right.poll();

    static uint32_t lastSend = 0;

    // ---- Send commands at 100 Hz ----
    if (millis() - lastSend >= 10)
    {
        lastSend = millis();

        ControlPacket cmd{};
        cmd.left_vel  = joy_left.y();
        cmd.right_vel = joy_right.y();
        cmd.flags     = 0;

        radio.send(cmd);
    }

    radio.update();

    // ---- UI ----
    Screen::instance().gfx().clearDisplay();
    joy_left.draw(0, 0);
    joy_right.draw(64, 0);
    Screen::instance().gfx().display();
}
