# SPECTRAL

Short description of the embedded system and what it does.

## Overview

SPECTRAL is a performance line following robot 

## Hardware

### Main Components

| Component          | Part Number       | Description                                                                       |
| ------------------ | ----------------- | --------------------------------------------------------------------------------- |
| MCU                | ESP32-WROOM-32UE  | Main microcontroller                                                              |
| Orientation Sensor | BNO055            | 9-DoF absolute orientation sensor with accelerometer, gyroscope, and magnetometer |
| Motor Controller   | ODrive Micro      | 100 W BLDC motor controller                                                       |
| Motor              | Flash Hobby D4215 | 4215 650 KV BLDC motor, 3S–6S                                                     |
| CAN Transceiver    | ATA6561           | CAN transceiver for motor controller communication                                |

### Pinout

## Pin Definitions

| GPIO | Function | Interface      | Notes                              |
| ---: | -------- | -------------- | ---------------------------------- |
|   16 | A0       | Sensor Address | Sensor address select              |
|   17 | A1       | Sensor Address | Sensor address select              |
|   18 | A2       | Sensor Address | Sensor address select              |
|   32 | S0       | Sensor Output  | Sensor output                      |
|   33 | S1       | Sensor Output  | Sensor output                      |
|   34 | S2       | Sensor Output  | Sensor output                      |
|   35 | S3       | Sensor Output  | Sensor output                      |
|   39 | S4       | Sensor Output  | Sensor output                      |
|   19 | CAN_STBY | CAN            | CAN transceiver standby control    |
|    4 | CAN_RX   | CAN            | CAN receive                        |
|    5 | CAN_TX   | CAN            | CAN transmit                       |
|   22 | SDA      | I2C            | I2C data                           |
|   21 | SCL      | I2C            | I2C clock                          |
|   25 | BUZZER   | GPIO           | Buzzer control                     |
|   26 | NEOPIXEL | GPIO           | Exposed on board; currently unused |
|   27 | FAN_PWM  | PWM            | Exposed on board; currently unused |


## Software

### Toolchain

- **Platform:** Espressif32
- **MCU:** ESP32-WROOM-32UE
- **Framework:** Arduino
- **Build System:** PlatformIO
- **IDE:** Visual Studio Code + PlatformIO

## Repository Structure

```text
SPECTRAL/
├── firmware/
│   ├── common/
│   ├── control_station_firmware/
│   └── spectral_firmware/
├── hardware/
│   ├── main_board/
│   ├── power_module/
│   └── sensor_module/
├── .gitignore
└── README.md
```

## Configuration

| Parameter                |               Value | Description                                        |
| ------------------------ | ------------------: | -------------------------------------------------- |
| Control Frequency        |             1000 Hz | Main control loop frequency                        |
| Display Update Period    |               40 ms | Period between display updates                     |
| Wheel Spacing            |              104 mm | Distance between drive wheels                      |
| Wheel Diameter           |               60 mm | Drive wheel diameter                               |
| Wheel Circumference      |            0.1885 m | Calculated wheel circumference                     |
| Line Following Kp        |                 1.0 | Proportional gain                                  |
| Line Following Ki        |                0.01 | Integral gain                                      |
| Line Following Kd        |                0.01 | Derivative gain                                    |
| Number of Sensor Modules |                   5 | Number of IR sensor modules                        |
| Sensors per Module       |                   8 | Number of sensors on each module                   |
| Total IR Sensors         |                  40 | Total number of IR sensors                         |
| IR Threshold             |                2000 | Sensor threshold used for line detection           |
| Controller MAC           | `D8:3B:DA:46:57:80` | MAC address of the remote controller               |
| Radio RX Timeout         |             1000 ms | Maximum time without receiving controller data     |
| Telemetry Frequency      |              120 Hz | Telemetry transmission frequency                   |
| Radio Debug              |            Disabled | Enables/disables radio debug output                |
| CAN Bitrate              |          500 kbit/s | CAN bus communication speed                        |
| CAN TX Timeout           |               40 ms | Maximum time to wait for CAN transmission          |
| Serial Baud Rate         |              115200 | Serial communication baud rate                     |
| ODrive Heartbeat Timeout |              200 ms | Maximum time without receiving an ODrive heartbeat |
| Motors Enabled           |                 Yes | Enables motor operation                            |

### ODrive Commands

The following CAN command IDs are used to communicate with the ODrive motor controller:

| Command              | CAN ID | Description                                |
| -------------------- | -----: | ------------------------------------------ |
| Heartbeat            | `0x01` | ODrive heartbeat                           |
| Emergency Stop       | `0x02` | Trigger emergency stop                     |
| Set Axis State       | `0x07` | Change ODrive axis state                   |
| Get Encoder Estimate | `0x09` | Request encoder position/velocity estimate |
| Set Input Velocity   | `0x0D` | Set motor velocity command                 |
| Clear Errors         | `0x18` | Clear ODrive errors                        |

### ODrive Axis States

| State       | Value | Description                           |
| ----------- | ----: | ------------------------------------- |
| Idle        |   `1` | Motor disabled / idle                 |
| Closed Loop |   `8` | Motor enabled for closed-loop control |

## Power

Spectral uses a 450 mAh 3s 75C lipo
Running power is unknown however the circuit supports up to 10A continous.
Idle power is measured to be ~140ma

WARNING: AS IT STANDS CURRENTLY, SPECTRAL LACKS OVER DISCHARGE PROTECTION, MONITOR BATTERY VOLTAGE BETWEEN RUNS TO AVOID DAMAGE TO THE BATTERY

## Communication

* UART - Serial debugging/flashing
* I2C - Display screen
* CAN - Motor controllers
* ESP-NOW - Base station communication

## Known Issues

* Dynamic velocity control has no smoothing between setpoints
* Power module lacks battery monitoring for undervoltage

## Future Work

This project is closed, however I will add documentation/clean up issues on request. 

## License

This project is licensed under the GNU GENERAL PUBLIC LICENSE.

## Author

**Veronica Tobias**

[GitHub](https://github.com/VeeT23)
