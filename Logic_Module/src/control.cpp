#include "control.h"
#include "pin_def.h"

// ---------- CONFIG ----------
constexpr uint32_t CONTROL_HZ = 1000;
constexpr TickType_t CONTROL_PERIOD = pdMS_TO_TICKS(1000 / CONTROL_HZ);

constexpr uint8_t NUM_MODULES = 1;
constexpr uint8_t SENSORS_PER_MODULE = 8;
constexpr uint8_t TOTAL_SENSORS = NUM_MODULES * SENSORS_PER_MODULE;
constexpr TickType_t PRINT_PERIOD = pdMS_TO_TICKS(100);

// ordered S0-0..S0-7, S1-0..S1-7, ...
static uint16_t ir_raw[TOTAL_SENSORS];

// ---------- CONTROL LOOP TASK ----------

static Radio_t* radioPtr = nullptr;

inline void setMuxAddress(uint8_t addr)
{
    digitalWrite(PINS::A0, addr & 0x01);
    digitalWrite(PINS::A1, addr & 0x02);
    digitalWrite(PINS::A2, addr & 0x04);
}

void controlTask(void* arg)
{
    TickType_t lastWake = xTaskGetTickCount();
    TickType_t lastTelemetry = lastWake;
    TickType_t lastPrint = lastWake;

    constexpr TickType_t TELEMETRY_PERIOD = pdMS_TO_TICKS(50);

    for (;;) {

        for (uint8_t sensor = 0; sensor < SENSORS_PER_MODULE; sensor++)
        {
            setMuxAddress(sensor);

            // ---- MUX SETTLE ----
            ets_delay_us(20);

            // ---- POLL ALL 5 MODULES ----
            ir_raw[0 * SENSORS_PER_MODULE + sensor] = analogRead(PINS::S0);
            //ir_raw[1 * SENSORS_PER_MODULE + sensor] = analogRead(PINS::S1);
           // ir_raw[2 * SENSORS_PER_MODULE + sensor] = analogRead(PINS::S2);
           // ir_raw[3 * SENSORS_PER_MODULE + sensor] = analogRead(PINS::S3);
            //ir_raw[4 * SENSORS_PER_MODULE + sensor] = analogRead(PINS::S4);
        }
        
        TickType_t now = xTaskGetTickCount();
        if (now - lastPrint >= PRINT_PERIOD)
        {
            lastPrint = now;

            Serial.print("IR: ");
            for (uint8_t i = 0; i < TOTAL_SENSORS; i++)
            {
                Serial.print(ir_raw[i]);
                if (i < TOTAL_SENSORS - 1)
                    Serial.print(',');
            }
            Serial.println();
        }

        // ---- TELEMETRY ----
        /*
        TickType_t now = xTaskGetTickCount();
        if (now - lastTelemetry >= TELEMETRY_PERIOD) {
            lastTelemetry = now;

            TelemetryPacket t{};
            t.battery_v = 12.3f;
            t.flags = 0;

            radioPtr->send(t);
        }

        radioPtr->update();
        */
        vTaskDelayUntil(&lastWake, CONTROL_PERIOD);
    }
}

void setup_control(Radio_t* radio)
{
    radioPtr = radio;

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
