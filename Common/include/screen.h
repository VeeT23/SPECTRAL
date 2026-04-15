#pragma once
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

class Screen {
public:
    static Screen& instance() {
        static Screen instance;
        return instance;
    }

    bool init(uint8_t addr) {
        if (initialized)
            return true;

        Wire.begin(SDA, SCL);

        if (!display.begin(SSD1306_SWITCHCAPVCC, addr)) {
            Serial.println("SSD1306 allocation failed");
            return false;
        }

        display.clearDisplay();
        display.setTextSize(1);
        display.setTextColor(SSD1306_WHITE);
        display.setCursor(0, 0);
        display.display();

        initialized = true;
        Serial.println("SSD1306 allocation success");
        return true;
    }

    Adafruit_SSD1306& gfx() {
        return display;
    }

    void drawCenteredText(const char* text, int16_t x, int16_t y, int16_t w, int16_t h, uint8_t textSize) {
        display.setTextSize(textSize);
        
        int16_t x1, y1;
        uint16_t textWidth, textHeight;
        display.getTextBounds((char*)text, 0, 0, &x1, &y1, &textWidth, &textHeight);
        
        int16_t centerX = x + (w - textWidth) / 2;
        int16_t centerY = y + (h - textHeight) / 2;
        
        display.setCursor(centerX, centerY);
        display.println(text);
    }

private:
    Screen()
        : display(128, 64, &Wire, -1) {}  // <-- constructed once, statically

    Screen(const Screen&) = delete;
    Screen& operator=(const Screen&) = delete;

    bool initialized = false;
    Adafruit_SSD1306 display;
};
