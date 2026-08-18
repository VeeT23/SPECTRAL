#include "control.h"
#include "pin_def.h"
#include "motor.h"
#include "screen.h"
#include "global_state.h"
#include "config.h"
#include "sensor_array.h"
#include "gyro.h"
#include "solution.h"

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

    // Accumulate arc length for distance traveled
    state.distance += d;
}

inline float wrapDegrees180(float angle_deg)
{
    while (angle_deg > 180.0f)
    {
        angle_deg -= 360.0f;
    }

    while (angle_deg <= -180.0f)
    {
        angle_deg += 360.0f;
    }

    return angle_deg;
}

inline float unwrapAngleNearReference(float angle_deg, float reference_deg)
{
    return reference_deg + wrapDegrees180(angle_deg - reference_deg);
}

inline bool hasReachedSolutionAngle(float previous_angle_deg, float target_angle_deg, float heading_deg)
{
    const float previous_unwrapped = unwrapAngleNearReference(previous_angle_deg, heading_deg);
    const float target_unwrapped = unwrapAngleNearReference(target_angle_deg, previous_unwrapped);

    if (target_unwrapped > previous_unwrapped)
    {
        return heading_deg >= target_unwrapped;
    }

    if (target_unwrapped < previous_unwrapped)
    {
        return heading_deg <= target_unwrapped;
    }

    return true;
}

inline bool isDistanceInSpan(float distance_m, const SolutionSpan &span)
{
    const float span_start = (span.start_distance < span.end_distance) ? span.start_distance : span.end_distance;
    const float span_end = (span.start_distance < span.end_distance) ? span.end_distance : span.start_distance;
    return distance_m >= span_start && distance_m <= span_end;
}

inline float getSpanPercentVelocityForDistance(const std::vector<SolutionSpan> &spans, float distance_m)
{
    for (size_t i = 0; i < spans.size(); ++i)
    {
        if (isDistanceInSpan(distance_m, spans[i]))
        {
            return spans[i].percent_velocity;
        }
    }

    return 1.0f;
}

inline void printSolutionDeserializeFailure(const char *label, const SolutionDeserializeDebugInfo &debug_info)
{
    Serial.printf(
        "Failed to decode %s: %s\n",
        label,
        solutionDeserializeErrorToString(debug_info.error));
    Serial.printf(
        "  data_len=%lu expected_len=%lu count=%lu failed_index=%lu\n",
        static_cast<unsigned long>(debug_info.data_length),
        static_cast<unsigned long>(debug_info.expected_length),
        static_cast<unsigned long>(debug_info.element_count),
        static_cast<unsigned long>(debug_info.failed_index));
    Serial.printf(
        "  magic=0x%08lX expected_magic=0x%08lX version=%lu expected_version=%lu\n",
        static_cast<unsigned long>(debug_info.actual_magic),
        static_cast<unsigned long>(debug_info.expected_magic),
        static_cast<unsigned long>(debug_info.actual_version),
        static_cast<unsigned long>(debug_info.expected_version));
}

inline void printDecodedSolutionSpans(const std::vector<SolutionSpan> &spans)
{
    Serial.println("Decoded solution spans:");
    for (size_t i = 0; i < spans.size(); ++i)
    {
        const SolutionSpan &span = spans[i];
        Serial.printf(
            "  [%u] start=%.3f end=%.3f speed=%.3f\n",
            static_cast<unsigned>(i),
            span.start_distance,
            span.end_distance,
            span.percent_velocity);
    }
}

// If odometry distance has exceeded a target point distance by this percent,
// we skip that target and jump to the next one.
constexpr float kSolutionDistanceJumpPercent = 1.0f;
constexpr float kMinLineFollowVelocityMps = 0.50f;

void controlTask(void *arg)
{
    // ---------- Task Scheduling -----------
    TickType_t lastWake = xTaskGetTickCount();
    TickType_t lastTelemetry = lastWake;
    TickType_t lastDraw = lastWake;
    TickType_t lastIdle = lastWake;
    TickType_t lastGyro = lastWake;
    TickType_t activeDuration = 0;
    
    // Gyro polling at 20Hz = 50ms period (reduced from 100Hz to avoid blocking)
    const TickType_t GYRO_PERIOD = pdMS_TO_TICKS(50);
    float gyro_yaw = 0.0f;
    float last_gyro_yaw = 0.0f;
    float relative_heading = 0.0f;
    bool has_gyro_yaw_sample = false;

    // ---------- Load Solution Points ----------
    std::vector<SolutionPoint> solution_points;
    std::vector<SolutionSpan> solution_spans;
    SolutionDeserializeDebugInfo point_decode_debug{};
    SolutionDeserializeDebugInfo span_decode_debug{};
    const bool points_loaded = deserializeEmbeddedSolutionPoints(solution_points, &point_decode_debug);
    const bool spans_loaded = deserializeEmbeddedSolutionSpans(solution_spans, &span_decode_debug);
    size_t next_solution_point_idx = 0;

    if (!points_loaded)
    {
        printSolutionDeserializeFailure("solution points", point_decode_debug);
        Serial.println("No valid solution points loaded; distance recalibration disabled");
    }
    else if (solution_points.empty())
    {
        Serial.println("Loaded solution points payload, but point count is 0; distance recalibration disabled");
    }
    else
    {
        relative_heading = solution_points.front().angle;
        next_solution_point_idx = (solution_points.size() > 1) ? 1 : solution_points.size();
        Serial.printf(
            "Loaded %u solution points; initial heading set to %.2f deg\n",
            static_cast<unsigned>(solution_points.size()),
            relative_heading);
    }

    if (!spans_loaded)
    {
        printSolutionDeserializeFailure("solution spans", span_decode_debug);
        Serial.println("No valid solution spans loaded; dynamic velocity scaling disabled");
    }
    else if (solution_spans.empty())
    {
        Serial.println("Loaded solution spans payload, but span count is 0; dynamic velocity scaling disabled");
    }
    else
    {
        Serial.printf(
            "Loaded %u solution spans for dynamic velocity scaling\n",
            static_cast<unsigned>(solution_spans.size()));
        printDecodedSolutionSpans(solution_spans);
    }

    // ---------- Initialize Gyro ----------

    Gyro gyro;
    const bool gyro_ready = gyro.init();
    if (!gyro_ready)
    {
        Serial.println("Failed to initialize gyro!");
    }
    else
    {
        Serial.println("Gyro initialized successfully");
    }


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

    // Create sensor array with module configuration from config.h
    SensorArray sensor_array(NUM_MODULES, SENSORS_PER_MODULE);

    float distance = 0.0f;

    OdometryState odom;

    if (!solution_points.empty())
    {
        odom.distance = solution_points.front().distance;
    }

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
                sensor_array.resetTrackingState(true);
                odom = OdometryState{};
                odom.prev_rev_L = motor_left.telemetry().revolutions;
                odom.prev_rev_R = motor_right.telemetry().revolutions;

                if (gyro_ready)
                {
                    gyro.zeroYaw();
                }

                if (!solution_points.empty())
                {
                    relative_heading = solution_points.front().angle;
                    odom.distance = solution_points.front().distance;
                    next_solution_point_idx = (solution_points.size() > 1) ? 1 : solution_points.size();
                }
                else
                {
                    relative_heading = 0.0f;
                    next_solution_point_idx = 0;
                }

                has_gyro_yaw_sample = false;
                Serial.println("Entered line following mode, resetting odometry, PID, and sensor tracking state");
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
            sensor_array.poll();
        }

        sensor_array.process();
        int8_t error = sensor_array.getError(); // returns INT8_MAX if no line detected (also updates valid_error internally)

        // ---------- POLL GYRO ----------
        
        if (gyro_ready && (ticks - lastGyro >= GYRO_PERIOD))
        {
            float roll, pitch;
            gyro.getEulerAngles(roll, pitch, gyro_yaw);

            if (has_gyro_yaw_sample)
            {
                // Keep heading continuous across 0/360 wrap by unwrapping yaw deltas.
                float delta_yaw = gyro_yaw - last_gyro_yaw;
                if (delta_yaw > 180.0f)
                {
                    delta_yaw -= 360.0f;
                }
                else if (delta_yaw < -180.0f)
                {
                    delta_yaw += 360.0f;
                }
                relative_heading += delta_yaw;
            }
            else
            {
                has_gyro_yaw_sample = true;
            }

            last_gyro_yaw = gyro_yaw;
            lastGyro = ticks;
        }
            
        // ---------- UPDATE CONTROL STATE ----------
        updateOdometry(
            odom,
            motor_left.telemetry().revolutions,
            motor_right.telemetry().revolutions);

        // Recalibrate odometry distance when heading reaches/surpasses each successive solution point angle.
        if (current_mode == 2)
        {
            size_t skipped_points = 0;
            while (next_solution_point_idx < solution_points.size())
            {
                const SolutionPoint &candidate = solution_points[next_solution_point_idx];
                const float jump_distance_threshold =
                    candidate.distance * (1.0f + kSolutionDistanceJumpPercent);

                if (odom.distance > jump_distance_threshold)
                {
                    ++next_solution_point_idx;
                    ++skipped_points;
                }
                else
                {
                    break;
                }
            }

            if (skipped_points > 0)
            {
                Serial.printf(
                    "Skipped %u solution point(s); odom distance %.3f exceeded jump threshold\n",
                    static_cast<unsigned>(skipped_points),
                    odom.distance);
            }

            if (next_solution_point_idx < solution_points.size())
            {
                const SolutionPoint &next_point = solution_points[next_solution_point_idx];
                const float previous_point_angle =
                    (next_solution_point_idx > 0)
                        ? solution_points[next_solution_point_idx - 1].angle
                        : relative_heading;
                const bool reached_point_angle = hasReachedSolutionAngle(
                    previous_point_angle,
                    next_point.angle,
                    relative_heading);

                if (reached_point_angle)
                {
                    odom.distance = next_point.distance;
                    Serial.printf(
                        "Distance recalibrated at point %u: prev=%.2f heading=%.2f target=%.2f distance=%.3f\n",
                        static_cast<unsigned>(next_solution_point_idx),
                        previous_point_angle,
                        relative_heading,
                        next_point.angle,
                        odom.distance);

                    ++next_solution_point_idx;
                }
            }
        }

        // Check if line was just lost
        if (sensor_array.isLineLost() && error == INT8_MAX)
        {
            Serial.println("Line lost!");
        }

        float pid_output = 0.0F;
        if (current_mode == 2)
        {
            activeDuration = ticks - lastIdle;
            int8_t valid_error = sensor_array.getValidError();
            const float span_percent_velocity = getSpanPercentVelocityForDistance(solution_spans, odom.distance);
            pid_output = pid_update(valid_error / static_cast<float>(sensor_array.getTotalSensors() / 2), CONTROL_PERIOD * portTICK_PERIOD_MS / 1000.0f, 1.0f - span_percent_velocity); // Normalize error to [-1, 1] range
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
                float velocity_setpoint_mps = rx.max_velocity;
                if (!solution_spans.empty())
                {
                    const float span_percent_velocity = getSpanPercentVelocityForDistance(solution_spans, odom.distance);
                    velocity_setpoint_mps = span_percent_velocity * (rx.max_velocity - kMinLineFollowVelocityMps) + kMinLineFollowVelocityMps;
                        
                }

                if(sensor_array.isLineLost())
                {
                    velocity_setpoint_mps = kMinLineFollowVelocityMps; // Don't stop completely when line is lost, to allow for recovery
                }
                float set_rev = velocity_setpoint_mps / WHEEL_CIRCUMFERENCE_M;
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
                const bool *ir_data = sensor_array.getProcessedData();
                for (uint8_t i = 0; i < sensor_array.getTotalSensors(); i++)
                {
                    Screen::instance().gfx().drawRect((sensor_array.getTotalSensors() - i) * 3, 0, 2, ir_data[i] ? 8 : 0, SSD1306_WHITE);
                }
                if (error != INT8_MAX)
                {
                    Screen::instance().gfx().drawCircle((64 - (128 / sensor_array.getTotalSensors() * error)), 12, 3, SSD1306_WHITE);
                }

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

            tx.relative_heading = relative_heading;

            // Copy raw IR
            const uint16_t *ir_raw_data = sensor_array.getRawData();
            memcpy(tx.ir_raw, ir_raw_data, sensor_array.getTotalSensors() * sizeof(uint16_t));

            // Pack 40 bools into 64-bit bitfield
            uint64_t packed = 0;
            const bool *ir_proc_data = sensor_array.getProcessedData();

            for (uint8_t i = 0; i < 40; i++)
            {
                if (ir_proc_data[i])
                {
                    packed |= (1ULL << i);
                }
            }

            tx.packed_ir_processed = packed;

            tx.line_error = sensor_array.getValidError();
            tx.pid_output = pid_output;

            tx.distance = odom.distance; // Approximate distance traveled (relative to start)

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
