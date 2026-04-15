#include "control.h"
#include "pin_def.h"
#include "motor.h"
#include "screen.h"
#include "global_state.h"
#include "config.h"
#include "sensor_array.h"

struct OdometryState
{
    float x = 0.0f;     // meters
    float y = 0.0f;     // meters
    float theta = 0.0f; // radians

    float distance = 0.0f; // total arc length traveled (meters)

    float prev_rev_L = 0.0f;
    float prev_rev_R = 0.0f;
};

inline void updateOdometry(
    OdometryState &state,
    float current_rev_L,
    float current_rev_R)
{
    // ---- Compute delta revolutions ----
    float delta_rev_L = current_rev_L - state.prev_rev_L;
    float delta_rev_R = current_rev_R - state.prev_rev_R;

    if (fabs(delta_rev_L) > 5 || fabs(delta_rev_R) > 5)
    {
        delta_rev_L = 0;
        delta_rev_R = 0;
    }

    state.prev_rev_L = current_rev_L;
    state.prev_rev_R = current_rev_R;

    // ---- Convert revolutions -> linear distance (meters) ----
    float dL = delta_rev_L * WHEEL_CIRCUMFERENCE_M;
    float dR = delta_rev_R * WHEEL_CIRCUMFERENCE_M;

    // ---- Differential drive kinematics ----
    float d = 0.5f * (dL + dR);                 // forward arc length
    float dtheta = (dR - dL) / WHEEL_SPACING_M; // radians

    // Accumulate arc length for distance traveled
    state.distance += d;

    // ---- Midpoint integration ----
    float theta_mid = state.theta + 0.5f * dtheta;

    state.x += d * cosf(theta_mid);
    state.y += d * sinf(theta_mid);

    state.theta += dtheta;
}

void controlTask(void *arg)
{
    // ---------- Task Scheduling -----------
    TickType_t lastWake = xTaskGetTickCount();
    TickType_t lastTelemetry = lastWake;
    TickType_t lastDraw = lastWake;
    TickType_t lastIdle = lastWake;
    TickType_t activeDuration = 0;

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

    float distance = 0.0f;

    OdometryState odom;

    bool line_lost = false;

    RadioInstance().reset_timeout(); // Reset radio timeout at startup

    float throttle_left = 0.0f;
    float throttle_right = 0.0f;
    uint8_t current_mode = 0;
    for (;;)
    {
        TickType_t ticks = xTaskGetTickCount();
        uint32_t now_ms = ticks * portTICK_PERIOD_MS;

        // =================== LOOP BEGIN ===================

        // ---------- PROCESS RADIO CONTROL ----------

        bool radio_timed_out = RadioInstance().update();
        if (radio_timed_out)
        {
            Serial.println("Timed out!");
            current_mode = 0;
        }

        ControlPacket rx;
        if (RadioInstance().recieve(rx))
        {
            if (current_mode != rx.control_mode && rx.control_mode == 2) // Just entered line following mode, reset odometry and PID state
            {
                lastIdle = ticks;
                motor_left.zeroPosition();
                motor_right.zeroPosition();
                odom = OdometryState{};
                odom.prev_rev_L = motor_left.telemetry().revolutions;
                odom.prev_rev_R = motor_right.telemetry().revolutions;
                Serial.println("Entered line following mode, resetting odometry and PID state");
            }

            current_mode = rx.control_mode;
            throttle_left = rx.throttle_left;
            throttle_right = rx.throttle_right;
        }

        // ---------- PROCESS CAN ----------
        twai_message_t msg;
        while (CANBus::instance().receive(msg, 0))
        {
            motor_left.processTwaiFrame(msg, now_ms);
            motor_right.processTwaiFrame(msg, now_ms);
        }

        // ---------- PROCESS SENSORS ----------

        for (int i = 0; i < SENSORS_PER_MODULE; i++)
        {
            poll_sensors();
        }

        process_ir_data();
        int8_t error = get_error(0.5f); // returns INT8_MAX if no line detected

        // ---------- UPDATE CONTROL STATE ----------
        updateOdometry(
            odom,
            motor_left.telemetry().revolutions,
            motor_right.telemetry().revolutions);

        if (error == INT8_MAX && !line_lost) // Line just lost
        {
            line_lost = true;
            Serial.println("Line lost!");

            valid_error = (prev_error < 0) ? -TOTAL_SENSORS : TOTAL_SENSORS; // If no line detected, keep previous error but amplified
        }
        else if (error != INT8_MAX) // Line found again
        {
            line_lost = false;
            valid_error = error;
            prev_error = error;
        }
        float pid_output = 0.0F;
        if (current_mode == 2)
        {
            activeDuration = ticks - lastIdle;
            pid_output = pid_update(valid_error / static_cast<float>(TOTAL_SENSORS / 2), CONTROL_PERIOD * portTICK_PERIOD_MS / 1000.0f); // Normalize error to [-1, 1] range
        }
        // ---------- UPDATE MOTORS ----------

        switch (current_mode)
        {
        case 0: // Idle
        {
            motor_left.enterIdle();
            motor_right.enterIdle();
            break;
        }
        case 1: // Remote control
        {
            motor_left.enterClosedLoop();
            motor_right.enterClosedLoop();

            // Convert throttle from m/s to rev/s
            float set_rev_left = throttle_left / WHEEL_CIRCUMFERENCE_M;
            float set_rev_right = throttle_right / WHEEL_CIRCUMFERENCE_M;
            
            motor_left.setVelocity(set_rev_left);
            motor_right.setVelocity(set_rev_right);
            break;
        }
        case 2: // Line following
        {
            motor_left.enterClosedLoop();
            motor_right.enterClosedLoop();

            if (ENABLE_MOTORS)
            {
                float set_rev = rx.max_velocity / WHEEL_CIRCUMFERENCE_M; // Calculate from max_velocity
                motor_left.setVelocity(set_rev + pid_output * set_rev);
                motor_right.setVelocity(set_rev - pid_output * set_rev);
            }
            else
            {
                motor_left.setVelocity(0);
                motor_right.setVelocity(0);
            }
            break;
        }
        }

        // ---------- DEBUG ----------
        if (ticks - lastDraw >= DRAW_PERIOD)
        {
            Screen::instance().gfx().clearDisplay();

            if (radio_timed_out)
            {
                Screen::instance().gfx().setCursor(0, 10);
                Screen::instance().drawCenteredText("NO SIGNAL",0,0,128,64,2);
            }
            else
            {
                Screen::instance().gfx().setTextSize(1);
                for (uint8_t i = 0; i < TOTAL_SENSORS; i++)
                {
                    Screen::instance().gfx().drawRect((TOTAL_SENSORS - i) * 3, 0, 2, ir_processed[i] ? 8 : 0, SSD1306_WHITE);
                }
                Screen::instance().gfx().drawCircle((64 - (128 / TOTAL_SENSORS * error)), 12, 3, SSD1306_WHITE);

                switch (current_mode)
                {
                case 0:
                    Screen::instance().gfx().setCursor(0, 20);
                    Screen::instance().gfx().print("Mode: Idle");
                    break;
                case 1:
                    Screen::instance().gfx().setCursor(0, 20);
                    Screen::instance().gfx().print("Mode: Remote");
                    break;
                case 2:
                    Screen::instance().gfx().setCursor(0, 20);
                    Screen::instance().gfx().print("Mode: Line Follow");
                    break;
                }

                Screen::instance().gfx().setCursor(0, 35);
                Screen::instance().gfx().printf("ThrL: %.2f", throttle_left);
                Screen::instance().gfx().setCursor(0, 45);
                Screen::instance().gfx().printf("ThrR: %.2f", throttle_right);
            }
            Screen::instance().gfx().display();
            lastDraw = ticks;
        }

        // --------- SEND TELEMETRY ----------
        if (ticks - lastTelemetry >= TELEMETRY_PERIOD)
        {
            TelemetryPacket tx{};

            tx.ticks_since_idle = activeDuration;

            // Average wheel velocity
            float avg_rev_per_sec =
                (motor_left.telemetry().velocity +
                 motor_right.telemetry().velocity) *
                0.5f;

            // Convert rev/s → m/s
            tx.velocity = avg_rev_per_sec * WHEEL_CIRCUMFERENCE_M;

            tx.steering = odom.theta * (180.0f / PI); // Convert radians → degrees

            // Copy raw IR
            memcpy(tx.ir_raw, ir_raw, sizeof(tx.ir_raw));

            // Pack 40 bools into 64-bit bitfield
            uint64_t packed = 0;

            for (uint8_t i = 0; i < 40; i++)
            {
                if (ir_processed[i])
                {
                    packed |= (1ULL << i);
                }
            }

            tx.packed_ir_processed = packed;

            tx.line_error = valid_error;
            tx.pid_output = pid_output;

            tx.distance = odom.distance; // Approximate distance traveled (relative to start)
            tx.approx_x = odom.x;
            tx.approx_y = odom.y;

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
