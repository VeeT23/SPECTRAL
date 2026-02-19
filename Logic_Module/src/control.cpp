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

void process_ir_data()
{
    uint16_t filtered[TOTAL_SENSORS];

    if (TOTAL_SENSORS == 0)
        return;

    if (TOTAL_SENSORS == 1)
    {
        filtered[0] = ir_raw[0];
    }
    else
    {
        // First element
        filtered[0] = (ir_raw[0] + ir_raw[1]) / 2;

        // Middle elements
        for (uint8_t i = 1; i < TOTAL_SENSORS - 1; i++)
        {
            filtered[i] = (ir_raw[i - 1] + ir_raw[i] + ir_raw[i + 1]) / 3;
        }

        // Last element
        filtered[TOTAL_SENSORS - 1] =
            (ir_raw[TOTAL_SENSORS - 2] + ir_raw[TOTAL_SENSORS - 1]) / 2;
    }

    // Threshold masking
    for (uint8_t i = 0; i < TOTAL_SENSORS; i++)
    {
        ir_processed[i] = (filtered[i] > IR_THRESHOLD);
    }
}

int8_t get_error()
{
    if (TOTAL_SENSORS == 0)
        return INT8_MAX;

    int8_t found_index = -1;

    // Define the two center positions
    int8_t center_left = (TOTAL_SENSORS - 1) / 2;
    int8_t center_right = TOTAL_SENSORS / 2;

    // Search outward symmetrically
    for (int8_t offset = 0; offset <= center_right; offset++)
    {
        if (center_left - offset >= 0 &&
            ir_processed[center_left - offset])
        {
            found_index = center_left - offset;
            break;
        }

        if (center_right + offset < TOTAL_SENSORS &&
            ir_processed[center_right + offset])
        {
            found_index = center_right + offset;
            break;
        }
    }

    if (found_index == -1)
        return INT8_MAX; // No line detected

    // Expand left
    int8_t left = found_index;
    while (left > 0 && ir_processed[left - 1])
        left--;

    // Expand right
    int8_t right = found_index;
    while (right < TOTAL_SENSORS - 1 && ir_processed[right + 1])
        right++;

    // Midpoint of detected span
    int16_t midpoint_times2 = left + right;
    // (left + right) = 2 * midpoint

    // True center scaled by 2
    int16_t center_times2 = TOTAL_SENSORS - 1;

    // Signed error
    int16_t error = midpoint_times2 - center_times2;

    return (int8_t)(error / 2);
}

float pid_update(float error, float dt)
{
    static float integral = 0.0f;
    static float prev_error = 0.0f;

    integral += error * dt;
    float derivative = (error - prev_error) / dt;
    prev_error = error;

    return KP * error + KI * integral + KD * derivative;
}

void controlTask(void *arg)
{
    // ---------- Task Scheduling -----------
    TickType_t lastWake = xTaskGetTickCount();
    TickType_t lastTelemetry = lastWake;
    TickType_t lastDraw = lastWake;

    // ---------- ODrive -----------
    Motor motor_left(2, true); // Inverted left motor
    Motor motor_right(1);

    motor_left.clearErrors();
    motor_right.clearErrors();

    xTaskDelayUntil(&lastWake, pdMS_TO_TICKS(10)); // Wait for ODrives to process clear errors command

    motor_left.enterClosedLoop();
    motor_right.enterClosedLoop();

    motor_left.setVelocity(0);
    motor_right.setVelocity(0);

    motor_left.requestEncoder();
    motor_right.requestEncoder();

    if (!motor_left.waitForEncoder(50))
    {
        Serial.println("Left encoder timeout!");
    }

    if (!motor_right.waitForEncoder(50))
    {
        Serial.println("Right encoder timeout!");
    }

    motor_left.zeroPosition();
    motor_right.zeroPosition();

    int8_t prev_error = 0;
    int8_t valid_error = 0;
    float initial_rotational_offset = 0.0f;
    bool line_lost = false;

    RadioInstance().reset_timeout(); // Reset radio timeout at startup

    float recieved_steering = 0.0f;
    float recieved_velocity = 0.0f;

    for (;;)
    {
        TickType_t ticks = xTaskGetTickCount();
        uint32_t now_ms = ticks * portTICK_PERIOD_MS;

        // =================== LOOP BEGIN ===================

        // ---------- PROCESS RADIO CONTROL ----------

        if (RadioInstance().update())
        {
            Serial.println("Timed out!");
        }

        
        ControlPacket rx;
        if (RadioInstance().recieve(rx))
        {
           recieved_steering = rx.steering;
           recieved_velocity = rx.velocity;
        }

        // ---------- PROCESS CAN ----------
        twai_message_t msg;
        while (CANBus::instance().receive(msg, 0))
        {
            motor_left.processTwaiFrame(msg, now_ms);
            motor_right.processTwaiFrame(msg, now_ms);
        }

        // ---------- PROCESS SENSORS ----------
        poll_sensors();
        process_ir_data();
        int8_t error = get_error(); // returns INT8_MAX if no line detected

        float current_rotational_offset = motor_left.telemetry().position - motor_right.telemetry().position;

        if (error == INT8_MAX && !line_lost) // Line just lost
        {
            line_lost = true;
            Serial.println("Line lost!");

            valid_error = (prev_error < 0) ? -TOTAL_SENSORS : TOTAL_SENSORS; // If no line detected, keep previous error but amplified
            initial_rotational_offset = current_rotational_offset;           // Update initial offset to current when line is lost
        }
        else if (error != INT8_MAX) // Line found again
        {
            line_lost = false;
            valid_error = error;
            prev_error = error;
        }

        float pid_output = pid_update(valid_error / static_cast<float>(TOTAL_SENSORS / 2), CONTROL_PERIOD * portTICK_PERIOD_MS / 1000.0f); // Normalize error to [-1, 1] range

        // ---------- UPDATE MOTORS ----------
        if (ENABLE_MOTORS)
        {
            motor_left.setVelocity(MAX_REV + pid_output * MAX_REV);
            motor_right.setVelocity(MAX_REV - pid_output * MAX_REV);
        }
        else
        {
            motor_left.setVelocity(0);
            motor_right.setVelocity(0);
        }

        // ---------- DEBUG ----------
        if (ticks - lastDraw >= DRAW_PERIOD)
        {
            Screen::instance().clear();
            // Serial.printf("Error: %d\n", error);
            // Serial.print("Motor Left - Pos: " + String(motor_left.telemetry().position, 2) + " Vel: " + String(motor_left.telemetry().velocity, 2) + " IsAlive: " + String(motor_left.alive(now_ms)));
            // Serial.println(" | Motor Right - Pos: " + String(motor_right.telemetry().position, 2) + " Vel: " + String(motor_right.telemetry().velocity, 2) + " IsAlive: " + String(motor_right.alive(now_ms)));
            for (uint8_t i = 0; i < TOTAL_SENSORS; i++)
            {
                Screen::instance().gfx().drawRect((TOTAL_SENSORS - i) * 3, 0, 2, ir_processed[i] ? 8 : 0, SSD1306_WHITE);
            }
            Screen::instance().gfx().drawCircle((64 - (128 / TOTAL_SENSORS * error)), 12, 3, SSD1306_WHITE);

            Screen::instance().gfx().drawLine(64, 32, 64 + recieved_steering * 64, 32+recieved_velocity*32, SSD1306_WHITE);
            // Screen::instance().gfx().setCursor(0, 30);
            // Screen::instance().gfx().print("Rot. offset: " + String(current_rotational_offset - initial_rotational_offset, 2));
            Screen::instance().show();

            lastDraw = ticks;
        }

        // --------- SEND TELEMETRY ----------
        if (ticks - lastTelemetry >= TELEMETRY_PERIOD)
        {
            TelemetryPacket tx{};
            tx.velocity = (motor_left.telemetry().velocity + motor_right.telemetry().velocity) / 2.0f;
            tx.steering = current_rotational_offset - initial_rotational_offset;
            memcpy(tx.ir_raw, ir_raw, sizeof(ir_raw));
            memcpy(tx.ir_processed, ir_processed, sizeof(ir_processed));

            RadioInstance().send(tx);
            lastTelemetry = ticks;
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
