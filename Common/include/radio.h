#pragma once

#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include <stdint.h>
#include <string.h>
#include "config.h"

// ================= PACKET HEADER =================

struct __attribute__((packed)) PacketHeader {
    uint32_t seq;
    uint8_t  flags;
};

// ================= PACKETS =================

struct __attribute__((packed)) ControlPacket {
    uint32_t seq;
    uint8_t  flags;
    float left_vel;
    float right_vel;
};

struct __attribute__((packed)) TelemetryPacket {
    uint32_t seq;
    uint8_t  flags;
    float battery_v;
};

// ================= RADIO =========================

template <typename TxPacket, typename RxPacket>
class Radio {
public:
    // ===== FLAGS =====
    static constexpr uint8_t FLAG_ACK_REQ = 0x01;
    static constexpr uint8_t FLAG_ACK     = 0x02;

    // ===== CALLBACKS =====
    void (*onPacket)(const RxPacket&) = nullptr;
    void (*onTimeout)()               = nullptr;

    // ===== STATE =====
    uint32_t txSeq      = 0;
    uint32_t lastRxSeq  = 0;
    uint32_t lastRxTime = 0;
    bool     linkAlive  = false;

    // ===== INIT =====
    bool begin(const uint8_t peerMac[6], uint8_t wifiChannel) {
        memcpy(peerMAC, peerMac, 6);

        WiFi.mode(WIFI_STA);
        WiFi.disconnect(true);

        esp_wifi_set_ps(WIFI_PS_NONE);
        esp_wifi_set_channel(wifiChannel, WIFI_SECOND_CHAN_NONE);

        if (esp_now_init() != ESP_OK)
            return false;

        esp_now_register_recv_cb(rxThunk);
        esp_now_register_send_cb(txThunk);

        esp_now_peer_info_t peer{};
        memcpy(peer.peer_addr, peerMAC, 6);
        peer.channel = wifiChannel;
        peer.encrypt = false;
        peer.ifidx   = WIFI_IF_STA;

        
        Serial.println("ESP MAC: " + WiFi.macAddress());

        if (esp_now_add_peer(&peer) != ESP_OK)
            return false;

        return true;
    }

    // ===== SEND =====
    bool send(const TxPacket& pkt, bool requestAck = false) {
        txBuf = pkt;
        txBuf.seq   = ++txSeq;
        txBuf.flags = requestAck ? FLAG_ACK_REQ : 0;

        return esp_now_send(
            peerMAC,
            reinterpret_cast<uint8_t*>(&txBuf),
            sizeof(TxPacket)
        ) == ESP_OK;
    }

    // ===== UPDATE (CALL FROM LOOP OR TASK) =====
    void update() {
        const uint32_t now = millis();

        // ---- link timeout ----
        if (linkAlive && (now - lastRxTime > RX_TIMEOUT_MS)) {
            linkAlive = false;
            if (onTimeout) onTimeout();
        }

        // ---- deferred ACK ----
        if (ackPending) {
            PacketHeader ack{};
            ack.seq   = pendingAckSeq;
            ack.flags = FLAG_ACK;

            esp_now_send(
                peerMAC,
                reinterpret_cast<uint8_t*>(&ack),
                sizeof(PacketHeader)
            );

            ackPending = false;
        }
    }

    
    // ===== SINGLETON =====
    static Radio& instance() {
        static Radio inst;
        return inst;
    }

private:
    // ===== INTERNAL STORAGE =====
    uint8_t  peerMAC[6]{};
    TxPacket txBuf{};

    volatile bool     ackPending   = false;
    volatile uint32_t pendingAckSeq = 0;

    // ===== RX CALLBACK (WIFI TASK) =====
    static void rxThunk(const uint8_t* mac,
                        const uint8_t* data,
                        int len) {
        instance().handleRx(mac, data, len);
    }

    void handleRx(const uint8_t*,
                  const uint8_t* data,
                  int len) {

        if (len < (int)sizeof(PacketHeader))
            return;

        PacketHeader hdr;
        memcpy(&hdr, data, sizeof(PacketHeader));

        lastRxTime = millis();
        linkAlive  = true;

        // ---- ACK request ----
        if (hdr.flags & FLAG_ACK_REQ) {
            pendingAckSeq = hdr.seq;
            ackPending    = true;
        }

        // ---- ACK only packet ----
        if (hdr.flags & FLAG_ACK)
            return;

        // ---- payload validation ----
        if (len != sizeof(RxPacket))
            return;

        RxPacket pkt;
        memcpy(&pkt, data, sizeof(RxPacket));

        if (lastRxSeq != 0 && pkt.seq != lastRxSeq + 1) {
            // optional drop detection
        }

        lastRxSeq = pkt.seq;

        if (onPacket)
            onPacket(pkt);
    }

    // ===== TX CALLBACK =====
    static void txThunk(const uint8_t*,
                        esp_now_send_status_t) {
        // intentionally empty
    }


    Radio() = default;
    Radio(const Radio&) = delete;
    Radio& operator=(const Radio&) = delete;
};
