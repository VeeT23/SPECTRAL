#pragma once

#include <Adafruit_BNO055.h>
#include <Adafruit_Sensor.h>


/**
 * @class Gyro
 * @brief Wrapper class for the Adafruit BNO055 9-DOF IMU sensor
 * 
 * Provides simplified interface for gyroscope, accelerometer, and magnetometer readings.
 * The BNO055 provides both raw sensor data and calculated orientation (Euler angles, quaternion).
 */
class Gyro {
public:
    /**
     * @brief Initialize the BNO055 sensor
     * @param address I2C address of the BNO055 (default: 0x28)
     * @return true if initialization successful, false otherwise
     */
    bool init(uint8_t address = 0x28) {
        // Give sensor time to power up and stabilize
        delay(500);
        
        Serial.println("Attempting BNO055 initialization...");
        if (!bno055.begin()) {
            Serial.println("BNO055 failed to initialize!");
            initialized = false;
            return false;
        }
        
        Serial.println("BNO055 initialized successfully");
        delay(1000);  // Wait for sensor to stabilize
        bno055.setExtCrystalUse(true);
        initialized = true;
        return true;
    }

    /**
     * @brief Check if sensor is connected and responding
     * @return true if sensor is available, false otherwise
     */
    bool isConnected() {
        if (!initialized) return false;
        uint8_t system_status = 0;
        bno055.getSystemStatus(&system_status, nullptr, nullptr);
        return system_status != 0;
    }

    /**
     * @brief Get gyroscope data (angular velocity in rad/s)
     * @param x Reference to store X-axis angular velocity
     * @param y Reference to store Y-axis angular velocity
     * @param z Reference to store Z-axis angular velocity
     */
    void getGyro(float& x, float& y, float& z) {
        imu::Vector<3> gyro = bno055.getVector(Adafruit_BNO055::VECTOR_GYROSCOPE);
        x = gyro.x();
        y = gyro.y();
        z = gyro.z();
    }

    /**
     * @brief Get accelerometer data (in m/s²)
     * @param x Reference to store X-axis acceleration
     * @param y Reference to store Y-axis acceleration
     * @param z Reference to store Z-axis acceleration
     */
    void getAccel(float& x, float& y, float& z) {
        imu::Vector<3> accel = bno055.getVector(Adafruit_BNO055::VECTOR_ACCELEROMETER);
        x = accel.x();
        y = accel.y();
        z = accel.z();
    }

    /**
     * @brief Get magnetometer data (in uT)
     * @param x Reference to store X-axis magnetic field
     * @param y Reference to store Y-axis magnetic field
     * @param z Reference to store Z-axis magnetic field
     */
    void getMag(float& x, float& y, float& z) {
        imu::Vector<3> mag = bno055.getVector(Adafruit_BNO055::VECTOR_MAGNETOMETER);
        x = mag.x();
        y = mag.y();
        z = mag.z();
    }

    /**
     * @brief Get Euler angles (pitch, roll, yaw in degrees)
     * @param roll Reference to store roll angle
     * @param pitch Reference to store pitch angle
     * @param yaw Reference to store yaw angle
     */
    void getEulerAngles(float& roll, float& pitch, float& yaw) {
        imu::Vector<3> euler = bno055.getVector(Adafruit_BNO055::VECTOR_EULER);
        roll = euler.z();   // X axis rotation
        pitch = euler.y();  // Y axis rotation
        yaw = euler.x();    // Z axis rotation

        // Apply software yaw zero offset when requested.
        if (yaw_zeroed) {
            yaw -= yaw_zero_offset;
            if (yaw < 0.0f) {
                yaw += 360.0f;
            } else if (yaw >= 360.0f) {
                yaw -= 360.0f;
            }
        }
    }

    /**
     * @brief Zero the yaw heading at the current orientation
     *
     * Future yaw values returned by getEulerAngles() will be relative to this point.
     */
    void zeroYaw() {
        if (!initialized) return;

        imu::Vector<3> euler = bno055.getVector(Adafruit_BNO055::VECTOR_EULER);
        yaw_zero_offset = euler.x();
        yaw_zeroed = true;
    }

    /**
     * @brief Get quaternion representation of orientation
     * @param w Reference to store W component
     * @param x Reference to store X component
     * @param y Reference to store Y component
     * @param z Reference to store Z component
     */
    void getQuaternion(float& w, float& x, float& y, float& z) {
        imu::Quaternion quat = bno055.getQuat();
        w = quat.w();
        x = quat.x();
        y = quat.y();
        z = quat.z();
    }

    /**
     * @brief Get linear acceleration (acceleration excluding gravity, in m/s²)
     * @param x Reference to store X-axis linear acceleration
     * @param y Reference to store Y-axis linear acceleration
     * @param z Reference to store Z-axis linear acceleration
     */
    void getLinearAccel(float& x, float& y, float& z) {
        imu::Vector<3> linAccel = bno055.getVector(Adafruit_BNO055::VECTOR_LINEARACCEL);
        x = linAccel.x();
        y = linAccel.y();
        z = linAccel.z();
    }

    /**
     * @brief Get gravity vector (in m/s²)
     * @param x Reference to store X-axis gravity component
     * @param y Reference to store Y-axis gravity component
     * @param z Reference to store Z-axis gravity component
     */
    void getGravity(float& x, float& y, float& z) {
        imu::Vector<3> gravity = bno055.getVector(Adafruit_BNO055::VECTOR_GRAVITY);
        x = gravity.x();
        y = gravity.y();
        z = gravity.z();
    }

    /**
     * @brief Get calibration status
     * @return Calibration status (0-3 for each sensor, 3 = fully calibrated)
     *         Bits: [7:6] = mag, [5:4] = accel, [3:2] = gyro, [1:0] = system
     */
    uint8_t getCalibrationStatus() {
        uint8_t sys, gyro, accel, mag;
        bno055.getCalibration(&sys, &gyro, &accel, &mag);
        return (sys << 6) | (accel << 4) | (gyro << 2) | mag;
    }

    /**
     * @brief Check if sensor is fully calibrated
     * @return true if all sensors are fully calibrated, false otherwise
     */
    bool isFullyCalibrated() {
        uint8_t sys, gyro, accel, mag;
        bno055.getCalibration(&sys, &gyro, &accel, &mag);
        return (sys == 3 && gyro == 3 && accel == 3 && mag == 3);
    }

    /**
     * @brief Get temperature reading (in °C)
     * @return Temperature value
     */
    int8_t getTemp() {
        return bno055.getTemp();
    }

    /**
     * @brief Set the operating mode
     * @param mode Operating mode as uint8_t (see Adafruit_BNO055 documentation)
     * @return true if successful, false otherwise
     */
    bool setMode(uint8_t mode) {
        if (!initialized) return false;
        bno055.setMode((adafruit_bno055_opmode_t)mode);
        return true;
    }

    /**
     * @brief Reset the sensor
     * Performs a software reset of the BNO055
     */
    void reset() {
        if (initialized) {
            bno055.enterNormalMode();
        }
    }

private:
    Adafruit_BNO055 bno055;  ///< BNO055 sensor object
    bool initialized = false; ///< Initialization status flag
    float yaw_zero_offset = 0.0f;
    bool yaw_zeroed = false;
};
