import serial
import serial.tools.list_ports
import threading
import time

HEADER = 0xAA55
HEADER_BYTES = HEADER.to_bytes(2, byteorder="little")


class ESP32Serial:
    def __init__(self, baudrate=576000, timeout=1):
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None
        self.connected = False
        self.running = True

        self._lock = threading.Lock()
        self._thread = threading.Thread(
            target=self._connection_loop,
            daemon=True
        )
        self._thread.start()

    # ---------------- PORT SCAN ----------------
    def _scan_ports(self):
        ports = serial.tools.list_ports.comports()

        for port in ports:
            desc = port.description.lower()
            if (
                "cp210" in desc
                or "ch340" in desc
                or "usb serial" in desc
                or "silicon labs" in desc
                or "esp32" in desc
            ):
                return port.device

        return None

    # ---------------- CONNECTION LOOP ----------------
    def _connection_loop(self):
        while self.running:
            if not self.connected:
                port = self._scan_ports()

                if port:
                    try:
                        print(f"Attempting connection to {port}")
                        ser = serial.Serial(
                            port,
                            self.baudrate,
                            timeout=self.timeout
                        )

                        with self._lock:
                            self.ser = ser
                            self.connected = True

                        print("Connected to ESP32")

                    except serial.SerialException:
                        print("Connection failed")

                time.sleep(1)
            else:
                time.sleep(0.2)

    # ---------------- HEADER-SAFE PACKET READ ----------------
    def read_packet(self, expected_payload_size):
        if not self.connected:
            return None

        try:
            with self._lock:

                # --- 1. Find header ---
                while True:
                    first = self.ser.read(1)
                    if not first:
                        return None

                    if first == HEADER_BYTES[0:1]:
                        second = self.ser.read(1)
                        if second == HEADER_BYTES[1:2]:
                            break  # header found

                # --- 2. Read size ---
                size_bytes = self.ser.read(2)
                if len(size_bytes) != 2:
                    return None

                size = int.from_bytes(size_bytes, "little")

                if size != expected_payload_size:
                    # Corrupted or wrong alignment → resync
                    return None

                # --- 3. Read payload ---
                payload = self.ser.read(size)
                if len(payload) != size:
                    return None

                return payload

        except (serial.SerialException, OSError):
            print("Connection lost")
            with self._lock:
                try:
                    self.ser.close()
                except:
                    pass
                self.ser = None
                self.connected = False

            return None

    # ---------------- CLEAN SHUTDOWN ----------------
    def close(self):
        self.running = False
        if self.ser:
            self.ser.close()