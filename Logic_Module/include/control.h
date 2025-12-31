#include <Arduino.h>

// ---------- CONFIG ----------
constexpr uint32_t CONTROL_HZ = 1000;
constexpr TickType_t CONTROL_PERIOD = pdMS_TO_TICKS(1000 / CONTROL_HZ);

// ---------- CONTROL LOOP TASK ----------

void controlTask(void* arg)
{
    TickType_t lastWake = xTaskGetTickCount();

    for (;;) {
        // control loop

        vTaskDelayUntil(&lastWake, CONTROL_PERIOD);
    }
}

void setup_control()
{
    xTaskCreatePinnedToCore(
        controlTask,
        "control",
        8192,
        nullptr,
        3,
        nullptr,
        1
    );
}