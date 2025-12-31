#include <Arduino.h>
#include <WiFi.h>
#include <ArduinoOTA.h>
#include "private.h" //Network stuff

// ---------- CONFIG ----------
constexpr uint32_t CONTROL_HZ = 1000;
constexpr TickType_t CONTROL_PERIOD = pdMS_TO_TICKS(1000 / CONTROL_HZ);

// Flag to know if OTA is active
bool otaEnabled = false;

// ---------- OTA SETUP ----------

void setupOTA() {
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASS); // Defined in private.h

    // Try to connect, but do NOT restart on failure
    Serial.println("Connecting to Wi-Fi");
    unsigned long startAttempt = millis();
    const unsigned long wifiTimeout = 5000; // 5 seconds timeout

    while (WiFi.status() != WL_CONNECTED && millis() - startAttempt < wifiTimeout) {
        Serial.print(".");
        delay(500);
    }

    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("Failed to connect to Wi-Fi. OTA disabled.");
        otaEnabled = false;
        return; // Skip OTA setup
    }

    Serial.println(WiFi.localIP());

    Serial.println("Wi-Fi connected. Starting OTA...");
    otaEnabled = true;

    ArduinoOTA.setHostname("pathfinder-esp32");

    ArduinoOTA.onStart([]() {
        Serial.println("OTA Start - stopping motors");
        // Housekeeping
    });

    ArduinoOTA.onEnd([]() {
        Serial.println("OTA End");
    });

    ArduinoOTA.onError([](ota_error_t error) {
        Serial.printf("OTA Error[%u]: ", error);
        if (error == OTA_AUTH_ERROR) Serial.println("Auth Failed");
        else if (error == OTA_BEGIN_ERROR) Serial.println("Begin Failed");
        else if (error == OTA_CONNECT_ERROR) Serial.println("Connect Failed");
        else if (error == OTA_RECEIVE_ERROR) Serial.println("Receive Failed");
        else if (error == OTA_END_ERROR) Serial.println("End Failed");
    });

    ArduinoOTA.begin();
    Serial.println("OTA ready!");
}

void otaTask(void* arg) {
    for (;;) {
        if (otaEnabled) {
            ArduinoOTA.handle();
        }
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}

// ---------- CONTROL LOOP TASK ----------
void controlTask(void* arg) {
    TickType_t lastWake = xTaskGetTickCount();

    for (;;) {
        // control loop

        vTaskDelayUntil(&lastWake, CONTROL_PERIOD);
    }
}

// ---------- SETUP / LOOP ----------
void setup() {
    delay(1000);
    Serial.begin(115200);
    Serial.println("Booting Pathfinder ESP32...");

    // Setup OTA (will skip if Wi-Fi fails)
    setupOTA();

    // Create control loop task on core 1
    xTaskCreatePinnedToCore(
        controlTask,
        "control",
        8192,
        nullptr,
        3,
        nullptr,
        1
    );

    // Create OTA task on core 0 (runs but skips if disabled)
    xTaskCreatePinnedToCore(
        otaTask,
        "ota",
        8192,
        nullptr,
        1,
        nullptr,
        0
    );

    Serial.println("Boot sequence complete!");
}

void loop() {
    // Nothing here - everything runs in tasks
    vTaskDelay(portMAX_DELAY);
}
