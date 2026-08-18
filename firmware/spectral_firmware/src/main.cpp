#include <Arduino.h>
#include "pin_def.h" // Pin configs
// Debug
#include "screen.h"
#include "buzzer.h"
// Peripherals
#include "global_state.h" //Holds radio + global data
#include "can_bus.h"
// Main loop
#include "control.h"

#include "splash.h"

/**
 * Main boot sequence
 * see global_state.h for config
 */

void setup()
{
    delay(100);
    // ---------- SERIAL INIT ----------
    Serial.begin(SERIAL_BAUD);
    Serial.println("Booting...");


    // ---------- CONFIGURE PINS ---------
    Serial.println("Configuring Pins...");
    PINS::configure_pins();
    

    // ---------- I2C INIT ----------
    Serial.println("Initializing I2C...");
    Wire.begin(PINS::SDA, PINS::SCL);
    Wire.setClock(400000);
    Wire.setTimeOut(5);

    // ---------- SCREEN INIT ----------
    Serial.println("Initializing OLED...");
    Screen::instance().init(0x3C);
    Screen::instance().gfx().clearDisplay();
    Screen::instance().gfx().drawBitmap(0, 0, SPLASH, 128, 64, SSD1306_WHITE);
    Screen::instance().gfx().display();

    // ---------- RADIO INIT ----------
    Serial.println("Initializing Radio...");
    auto& radio = RadioInstance();
    if (!radio.begin(CONTROLLER_MAC, RX_TIMEOUT_MS, RADIO_DEBUG)) {
        Serial.println("Radio init failed!");
        while (true) { delay(1000); }
    }

    // ---------- CAN INIT ----------
    Serial.println("Initializing CAN Bus...");
    if (!CANBus::instance().begin(PINS::CAN_TX, PINS::CAN_RX, CAN_BITRATE))
    {
        Serial.println("CAN init failed!");
        while (true) { delay(1000); }
    }
    if (CANBus::instance().test_can())
    {
        Serial.println("CAN TX failed!");
        while (true) { delay(1000); }
    }
    // ---------- BOOT FINISH ----------
    Serial.println("Boot sequence complete!");
    Buzzer::beep(2000,100);
    delay(2000);
    setup_control();
}

void loop()
{
    vTaskDelay(portMAX_DELAY);
}
