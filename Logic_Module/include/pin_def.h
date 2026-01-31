#pragma once
#include <Arduino.h>
namespace PINS {

    //Sensor address pins
    constexpr int A0 = 16;
    constexpr int A1 = 17;
    constexpr int A2 = 18;

    //Sensor output pins
    constexpr int S0 = 32;
    constexpr int S1 = 33;
    constexpr int S2 = 34;
    constexpr int S3 = 35;
    constexpr int S4 = 39;

    //CAN BUS
    constexpr int CAN_STBY = 19;
    constexpr int CAN_RX = 4;
    constexpr int CAN_TX = 5;

    //I2C BUS
    constexpr int SDA = 22;
    constexpr int SCL = 21;

    //Misc
    constexpr int BUZZER = 25;
    constexpr int NEOPIXEL = 26;
    constexpr int FAN_PWM = 27;

    constexpr int OUTPUT_PINS[] =
    {
        A0,
        A1,
        A2,
        CAN_STBY,
        BUZZER,
        NEOPIXEL,
        FAN_PWM
    };

    constexpr int INPUT_PINS[] = 
    {
        S0,
        S1,
        S2,
        S3,
        S4
    };

    inline void configure_pins()
{
    for(int pin : PINS::INPUT_PINS)  { pinMode(pin, INPUT);  }
    for(int pin : PINS::OUTPUT_PINS) { pinMode(pin, OUTPUT); }
}
}

