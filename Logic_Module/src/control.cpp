#include "control.h"
#include "pin_def.h"
#include "motor.h"
#include "screen.h"
#include "global_state.h"
#include "config.h"

inline void setMuxAddress(uint8_t addr)
{
    digitalWrite(PINS::A0, addr & 0x01);
    digitalWrite(PINS::A1, addr & 0x02);
    digitalWrite(PINS::A2, addr & 0x04);
}

void poll_sensors()
{
    ir_raw[0 * SENSORS_PER_MODULE + sensor_idx] = analogRead(PINS::S4);
    ir_raw[1 * SENSORS_PER_MODULE + sensor_idx] = analogRead(PINS::S3);
    ir_raw[2 * SENSORS_PER_MODULE + sensor_idx] = analogRead(PINS::S2);
    ir_raw[3 * SENSORS_PER_MODULE + sensor_idx] = analogRead(PINS::S1);
    ir_raw[4 * SENSORS_PER_MODULE + sensor_idx] = analogRead(PINS::S0);

    // Increment, then set -> lets mux stabalize between ticks while MCU does other things.
    sensor_idx++;
    sensor_idx = (sensor_idx == SENSORS_PER_MODULE) ? 0 : sensor_idx;
    setMuxAddress(sensor_idx);
}

void controlTask(void *arg)
{
    // ---------- Task Scheduling -----------
    TickType_t lastWake = xTaskGetTickCount();
    TickType_t lastTelemetry = lastWake;
    TickType_t lastPrint = lastWake;

    // ---------- ODrive -----------
    Motor motor_left(1);
    Motor motor_right(2);

    motor_left.enterClosedLoop();
    motor_right.enterClosedLoop();

    for (;;)
    {
        TickType_t ticks = xTaskGetTickCount();
        uint32_t now_ms = ticks * portTICK_PERIOD_MS;

        // =================== LOOP BEGIN ===================

        // ---------- PROCESS RADIO ----------

        RadioInstance().update(); // Checks heartbeat

        if (control_pkt_pending)
        {
            Serial.println("Control Packet Received");
            control_pkt_pending = false;

            const ControlPacket &pkt = latest_control_pkt;

            // Example usage
            //motor_left.setVelocity(pkt.left_vel);
            //motor_right.setVelocity(pkt.right_vel);
        }

        // ---------- PROCESS CAN ----------
        twai_message_t msg;
        if (CANBus::instance().receive(msg))
        {
            motor_left.processTwaiFrame(msg, now_ms);
            motor_right.processTwaiFrame(msg, now_ms);
        }

        // ---------- PROCESS SENSORS ----------
        poll_sensors();

        // ---------- UPDATE MOTORS ----------
        motor_left.setVelocity(0);
        motor_right.setVelocity(0);

        // ---------- DEBUG ----------
        if (ticks - lastPrint >= DRAW_PERIOD)
        {
            Screen::instance().clear();
            lastPrint = ticks;
            for (uint8_t i = 0; i < TOTAL_SENSORS; i++)
            {
                Screen::instance().gfx().drawRect((TOTAL_SENSORS - i) * 3, 0, 2, (ir_raw[i] / 4096.0 * 64), SSD1306_WHITE);
            }
            Screen::instance().show();
        }

        // =================== LOOP END ===================
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
        1);
}
