#pragma once

#include <stdint.h>
#include <cstring>
#include <driver/twai.h>
#include "config.h"

// ---------------- CAN BUS SINGLETON ----------------
class CANBus
{
public:
    // Get singleton instance
    static CANBus& instance()
    {
        static CANBus bus;
        return bus;
    }

    // ---------- Lifecycle ----------

    bool begin(int tx, int rx, uint32_t bitrate = 500000)
    {
        if (started_) return true;

        digitalWrite(PINS::CAN_STBY,LOW); // Active low

        twai_general_config_t g_config = TWAI_GENERAL_CONFIG_DEFAULT(
            static_cast<gpio_num_t>(tx),
            static_cast<gpio_num_t>(rx),
            TWAI_MODE_NORMAL
        );

        twai_timing_config_t t_config;
        switch (bitrate)
        {
            case 250000: t_config = TWAI_TIMING_CONFIG_250KBITS(); break;
            case 500000: t_config = TWAI_TIMING_CONFIG_500KBITS(); break;
            case 1000000: t_config = TWAI_TIMING_CONFIG_1MBITS(); break;
            default:     return false;
        }

        twai_filter_config_t f_config = TWAI_FILTER_CONFIG_ACCEPT_ALL();

        if (twai_driver_install(&g_config, &t_config, &f_config) != ESP_OK)
            return false;

        if (twai_start() != ESP_OK)
            return false;

        started_ = true;
        return true;
    }

    void end()
    {
        if (!started_) return;
        twai_stop();
        twai_driver_uninstall();
        started_ = false;
    }

    bool started() const
    {
        return started_;
    }

    // ---------- TX ----------

    bool canSend(uint32_t id, const uint8_t* data, uint8_t len)
    {
        if (!started_ || len > 8) return false;

        twai_message_t msg{};
        msg.identifier = id;
        msg.extd = 0;          // ODrive uses 11-bit IDs
        msg.rtr  = 0;
        msg.data_length_code = len;

        if (data && len > 0)
            memcpy(msg.data, data, len);

        return twai_transmit(&msg, pdMS_TO_TICKS(CAN_TX_TIMEOUT_MS)) == ESP_OK;
    }

    // ---------- RX ----------

    bool receive(twai_message_t& msg, TickType_t timeout = portMAX_DELAY)
    {
        if (!started_) return false;
        return twai_receive(&msg, timeout) == ESP_OK;
    }

    // ---------- TEST ---------

    /**
     * @return
     * - FALSE: fail
     * - TRUE: success
     */
    bool test_can()
    {
        twai_status_info_t status;
        twai_get_status_info(&status);
        Serial.print("CAN state: ");
        Serial.println(status.state);
        if (status.state != ESP_OK) return 0;
        uint8_t dummy[1] = {0xAA};
        bool ok = CANBus::instance().canSend(0x123, dummy, 1);
        if (ok != ESP_OK) return 0;
        return 1;
    }
private:
    CANBus() = default;
    ~CANBus() = default;

    CANBus(const CANBus&) = delete;
    CANBus& operator=(const CANBus&) = delete;

    bool started_ = false;
};
