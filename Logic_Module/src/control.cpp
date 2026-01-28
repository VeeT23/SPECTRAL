#include "control.h"
#include "pin_def.h"
#include "motor.h"

// ---------- CONFIG ----------
constexpr uint32_t CONTROL_HZ = 1000;
constexpr TickType_t CONTROL_PERIOD = pdMS_TO_TICKS(1000 / CONTROL_HZ);

constexpr uint8_t NUM_MODULES = 5;
constexpr uint8_t SENSORS_PER_MODULE = 8;
constexpr uint8_t TOTAL_SENSORS = NUM_MODULES * SENSORS_PER_MODULE;
constexpr TickType_t PRINT_PERIOD = pdMS_TO_TICKS(100);

// ordered S0-0..S0-7, S1-0..S1-7, ...
static uint16_t ir_raw[TOTAL_SENSORS];

// ---------- CONTROL LOOP TASK ----------

static Radio_t *radioPtr = nullptr;

inline void setMuxAddress(uint8_t addr)
{
    digitalWrite(PINS::A0, addr & 0x01);
    digitalWrite(PINS::A1, addr & 0x02);
    digitalWrite(PINS::A2, addr & 0x04);
}

void controlTask(void *arg)
{
    TickType_t lastWake = xTaskGetTickCount();
    TickType_t lastTelemetry = lastWake;
    TickType_t lastPrint = lastWake;

    constexpr TickType_t TELEMETRY_PERIOD = pdMS_TO_TICKS(50);

    Motor motor_left(1);
    Motor motor_right(2);

    // ---------- GIVE ODRIVE TIME ----------
    vTaskDelay(pdMS_TO_TICKS(100));

    // ---------- ENTER CLOSED LOOP ----------
    motor_left.enterClosedLoop();
    motor_right.enterClosedLoop();

    TickType_t start = xTaskGetTickCount();
    while (
        !motor_left.alive(xTaskGetTickCount()) ||
        !motor_right.alive(xTaskGetTickCount()))
    {
        if (xTaskGetTickCount() - start > pdMS_TO_TICKS(1000))
        {
            Serial.println("ODrive heartbeat timeout");
            break;
        }
        vTaskDelay(pdMS_TO_TICKS(10));
    }

    constexpr float TEST_VELOCITY = 1.0f; // rev/s

    for (;;)
    {

        motor_left.setVelocity(TEST_VELOCITY);
        motor_right.setVelocity(TEST_VELOCITY);

        if (motor_left.alive(xTaskGetTickCount()))
            Serial.println("Left motor heartbeat OK");
        else
            Serial.println("Left motor NO heartbeat");

        if (motor_right.alive(xTaskGetTickCount()))
            Serial.println("Right motor heartbeat OK");
        else
            Serial.println("Right motor NO heartbeat");

        /*
        for (uint8_t sensor = 0; sensor < SENSORS_PER_MODULE; sensor++)
        {
            setMuxAddress(sensor);
            ets_delay_us(20);

            ir_raw[0 * SENSORS_PER_MODULE + sensor] = analogRead(PINS::S0);
            ir_raw[1 * SENSORS_PER_MODULE + sensor] = analogRead(PINS::S1);
            ir_raw[2 * SENSORS_PER_MODULE + sensor] = analogRead(PINS::S2);
            ir_raw[3 * SENSORS_PER_MODULE + sensor] = analogRead(PINS::S3);
            ir_raw[4 * SENSORS_PER_MODULE + sensor] = analogRead(PINS::S4);
        }

        TickType_t now = xTaskGetTickCount();
        if (now - lastPrint >= PRINT_PERIOD)
        {
            lastPrint = now;

            Serial.print("IR: ");
            for (uint8_t i = 0; i < TOTAL_SENSORS; i++)
            {
                Serial.print(ir_raw[i]);
                if (i < TOTAL_SENSORS - 1) Serial.print(',');
            }
            Serial.println();
        }
            */
        static uint32_t lastStatusPrint = 0;
        uint32_t now_ms = millis();

        if (now_ms - lastStatusPrint > 500)
        {
            lastStatusPrint = now_ms;

            Serial.print("[CTRL] L alive=");
            Serial.print(motor_left.alive(xTaskGetTickCount()));
            Serial.print(" R alive=");
            Serial.print(motor_right.alive(xTaskGetTickCount()));
            Serial.println();
        }

        vTaskDelayUntil(&lastWake, CONTROL_PERIOD);
    }
}

void setup_control(Radio_t *radio)
{
    radioPtr = radio;

    xTaskCreatePinnedToCore(
        controlTask,
        "control",
        8192,
        nullptr,
        3,
        nullptr,
        1);
}
