import serial
import serial.tools.list_ports
import threading
import time
from queue import Queue

HEADER = 0xAA55
HEADER_BYTES = HEADER.to_bytes(2, byteorder="little")


class ESP32Serial:
    def __init__(self, baudrate=576000, timeout=1, packet_size=None):
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None
        self.connected = False
        self.running = True
        self.packet_size = packet_size

        self._lock = threading.Lock()
        self._packet_queue = Queue(maxsize=10)  # Buffer up to 10 packets
        
        self._connection_thread = threading.Thread(
            target=self._connection_loop,
            daemon=True
        )
        self._connection_thread.start()
        
        self._read_thread = threading.Thread(
            target=self._read_loop,
            daemon=True
        )
        self._read_thread.start()

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
        last_status = None
        while self.running:
            if not self.connected:
                port = self._scan_ports()

                if port:
                    try:
                        print(f"[SERIAL] Attempting connection to {port}...")
                        ser = serial.Serial(
                            port,
                            self.baudrate,
                            timeout=self.timeout
                        )

                        with self._lock:
                            self.ser = ser
                            self.connected = True

                        print(f"[SERIAL] ✓ Connected to ESP32 on {port} @ {self.baudrate} baud")

                    except serial.SerialException as e:
                        print(f"[SERIAL] ✗ Connection failed: {e}")
                else:
                    print(f"[SERIAL] No compatible port found, retrying...")

                time.sleep(1)
            else:
                # Connected - do nothing, just keep checking
                time.sleep(0.2)

    # ---------------- READ LOOP ----------------
    def _read_loop(self):
        """Background thread that continuously reads packets from serial."""
        read_attempt_count = 0
        successful_reads = 0
        while self.running:
            if not self.connected:
                time.sleep(0.1)
                continue
            
            read_attempt_count += 1
            packet_data = self._read_packet_blocking(self.packet_size)
            if packet_data is not None:
                successful_reads += 1
                try:
                    self._packet_queue.put_nowait(packet_data)
                except:
                    # Queue full, drop oldest packet
                    print(f"[SERIAL] Queue full, dropping packet")
                    try:
                        self._packet_queue.get_nowait()
                        self._packet_queue.put_nowait(packet_data)
                    except:
                        pass
            
            # Print stats every 50 read attempts
            if read_attempt_count % 50 == 0 and read_attempt_count > 0:
                print(f"[SERIAL] Read stats: {successful_reads}/{read_attempt_count} successful")
    
    def get_packet(self):
        """Non-blocking: Get next packet from queue, or None if empty."""
        try:
            packet = self._packet_queue.get_nowait()
            return packet
        except:
            return None
    
    def _read_packet_blocking(self, expected_payload_size):
        """Internal blocking read. Called from background thread only."""
        if not self.connected or expected_payload_size is None:
            return None

        try:
            with self._lock:

                # --- 1. Find header ---
                header_search_count = 0
                while True:
                    first = self.ser.read(1)
                    header_search_count += 1
                    if not first:
                        if header_search_count > 1:
                            print(f"[SERIAL] No data received (searched {header_search_count} bytes)")
                        return None

                    if first == HEADER_BYTES[0:1]:
                        second = self.ser.read(1)
                        if second == HEADER_BYTES[1:2]:
                            
                            break  # header found

                # --- 2. Read size ---
                size_bytes = self.ser.read(2)
                if len(size_bytes) != 2:
                    print(f"[SERIAL] Failed to read size: got {len(size_bytes)} bytes instead of 2")
                    return None

                size = int.from_bytes(size_bytes, "little")
               

                if size != expected_payload_size:
                    # Corrupted or wrong alignment → resync
                    print(f"[SERIAL] Size mismatch! Got {size}, expected {expected_payload_size} - resyncing")
                    return None

                # --- 3. Read payload ---
                payload = self.ser.read(size)
                if len(payload) != size:
                    print(f"[SERIAL] Payload read incomplete: got {len(payload)} bytes, expected {size}")
                    return None

                return payload

        except (serial.SerialException, OSError) as e:
            print(f"[SERIAL] Connection lost: {e}")
            with self._lock:
                try:
                    self.ser.close()
                except:
                    pass
                self.ser = None
                self.connected = False

            return None

    def read_packet(self, expected_payload_size):
        """Deprecated: Kept for backward compatibility. Use get_packet() instead."""
        if expected_payload_size is not None:
            self.packet_size = expected_payload_size
        return self.get_packet()

    # ---------------- CLEAN SHUTDOWN ----------------
    def close(self):
        self.running = False
        if self._connection_thread:
            self._connection_thread.join(timeout=2)
        if self._read_thread:
            self._read_thread.join(timeout=2)
        if self.ser:
            self.ser.close()