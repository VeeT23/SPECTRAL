#include <Arduino.h>
#include "control.h"
#include "screen.h"
#include "pin_def.h"
#include "buzzer.h"
#include "radio.h"
#include "packet.h"

uint8_t controllerMAC[] = { 0xD8, 0x3B, 0xDA, 0x46, 0x57, 0x80 };
Radio<TelemetryPacket, ControlPacket> radio;

void setup() {
    delay(1000);
    Wire.begin(PINS::SDA, PINS::SCL);
    Serial.begin(115200);

    Serial.println("Booting...");

    Screen::instance().init(0x3C);
    Buzzer::beep(2000,100);

    /*
    if (!radio.begin(controllerMAC)) {
        Serial.println("Radio init failed!");
        while (true);
    }

    radio.onPacket = [](const ControlPacket& cmd) {
        Serial.print("L: ");
        Serial.print(cmd.left_vel);
        Serial.print(" R: ");
        Serial.println(cmd.right_vel);
    };

    radio.onTimeout = []() {
        Serial.println("RADIO TIMEOUT");
        // stopMotors();
    };
    */
    setup_control(&radio);

    Serial.println("Boot sequence complete!");
}

void loop() {
    // Nothing here - everything runs in tasks
    vTaskDelay(portMAX_DELAY);
}
