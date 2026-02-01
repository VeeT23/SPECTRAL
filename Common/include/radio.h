#pragma once

#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>
#include <string.h>
#include "config.h"

// ================= PACKET HEADER =================

struct __attribute__((packed)) PacketHeader {
    uint32_t seq;
    uint8_t  flags;
};

// ================= RADIO =========================

template <typename TxPacket, typename RxPacket>
class Radio {
public:
    // ===== Singleton =====
    static Radio& instance() {
        static Radio inst;
        return inst;
    }

    Radio(const Radio&) = delete;
    Radio& operator=(const Radio&) = delete;

    // ===== Flags =====
    static constexpr uint8_t FLAG_ACK_REQ = 0x01;
    static constexpr uint8_t FLAG_ACK     = 0x02;

    // ===== Callbacks =====
    void (*onPacket)(const RxPacket&) = nullptr;
    void (*onTimeout)()               = nullptr;

    // ===== State =====
    uint32_t txSeq      = 0;
    uint32_t lastRxSeq  = 0;
    uint32_t lastRxTime = 0;
    bool     linkAlive  = false;

    // ===== Init =====
    bool begin(const uint8_t peerMac[6]) {
        memcpy(peerMAC, peerMac, 6);

        WiFi.mode(WIFI_STA);
        WiFi.disconnect(true);

        Serial.print("ESP MAC: ");
        Serial.println(WiFi.macAddress());

        if (esp_now_init() != ESP_OK)
            return false;

        esp_now_register_recv_cb(rxThunk);
        esp_now_register_send_cb(txThunk);

        esp_now_peer_info_t peer{};
        memcpy(peer.peer_addr, peerMAC, 6);
        peer.channel = 0;     // use current channel
        peer.encrypt = false;

        if (esp_now_add_peer(&peer) != ESP_OK)
            return false;

        return true;
    }

    // ===== Send =====
    bool send(TxPacket& pkt, bool requestAck = false) {
        pkt.seq   = ++txSeq;
        pkt.flags = requestAck ? FLAG_ACK_REQ : 0;

        return esp_now_send(
            peerMAC,
            reinterpret_cast<uint8_t*>(&pkt),
            sizeof(TxPacket)
        ) == ESP_OK;
    }

    // ===== Update =====
    void update() {
        const uint32_t now = millis();

        if (linkAlive && (now - lastRxTime > RX_TIMEOUT_MS)) {
            linkAlive = false;
            if (onTimeout) onTimeout();
        }
    }

private:
    Radio() = default;

    uint8_t peerMAC[6]{};

    // ===== RX THUNK =====
    static void rxThunk(const uint8_t* mac,
                        const uint8_t* data,
                        int len) {
        instance().handleRx(mac, data, len);
    }

    // ===== RX HANDLER =====
    void handleRx(const uint8_t*,
                  const uint8_t* data,
                  int len) {

        if (len < (int)sizeof(PacketHeader)) {
            // Garbage packet
            return;
        }

        PacketHeader hdr;
        memcpy(&hdr, data, sizeof(PacketHeader));

        lastRxTime = millis();
        linkAlive  = true;

        // ---- ACK handling ----
        if (hdr.flags & FLAG_ACK_REQ) {
            sendAck(hdr.seq);
        }

        if (hdr.flags & FLAG_ACK) {
            // Optional: track ACKs here
            return;
        }

        // ---- Validate payload size ----
        if (len != sizeof(RxPacket)) {
            Serial.printf(
                "RX size mismatch: got %d expected %d\n",
                len, sizeof(RxPacket)
            );
            return;
        }

        RxPacket pkt;
        memcpy(&pkt, data, sizeof(RxPacket));

        // ---- Sequence tracking ----
        if (lastRxSeq != 0 && pkt.seq != lastRxSeq + 1) {
            // packet drop (optional logging)
        }

        lastRxSeq = pkt.seq;

        if (onPacket)
            onPacket(pkt);
    }

    // ===== TX CALLBACK =====
    static void txThunk(const uint8_t*,
                        esp_now_send_status_t) {
        // Optional: track delivery success
    }

    // ===== ACK =====
    void sendAck(uint32_t seq) {
        PacketHeader ack{};
        ack.seq   = seq;
        ack.flags = FLAG_ACK;

        esp_now_send(
            peerMAC,
            reinterpret_cast<uint8_t*>(&ack),
            sizeof(PacketHeader)
        );
    }
};
