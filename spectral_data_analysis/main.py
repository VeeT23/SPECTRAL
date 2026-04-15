from PyQt6 import QtWidgets, QtCore
import sys
from spectral.ui.main_window import MainWindow
from spectral.data.config import Config
from spectral.io.esp_serial import ESP32Serial
from spectral.io.packet import read_packet, SIZE

class Main(QtCore.QObject):
    def __init__(self):
        super().__init__()

        self.config = Config()

        self.window = MainWindow(self.config)

        self.serial = ESP32Serial(packet_size=SIZE)

        timer = QtCore.QTimer(self)
        timer.timeout.connect(self.update)
        timer.start(5) # Update every 5 ms

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