#pragma once

#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>

template <typename TxPacket, typename RxPacket>
class ESPNowRadio
{
public:
    // ===============================
    // Meyer's Singleton Access
    // ===============================
    static ESPNowRadio &instance()
    {
        static ESPNowRadio instance;
        return instance;
    }

    // ===============================
    // Initialization
    // ===============================
    bool begin(const uint8_t *peer_mac,
               uint32_t timeout_ms = 1000,
               bool debug_enable = false)
    {
        debug = debug_enable;
        timeout = timeout_ms;

        memcpy(peerMac, peer_mac, 6);

        WiFi.mode(WIFI_STA);
        WiFi.disconnect();

        if (esp_now_init() != ESP_OK)
        {
            if (debug)
                Serial.println("[ESPNOW] Init failed");
            return false;
        }

        esp_now_register_recv_cb(onReceiveStatic);
        esp_now_register_send_cb(onSendStatic);

        esp_now_peer_info_t peerInfo{};
        memcpy(peerInfo.peer_addr, peerMac, 6);
        peerInfo.channel = 0;
        peerInfo.encrypt = false;

        if (!esp_now_is_peer_exist(peerMac))
        {
            if (esp_now_add_peer(&peerInfo) != ESP_OK)
            {
                if (debug)
                    Serial.println("[ESPNOW] Failed to add peer");
                return false;
            }
        }

        if (debug)
        {
            Serial.println("[ESPNOW] Initialized");
            Serial.print("[ESPNOW] Peer MAC: ");
            printMac(peerMac);
        }

        return true;
    }

    // ===============================
    // Public API
    // ===============================

    // Returns true if timed out
    bool update()
    {
        uint32_t now = millis();
        bool timed_out = (now - last_received) > timeout;

        if (debug)
        {
            Serial.print("[ESPNOW] Update - last_received=");
            Serial.print(last_received);
            Serial.print(" timeout=");
            Serial.print(timeout);
            Serial.print(" timed_out=");
            Serial.println(timed_out);
        }

        return timed_out;
    }

    // Copies last packet if new one exists
    bool recieve(RxPacket &pkt)
    {
        if (!new_packet)
            return false;

        noInterrupts();
        pkt = last_packet;
        new_packet = false;
        interrupts();

        if (debug)
        {
            Serial.println("[ESPNOW] Packet retrieved by user");
        }

        return true;
    }

    bool send(TxPacket &pkt)
    {
        esp_err_t result = esp_now_send(peerMac,
                                        reinterpret_cast<uint8_t *>(&pkt),
                                        sizeof(TxPacket));

        if (debug)
        {
            Serial.print("[ESPNOW] Sending packet, size=");
            Serial.print(sizeof(TxPacket));
            Serial.print(" result=");
            Serial.println(result == ESP_OK ? "OK" : "FAIL");
        }

        return result == ESP_OK;
    }

    void reset_timeout()
    {
        last_received = millis();
    }

private:
    // ===============================
    // Internal State
    // ===============================
    RxPacket last_packet{};
    volatile bool new_packet = false;
    uint32_t last_received = 0;
    uint32_t timeout = 1000;
    uint8_t peerMac[6]{};
    bool debug = false;

    // ===============================
    // Constructor (private)
    // ===============================
    ESPNowRadio() {}

    // ===============================
    // Static Callbacks
    // ===============================
    static void onReceiveStatic(const uint8_t *mac_addr,
                                const uint8_t *data,
                                int len)
    {
        auto &inst = instance();

        if (inst.debug)
        {
            Serial.print("[ESPNOW] RX from ");
            inst.printMac(mac_addr);
            Serial.print("[ESPNOW] RX len=");
            Serial.println(len);
        }

        if (len != sizeof(RxPacket))
        {
            if (inst.debug)
            {
                Serial.println("[ESPNOW] RX size mismatch");
            }
            return;
        }

        noInterrupts();
        memcpy(&inst.last_packet, data, sizeof(RxPacket));
        inst.last_received = millis();
        inst.new_packet = true;
        interrupts();

        if (inst.debug)
        {
            Serial.println("[ESPNOW] Packet stored");
        }
    }

    static void onSendStatic(const uint8_t *mac_addr,
                             esp_now_send_status_t status)
    {
        auto &inst = instance();

        if (inst.debug)
        {
            Serial.print("[ESPNOW] TX to ");
            inst.printMac(mac_addr);
            Serial.print(" Status: ");
            Serial.println(status == ESP_NOW_SEND_SUCCESS ? "Success" : "Fail");
        }
    }

    // ===============================
    // Utility
    // ===============================
    void printMac(const uint8_t *mac)
    {
        for (int i = 0; i < 6; i++)
        {
            Serial.printf("%02X", mac[i]);
            if (i < 5)
                Serial.print(":");
        }
        Serial.println();
    }
};
