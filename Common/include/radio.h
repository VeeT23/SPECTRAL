#pragma once
#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>

template <typename TxPacket, typename RxPacket>
class Radio {
public:
    // Config
    static constexpr uint32_t RX_TIMEOUT_MS = 100;
    static constexpr uint8_t  FLAG_ACK_REQ = 0x01;
    static constexpr uint8_t  FLAG_ACK     = 0x02;

    // Callbacks
    void (*onPacket)(const RxPacket&) = nullptr;
    void (*onTimeout)() = nullptr;

    // Public state
    uint32_t txSeq = 0;
    uint32_t lastRxSeq = 0;
    uint32_t lastRxTime = 0;
    bool     linkAlive = false;

    // Init
    bool begin(const uint8_t peerMac[6]) {
        memcpy(peerMAC, peerMac, 6);

        WiFi.mode(WIFI_STA);
        Serial.println(WiFi.macAddress());
        WiFi.disconnect();

        if (esp_now_init() != ESP_OK)
            return false;

        esp_now_register_recv_cb(rxThunk);
        esp_now_register_send_cb(txThunk);

        esp_now_peer_info_t peer{};
        memcpy(peer.peer_addr, peerMAC, 6);
        peer.channel = 0;
        peer.encrypt = false;

        if (esp_now_add_peer(&peer) != ESP_OK)
            return false;

        instance = this;
        return true;
    }

    // Send 
    bool send(TxPacket& pkt, bool requestAck = false) {
        pkt.seq = ++txSeq;
        pkt.flags = requestAck ? FLAG_ACK_REQ : 0;

        return esp_now_send(peerMAC,
                            reinterpret_cast<uint8_t*>(&pkt),
                            sizeof(TxPacket)) == ESP_OK;
    }

    // Update
    void update() {
        uint32_t now = millis();

        if (linkAlive && (now - lastRxTime > RX_TIMEOUT_MS)) {
            linkAlive = false;
            if (onTimeout) onTimeout();
        }
    }

private:
    uint8_t peerMAC[6];

    static Radio* instance;

    // ===== RX CALLBACK =====
    static void rxThunk(const uint8_t* mac,
                        const uint8_t* data,
                        int len) {
        if (!instance) return;
        instance->handleRx(mac, data, len);
    }

    void handleRx(const uint8_t* mac,
                  const uint8_t* data,
                  int len) {

        if (len != sizeof(RxPacket))
            return;

        RxPacket pkt;
        memcpy(&pkt, data, sizeof(RxPacket));

        // Sequence tracking
        if (pkt.seq != lastRxSeq + 1 && lastRxSeq != 0) {
            // Packet dropped (optional logging)
        }

        lastRxSeq = pkt.seq;
        lastRxTime = millis();
        linkAlive = true;

        // ACK handling
        if (pkt.flags & FLAG_ACK_REQ) {
            sendAck(pkt.seq);
        }

        if (onPacket)
            onPacket(pkt);
    }

    // TX callback
    static void txThunk(const uint8_t* mac,
                        esp_now_send_status_t status) {
        (void)mac;
        (void)status;
    }

    // ACK
    void sendAck(uint32_t seq) {
        RxPacket ack{};
        ack.seq = seq;
        ack.flags = FLAG_ACK;
        esp_now_send(peerMAC,
                      reinterpret_cast<uint8_t*>(&ack),
                      sizeof(RxPacket));
    }
};

template <typename TxPacket, typename RxPacket>
Radio<TxPacket, RxPacket>* Radio<TxPacket, RxPacket>::instance = nullptr;
