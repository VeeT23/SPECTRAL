#include <Arduino.h>
#include "control.h"
#include "screen.h"
#include "pin_def.h"
#include "buzzer.h"
#include "radio.h"
#include "packet.h"
#include "can_bus.h"

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

    // ---------- CAN INIT ----------
    if (!CANBus::instance().begin(PINS::CAN_TX, PINS::CAN_RX, 250000))
    {
        Serial.println("CAN init failed!");
        while (true) { delay(1000); }
    }
    twai_status_info_t status;
    twai_get_status_info(&status);

    Serial.print("CAN state: ");
    Serial.println(status.state);  // 0=STOPPED, 1=RUNNING, 2=BUS_OFF

    Serial.println("CAN started");

    uint8_t dummy[1] = {0xAA};
bool ok = CANBus::instance().canSend(0x123, dummy, 1);
Serial.print("Raw CAN send: "); Serial.println(ok ? "OK" : "FAIL");


    Serial.println("Boot sequence complete!");
}

void loop() {
    // Nothing here - everything runs in tasks
    vTaskDelay(portMAX_DELAY);
}
