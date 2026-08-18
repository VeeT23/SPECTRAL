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

| MCU Pin | Function    | Peripheral | Notes        |
| ------- | ----------- | ---------- | ------------ |
| PA0     | User Button | GPIO       | Active low   |
| PA1     | LED         | GPIO       | Active high  |
| PB6     | I2C SCL     | I2C1       | Sensor bus   |
| PB7     | I2C SDA     | I2C1       | Sensor bus   |
| PA9     | UART TX     | USART1     | Debug output |
| PA10    | UART RX     | USART1     | Debug input  |

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
│   ├── pcb/
│   ├── schematic/
│   └── bom/
├── .gitignore
└── README.md
```

## Building

### Prerequisites





## Configuration

Document compile-time and runtime configuration options.

Example:

```c
#define SENSOR_SAMPLE_PERIOD_MS 1000
#define UART_BAUDRATE           115200
#define LOW_BATTERY_THRESHOLD_MV 3300
```

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
