#pragma once
#include <Arduino.h>
#include "pin_def.h"   // PINS::BUZZER

namespace Buzzer {

    // -------- Configuration --------
    constexpr uint8_t  PWM_CHANNEL    = 0;
    constexpr uint8_t  PWM_RESOLUTION = 8;   // 8-bit duty (0–255)
    constexpr uint32_t DEFAULT_FREQ   = 2000;

    // -------- Internal state --------
    inline bool initialized = false;
    inline uint8_t  currentVolume = 0;

    void stop() {
        if (!initialized)
            return;

        ledcWrite(PWM_CHANNEL, 0);
    }
    // -------- Public API --------

    inline void init() {
        if (initialized)
            return;

        ledcSetup(PWM_CHANNEL, DEFAULT_FREQ, PWM_RESOLUTION);
        ledcAttachPin(PINS::BUZZER, PWM_CHANNEL);

        initialized = true;
    }

    /**
     * Start a non-blocking beep
     * @param freq   Frequency in Hz
     * @param ms     Duration in milliseconds
     * @param volume Duty cycle (0–255), ~128 recommended
     */
    inline void beep(uint32_t freq, uint32_t ms, uint8_t volume = 128) {
        if (!initialized)
            init();

        freq   = constrain(freq, 20, 20000);
        volume = constrain(volume, 0, 255);

        ledcSetup(PWM_CHANNEL, freq, PWM_RESOLUTION);
        ledcWrite(PWM_CHANNEL, volume);

        delay(ms);

        stop();
    }

    
}
