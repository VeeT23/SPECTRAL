#include <WiFi.h>
#include <ArduinoOTA.h>
#include "private.h" //Network stuff

void otaTask(void* arg) {
    for (;;) {
        ArduinoOTA.handle();
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}

void setup_OTA() {
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASS); // Defined in private.h

    // Try to connect, but fall-back on failure
    Serial.println("Connecting to Wi-Fi");
    unsigned long startAttempt = millis();
    const unsigned long wifiTimeout = 5000; // 5 seconds timeout

    while (WiFi.status() != WL_CONNECTED && millis() - startAttempt < wifiTimeout) {
        Serial.print(".");
        delay(500);
    }

    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("Failed to connect to Wi-Fi. OTA disabled.");
        return; // Skip OTA setup
    }

    Serial.println(WiFi.localIP());

    Serial.println("Wi-Fi connected. Starting OTA...");

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

    xTaskCreatePinnedToCore(
        otaTask,
        "ota",
        8192,
        nullptr,
        1,
        nullptr,
        0
    );

    Serial.println("OTA ready!");

}