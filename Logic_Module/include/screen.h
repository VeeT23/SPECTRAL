#pragma once
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include "splash.h"

class Screen {
public:
    static Screen& instance() {
        static Screen instance;
        return instance;
    }

    // NOTE: I2C must be initialized prior
    bool init(uint8_t addr) {
        if (initialized)
            return true;
        

        if (!display.begin(SSD1306_SWITCHCAPVCC, addr)) {
            Serial.println("SSD1306 allocation failed");
            return false;
        }

        display.clearDisplay();
        display.setTextSize(1);
        display.setTextColor(SSD1306_WHITE);
        display.setCursor(0, 0);
        display.drawBitmap(0, 0, SPLASH, 128, 64, WHITE);
        display.display();

        initialized = true;
        Serial.println("SSD1306 allocation success");
        return true;
    }

    Adafruit_SSD1306& gfx() {
        return display;
    }
    void clear()
    {
        gfx().clearDisplay();
    }
    void show()
    {
        gfx().display();
    }
private:
    Screen()
        : display(128, 64, &Wire, -1) {}

    Screen(const Screen&) = delete;
    Screen& operator=(const Screen&) = delete;

    bool initialized = false;
    Adafruit_SSD1306 display;
};
