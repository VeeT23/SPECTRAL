from PyQt6 import QtWidgets, QtCore
import sys
from spectral.ui.main_window import MainWindow
from spectral.data.config import Config
from spectral.io.esp_serial import ESP32Serial
from spectral.io.packet import read_packet

class Main(QtCore.QObject):
    def __init__(self):
        super().__init__()

        self.packets = {}
        self.prev_tick = None

        self.config = Config()

        self.window = MainWindow(self.config)

        self.serial = ESP32Serial()

        timer = QtCore.QTimer(self)
        timer.timeout.connect(self.update)
        timer.start(5) # Update every 5 ms

    def update(self):

        packet = read_packet(self.serial)
        
        if packet is None:
            return
        
        if self.prev_tick is not None and packet.ticks_since_idle < self.prev_tick: # New run, reset packets
            print("Resetting packets")
            self.packets = {}
        
        self.prev_tick = packet.ticks_since_idle
        self.packets[packet.ticks_since_idle] = packet

        self.window.on_packet(packet)
           

def main():
    app = QtWidgets.QApplication(sys.argv)
    main_application = Main()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()