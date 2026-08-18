#pragma once

#include <Arduino.h>
#include "config.h"
#include "pin_def.h"

/// @class SensorArray
/// @brief Encapsulates IR sensor array management for line following
///
/// This class manages a grid of IR sensors used to detect and track a line on the course.
/// The robot course contains multiple lines and decals that can cause false positives,
/// so this class implements a search strategy that prioritizes detecting the line in a
/// specific region of the sensor array to filter out noise from decals and other obstacles.
///
/// When the robot turns sharply and loses the line, the class maintains a valid error
/// output (amplified in the direction of the last detected error) to help the robot
/// complete the turn and relocate the line.
class SensorArray
{
private:
    // Configuration
    uint8_t num_modules;           ///< Number of sensor modules (e.g., 5)
    uint8_t sensors_per_module;    ///< Sensors per module (e.g., 8)
    uint16_t total_sensors;        ///< Total sensors = num_modules * sensors_per_module

    // Sensor state
    uint8_t sensor_idx;            ///< Current multiplexer index (0 to sensors_per_module-1)
    uint16_t *ir_raw;              ///< Raw ADC readings from all sensors
    bool *ir_processed;            ///< Thresholded sensor data (line detected or not)

    // Line tracking state
    int8_t prev_error;             ///< Previous error value used for line-lost amplification
    int8_t valid_error;            ///< Current valid error (may be amplified if line is lost)
    bool line_lost;                ///< True if no line detected in current frame
    bool waiting_for_corner;       ///< True if waiting for corner sensor confirmation after line loss
    bool expecting_left_corner;    ///< True if waiting for left corner, false for right corner

    /// @brief Sets the analog multiplexer address to select which sensor(s) to read
    /// @param addr The multiplexer address (0-7) corresponding to sensor pairs
    void setMuxAddress(uint8_t addr)
    {
        digitalWrite(PINS::A0, addr & 0x01);
        digitalWrite(PINS::A1, addr & 0x02);
        digitalWrite(PINS::A2, addr & 0x04);
    }

public:
    /// @brief Constructor initializes sensor array with given module configuration
    /// @param num_modules_ Number of sensor modules (typically 5)
    /// @param sensors_per_module_ Sensors per module (typically 8)
    ///
    /// Allocates dynamic arrays for raw and processed sensor data.
    /// Initializes line tracking state to assume no line is detected.
    SensorArray(uint8_t num_modules_, uint8_t sensors_per_module_)
        : num_modules(num_modules_),
          sensors_per_module(sensors_per_module_),
          total_sensors(num_modules_ * sensors_per_module_),
          sensor_idx(0),
          prev_error(0),
          valid_error(0),
          line_lost(false),
          waiting_for_corner(false),
          expecting_left_corner(false)
    {
        ir_raw = new uint16_t[total_sensors];
        ir_processed = new bool[total_sensors];

        memset(ir_raw, 0, total_sensors * sizeof(uint16_t));
        memset(ir_processed, 0, total_sensors * sizeof(bool));
    }

    /// @brief Destructor deallocates sensor data arrays
    ~SensorArray()
    {
        delete[] ir_raw;
        delete[] ir_processed;
    }

    /// @brief Polls one sensor sample from the current multiplexer address
    ///
    /// This method sequentially increments through the multiplexer addresses,
    /// reading from each of the 5 modules. Should be called SENSORS_PER_MODULE times
    /// per control loop to collect all sensor readings.
    ///
    /// The sensors are physically multiplexed, so we cycle through addresses 0-7
    /// to read each sensor sequentially and store in the ir_raw array.
    void poll()
    {
        sensor_idx++;
        sensor_idx = (sensor_idx == sensors_per_module) ? 0 : sensor_idx;
        setMuxAddress(sensor_idx);
        esp_rom_delay_us(20); // Short delay to allow mux to stabilize

        ir_raw[0 * sensors_per_module + sensor_idx] = analogRead(PINS::S4);
        ir_raw[1 * sensors_per_module + sensor_idx] = analogRead(PINS::S3);
        ir_raw[2 * sensors_per_module + sensor_idx] = analogRead(PINS::S2);
        ir_raw[3 * sensors_per_module + sensor_idx] = analogRead(PINS::S1);
        ir_raw[4 * sensors_per_module + sensor_idx] = analogRead(PINS::S0);
    }

    /// @brief Processes raw sensor data: filters and applies threshold
    ///
    /// This method:
    /// 1. Applies a moving average filter to smooth raw ADC readings
    ///    - Single sensor: no filtering
    ///    - Edge sensors: 2-point average
    ///    - Inner sensors: 3-point average
    /// 2. Compares filtered values against IR_THRESHOLD to detect line presence
    /// 3. Stores binary line detection results in ir_processed array
    ///
    /// The filtering helps reduce noise from ambient IR and sensor variations,
    /// making the line detection more robust.
    void process()
    {
        uint16_t filtered[total_sensors];

        if (total_sensors == 0)
            return;

        if (total_sensors == 1)
        {
            filtered[0] = ir_raw[0];
        }
        else
        {
            // First element
            filtered[0] = (ir_raw[0] + ir_raw[1]) / 2;

            // Middle elements
            for (uint8_t i = 1; i < total_sensors - 1; i++)
            {
                filtered[i] = (ir_raw[i - 1] + ir_raw[i] + ir_raw[i + 1]) / 3;
            }

            // Last element
            filtered[total_sensors - 1] =
                (ir_raw[total_sensors - 2] + ir_raw[total_sensors - 1]) / 2;
        }

        // Threshold masking
        for (uint8_t i = 0; i < total_sensors; i++)
        {
            ir_processed[i] = (filtered[i] > IR_THRESHOLD);
        }
    }

    /// @brief Detects line position and calculates steering error
    ///
    /// **Search Strategy for Noise Rejection:**
    /// The course contains multiple lines and decals that create false positives.
    /// To avoid tracking false lines, we use an intelligent search strategy:
    /// - Define a target position based on offset (default center of array)
    /// - Search outward symmetrically from that position
    /// - Lock onto the first line detected
    /// - This prioritizes lines near the center, ignoring edge noise/decals
    ///
    /// **Offset Parameter:**
    /// The offset [-1.0, 1.0] shifts the search center:
    /// - -1.0 searches from left edge
    /// -  0.0 searches from center (default)
    /// - +1.0 searches from right edge
    /// Useful for handling course curves or when the line is expected off-center.
    ///
    /// **Return Value:**
    /// - INT8_MAX: No line detected
    /// - [-N/2, N/2]: Position error (N = total sensors)
    ///   - Negative: line is to the left, turn left
    ///   - Positive: line is to the right, turn right
    ///   - Zero: line is centered
    ///
    /// **Side Effect:**
    /// Automatically updates internal valid_error state via updateValidError().
    /// This ensures valid_error is maintained for PID control even if the line is lost.
    int8_t getError(float offset = 0.0f)
    {
        offset = constrain(offset, -1.0f, 1.0f); // Ensure offset is within [-1, 1]
        if (total_sensors == 0)
        {
            updateValidError(INT8_MAX);
            return INT8_MAX;
        }

        // Map offset to target search position
        // offset=-1 -> position 0 (left), offset=0 -> center, offset=1 -> right
        float target_pos = (offset + 1.0f) * (total_sensors - 1) / 2.0f;
        int8_t center_left = (int8_t)target_pos;
        int8_t center_right = center_left + 1;

        // Search outward symmetrically from target position to find line
        // This strategy helps ignore decals/false lines at the array edges
        int8_t found_index = -1;
        for (int8_t search_offset = 0; search_offset <= total_sensors; search_offset++)
        {
            // Check left side of target
            if (center_left - search_offset >= 0 &&
                ir_processed[center_left - search_offset])
            {
                found_index = center_left - search_offset;
                break;
            }

            // Check right side of target
            if (center_right + search_offset < total_sensors &&
                ir_processed[center_right + search_offset])
            {
                found_index = center_right + search_offset;
                break;
            }
        }

        int8_t raw_error;
        if (found_index == -1)
        {
            // Line not detected anywhere in array
            raw_error = INT8_MAX;
        }
        else
        {
            // Expand left to find the edge of the line
            int8_t left = found_index;
            while (left > 0 && ir_processed[left - 1])
                left--;

            // Expand right to find the other edge of the line
            int8_t right = found_index;
            while (right < total_sensors - 1 && ir_processed[right + 1])
                right++;

            // Calculate line center as midpoint between left and right edges
            int16_t midpoint_times2 = left + right;

            // Target center shifted by offset
            int16_t center_times2 = (int16_t)(target_pos * 2.0f);

            // Signed error: (actual line center) - (target line center)
            // Negative error means line is to the left
            // Positive error means line is to the right
            int16_t error = midpoint_times2 - center_times2;

            raw_error = (int8_t)(error / 2);
        }

        // Update valid error state internally
        // This maintains robust error output even when line is temporarily lost
        updateValidError(raw_error);

        return raw_error;
    }

private:
    /// @brief Maintains valid_error state when line is lost
    ///
    /// **Handle Quick Turns with Corner Sensor Validation:**
    /// When the robot executes a sharp turn at a decal-prone corner, it may lose the line
    /// temporarily. To avoid locking onto decals, we only resume using real sensor data
    /// when the corner sensor (outermost sensor in the turn direction) detects the line.
    ///
    /// **Behavior:**
    /// - Line detected (normal): Update valid_error with current error, track direction
    /// - Line just lost: 
    ///   - Enter corner sensor validation mode
    ///   - Amplify previous error direction to maintain turn momentum
    ///   - Set expecting_left_corner or expecting_right_corner based on turn direction
    /// - Line still lost: Keep amplified error, wait for corner confirmation
    /// - Corner sensor confirms line:
    ///   - If left turn (prev_error < 0), wait for leftmost sensor (index 0)
    ///   - If right turn (prev_error >= 0), wait for rightmost sensor (index total_sensors-1)
    ///   - Once confirmed, resume normal tracking with actual error
    /// - Line detected elsewhere (not at corner): Ignore, continue amplified error
    ///
    /// This ensures smooth turn completion at decal-prone corners by preventing the robot
    /// from locking onto false lines until the actual course line is found at the corner.
    void updateValidError(int8_t raw_error)
    {
        if (raw_error == INT8_MAX && !line_lost) // Line just lost
        {
            line_lost = true;
            waiting_for_corner = true;
            expecting_left_corner = (prev_error < 0);
            // Keep previous error but amplify it to maintain turn momentum
            valid_error = (prev_error < 0) ? -total_sensors : total_sensors;
        }
        else if (raw_error != INT8_MAX && waiting_for_corner)
        {
            // Line detected, but we're waiting for corner sensor confirmation
            // Only resume if the corner sensor is active, based on turn direction
            bool left_corner_active = ir_processed[0];  // Leftmost sensor
            bool right_corner_active = ir_processed[total_sensors - 1];  // Rightmost sensor
            
            bool corner_confirmed = (expecting_left_corner && left_corner_active) ||
                                    (!expecting_left_corner && right_corner_active);
            
            if (corner_confirmed)
            {
                // Corner sensor confirmed the line, resume normal tracking
                waiting_for_corner = false;
                line_lost = false;
                valid_error = raw_error;
                prev_error = raw_error;
            }
            // else: continue amplified error, ignore this false detection
        }
        else if (raw_error != INT8_MAX && !waiting_for_corner)
        {
            // Normal line tracking (not in turn recovery mode)
            line_lost = false;
            valid_error = raw_error;
            prev_error = raw_error;
        }
    }

public:

    /// @brief Reset internal tracking state for a clean mode transition
    /// @param start_line_lost If true, startup no-line frames do not trigger corner-wait logic
    void resetTrackingState(bool start_line_lost = true)
    {
        sensor_idx = 0;
        prev_error = 0;
        valid_error = 0;
        line_lost = start_line_lost;
        waiting_for_corner = false;
        expecting_left_corner = false;

        memset(ir_raw, 0, total_sensors * sizeof(uint16_t));
        memset(ir_processed, 0, total_sensors * sizeof(bool));
    }

    /// @brief Get the current valid error for PID control
    /// @return int8_t The valid error value (possibly amplified if line is lost)
    int8_t getValidError() const
    {
        return valid_error;
    }

    /// @brief Check if the line is currently lost
    /// @return true if no line detected in the current frame, false otherwise
    bool isLineLost() const
    {
        return line_lost;
    }

    /// @brief Check if currently waiting for corner sensor confirmation
    /// @return true if in corner sensor validation mode after line loss, false otherwise
    /// 
    /// This indicates the robot is in sharp turn recovery and maintaining amplified
    /// error until the corner sensor confirms the presence of the real line.
    bool isWaitingForCorner() const
    {
        return waiting_for_corner;
    }

    /// @brief Get raw ADC readings from all sensors
    /// @return Pointer to ir_raw array (const to prevent external modification)
    uint16_t const *getRawData() const
    {
        return ir_raw;
    }

    /// @brief Get processed (thresholded) sensor data
    /// @return Pointer to ir_processed array (const to prevent external modification)
    bool const *getProcessedData() const
    {
        return ir_processed;
    }

    /// @brief Get total number of sensors in the array
    /// @return Total sensors = num_modules * sensors_per_module
    uint16_t getTotalSensors() const
    {
        return total_sensors;
    }

    /// @brief Get sensors per module count
    /// @return Sensors per module
    uint8_t getSensorsPerModule() const
    {
        return sensors_per_module;
    }

    /// @brief Get number of sensor modules
    /// @return Number of modules
    uint8_t getNumModules() const
    {
        return num_modules;
    }
};

/// @brief PID controller for line following
/// @param error Normalized error in range [-1, 1]
/// @param dt Time step in seconds
/// @return Steering output to adjust motor differential
///
/// Implements classic PID control with configurable gains (KP, KI, KD from config.h)
/// to convert line position error into motor control signals.
float pid_update(float error, float dt, float velocity_percent)
{
    static float integral = 0.0f;
    static float prev_error = 0.0f;

    // Accumulate integral error over time
    integral += error * dt;
    
    // Calculate derivative (rate of change) of error
    float derivative = (error - prev_error) / dt;
    prev_error = error;

    // PID output = proportional + integral + derivative terms
    return KP * error + KI * integral + KD * derivative;
}
