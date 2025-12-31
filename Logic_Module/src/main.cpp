#include <Arduino.h>
#include "ota.h"
#include "control.h"

void setup() {
    delay(1000);
    Serial.begin(115200);
    Serial.println("Booting Pathfinder ESP32...");

    setup_OTA();
    setup_control();

    Serial.println("Boot sequence complete!");
}

void loop() {
    // Nothing here - everything runs in tasks
    vTaskDelay(portMAX_DELAY);
}
