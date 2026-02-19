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

using ControllerRadio = ESPNowRadio<ControlPacket, TelemetryPacket>;
ControllerRadio& radio = ControllerRadio::instance();

// ================= SETUP =======================

void setup()
{
    delay(2000);
    Serial.begin(115200);
    while (!Serial)
    {
        delay(100);
    }
    
    Wire.begin();

    Screen::instance().init(0x3C);
    Serial.println("Controller starting...");
    if (!radio.begin(ROBOT_MAC, RX_TIMEOUT_MS, RADIO_DEBUG)) {
        Serial.println("Radio init failed!");
        while (true) { delay(1000); }
    }

}

// ================= LOOP ========================

void loop()
{
    joy_left.poll();
    joy_right.poll();

    static uint32_t lastSend = 0;

    if (millis() - lastSend >= TX_PERIOD) {
        lastSend = millis();

        ControlPacket cmd{};
        cmd.velocity = joy_left.y(); // Forward/backward on left stick
        cmd.steering = joy_right.x(); // Left/right on right stick
        radio.send(cmd);
    }

    radio.update();

    // ---- UI ----
    auto& gfx = Screen::instance().gfx();
    gfx.clearDisplay();
    joy_left.draw(0, 0);
    joy_right.draw(64, 0);
    gfx.display();
    delay(10);
}
