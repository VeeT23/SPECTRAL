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


void handlePacket(const ControlPacket& pkt)
{
    latest_control_pkt = pkt;        // copy
    control_pkt_pending = true;      // signal
}


/**
 * Main boot sequence
 * see global_state.h for config
 */

void setup()
{
    delay(100);
    // ---------- SERIAL INIT ----------
    Serial.begin(115200);
    Serial.println("Booting...");


    // ---------- CONFIGURE PINS ---------
    Serial.println("Configuring Pins...");
    PINS::configure_pins();
    

    // ---------- I2C INIT ----------
    Serial.println("Initializing I2C...");
    Wire.begin(PINS::SDA, PINS::SCL);

    // ---------- SCREEN INIT ----------
    Serial.println("Initializing OLED...");
    Screen::instance().init(0x3C);

    // ---------- RADIO INIT ----------
    Serial.println("Initializing Radio...");
    auto& radio = RadioInstance();
    radio.onPacket  = handlePacket;
    if (!radio.begin(CONTROLLER_MAC, 1)) {
        Serial.println("Radio init failed!");
        while (true) { delay(1000); }
    }

    // ---------- CAN INIT ----------
    Serial.println("Initializing CAN Bus...");
    if (!CANBus::instance().begin(PINS::CAN_TX, PINS::CAN_RX, 500000))
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
