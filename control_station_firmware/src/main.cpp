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

// ================= SETUP =======================

void setup()
{
    delay(2000);
    Serial.begin(576000);

    Wire.begin();

    Screen::instance().init(0x3C);
    if (!radio.begin(ROBOT_MAC, RX_TIMEOUT_MS, RADIO_DEBUG))
    {
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
    static uint8_t control_mode = 0;           // 0: IDLE, 1: MANUAL, 2: AUTO
    static float max_velocity = BASE_VELOCITY; // Default max velocity, can be adjusted in AUTO mode
    static bool in_config_menu = false;

    if (joy_left.just_released())
    {
        if (in_config_menu)
        {
            in_config_menu = false;
        }
        else
        {
            if (control_mode == 0) // Only allow config menu access from IDLE mode
            {
                in_config_menu = true;
            }
            else
            {
                control_mode = 0; // IDLE
            }
        }
    }

    if (joy_right.just_released())
    {
        if (in_config_menu)
        {
            // Exit config menu on right joystick button press
            in_config_menu = false;
        }
        else
        {
            // Cycle control modes on right joystick button press
            control_mode++;
            if (control_mode > 2)
                control_mode = 0;
        }
    }

    if (in_config_menu)
    {
        max_velocity += joy_right.y() * 0.005f;               // Adjust max velocity with right joystick up/down
        max_velocity = constrain(max_velocity, 0.05f, 10.0f); // Constrain to reasonable range
    }

    if (millis() - lastSend >= TX_PERIOD)
    {
        lastSend = millis();

        float throttle = joy_left.y() * max_velocity;                    // Forward/backward on left joystick
        float steering = joy_right.x() * (1 - abs(joy_left.y()) * 0.5f); // Left/right on right joystick

        float throttle_left, throttle_right;

        if (throttle == 0.0f && steering != 0.0f)
        {
            // In-place turning: wheels spin opposite directions
            throttle_left = steering * max_velocity;
            throttle_right = -steering * max_velocity;
        }
        else
        {
            // Normal turning: adjust throttle per wheel
            float turn_scale = steering * abs(throttle);
            throttle_left = throttle + turn_scale;
            throttle_right = throttle - turn_scale;
        }

        ControlPacket cmd{};
        cmd.control_mode = control_mode;
        cmd.throttle_left = throttle_left; // m/s
        cmd.throttle_right = throttle_right;
        cmd.max_velocity = max_velocity; // Only used in AUTO mode
        radio.send(cmd);
    }

    bool timeout = radio.update();

    TelemetryPacket pkt;

    if (radio.recieve(pkt))
    {
        if (Serial)
        {
            const uint16_t size = sizeof(pkt);

            Serial.write((uint8_t *)&TELEMETRY_HEADER, sizeof(TELEMETRY_HEADER));
            Serial.write((uint8_t *)&size, sizeof(size));
            Serial.write((uint8_t *)&pkt, size);
        }
    }

    // ---- UI ----
    auto &gfx = Screen::instance().gfx();
    gfx.clearDisplay();

    if (in_config_menu)
    {
        gfx.setTextSize(1);
        gfx.setCursor(0, 0);
        gfx.printf("Max Velocity: %.2f", max_velocity);
    }
    else
    {                // Default control menu
        if (timeout) // Prioritize showing timeout error over no serial error, since no serial may just mean "not plugged in yet"
        {
            Screen::instance().drawCenteredText("TIMEOUT", 0, 0, 128, 32, 2);
        }
        else
        {
            if (!Serial)
            {
                Screen::instance().drawCenteredText("NO SERIAL", 0, 0, 128, 32, 1);
            }
        }

        joy_left.draw(0, 32, 32, 32);
        joy_right.draw(96, 32, 32, 32);

        // Draw MODE label in top center box
        Screen::instance().drawCenteredText("MODE", 32, 32, 64, 16, 1);

        // Draw control mode value in bottom center box
        const char *mode_str = "";
        switch (control_mode)
        {
        case 0:
            mode_str = "IDLE";
            break;
        case 1:
            mode_str = "REMO";
            break;
        case 2:
            mode_str = "AUTO";
            break;
        }
        Screen::instance().drawCenteredText(mode_str, 32, 48, 64, 16, 2);
    }
    gfx.display();
    delay(10);
}
