from PyQt6 import QtWidgets, QtCore
import sys
from spectral.ui.main_window import MainWindow
from spectral.data.config import Config
from spectral.io.esp_serial import ESP32Serial
from spectral.io.packet import read_packet, SIZE

class Main(QtCore.QObject):
    def __init__(self):
        super().__init__()

        print("[MAIN] Initializing application...")
        self.config = Config()

        self.window = MainWindow(self.config)

        self.serial = ESP32Serial(packet_size=SIZE)
        print(f"[MAIN] Serial reader started, waiting for connection...")

        # Packet reading timer (200 TPS)
        timer = QtCore.QTimer(self)
        timer.timeout.connect(self.update)
        timer.start(5) # Update every 5 ms

        # UI update timer (60 TPS)
        self.ui_timer = QtCore.QTimer(self)
        self.ui_timer.timeout.connect(self.window.update)
        self.ui_timer.start(int(1000 / 60))  # ~16.67 ms for 60 TPS

    def update(self):
        # Consume all available packets from the queue (prevents buildup/overlap)
        latest_packet = None

        while True:
            packet = read_packet(self.serial)
            if packet is None:
                break
            latest_packet = packet
        
        if latest_packet is None:
            return
        
        self.window.on_packet(latest_packet)
           

def main():
    app = QtWidgets.QApplication(sys.argv)
    main_application = Main()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()