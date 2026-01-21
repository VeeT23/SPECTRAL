#pragma once

#include <Arduino.h>
#include <math.h>
#include "screen.h"

class Joystick
{
public:
    Joystick(uint8_t pinX, uint8_t pinY, uint8_t pinButton, bool invertX = false, bool invertY = false)
        : xPin(pinX), yPin(pinY), buttonPin(pinButton), invertX(invertX), invertY(invertY)
    {
        pinMode(buttonPin, INPUT_PULLUP);
    }

     void poll()
    {
        // Read and map to [-1, 1]
        float rawX = map12bitToFloat(analogRead(xPin));
        float rawY = map12bitToFloat(analogRead(yPin));

        // Apply optional inversion
        joy_x = invertX ? -rawX : rawX;
        joy_y = invertY ? -rawY : rawY;

        // Button state
        button = (digitalRead(buttonPin) == LOW);

        // Constrain to valid range and circle
        joy_x = constrain(joy_x, -1.0f, 1.0f);
        joy_y = constrain(joy_y, -1.0f, 1.0f);
        constrainToCircle(joy_x, joy_y);
    }

    void draw(int xOffset, int yOffset)
    {
        Adafruit_SSD1306& display = Screen::instance().gfx();

        constexpr int halfSize     = 32;
        constexpr int maxDotRadius = 3;
        constexpr int minDotRadius = 1;
        constexpr float deadzone   = 0.15f;

        const int cx = xOffset + halfSize;
        const int cy = yOffset + halfSize;

        float mag = hypotf(joy_x, joy_y);
        int dotR  = computeDotRadius(mag, deadzone, minDotRadius, maxDotRadius);

        int dx = (int)(joy_x * halfSize);
        int dy = (int)(-joy_y * halfSize);
        int dz = (int)(deadzone * halfSize);

        // Outer box
        display.drawRect(xOffset, yOffset,
                         halfSize * 2, halfSize * 2, SSD1306_WHITE);

        // Circular limit
        display.drawCircle(cx, cy, halfSize, SSD1306_WHITE);

        // Deadzone
        display.drawRect(cx - dz, cy - dz, dz * 2, dz * 2, SSD1306_WHITE);

        // Position dot
        display.drawCircle(cx + dx, cy + dy, dotR, SSD1306_WHITE);
        if (button)
            display.fillCircle(cx + dx, cy + dy, dotR, SSD1306_WHITE);
    }

    float x() const { return joy_x; }
    float y() const { return joy_y; }
    bool pressed() const { return button; }

private:
    uint8_t xPin, yPin, buttonPin;
    bool invertX, invertY;

    float joy_x = 0.0f;
    float joy_y = 0.0f;
    bool  button = false;

    static inline float map12bitToFloat(uint16_t value)
    {
        return (static_cast<float>(value) / 4095.0f) * 2.0f - 1.0f;
    }

    static inline void constrainToCircle(float& x, float& y)
    {
        float mag = hypotf(x, y);
        if (mag > 1.0f) {
            x /= mag;
            y /= mag;
        }
    }

    static inline int computeDotRadius(float mag, float deadzone, int minR, int maxR)
    {
        if (mag >= deadzone)
            return maxR;

        float t = mag / deadzone;
        return minR + (int)(t * (maxR - minR));
    }
};
