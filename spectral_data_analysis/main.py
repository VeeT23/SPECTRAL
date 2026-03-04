from PyQt6 import QtWidgets, QtCore
import sys


from ui.main_window import MainWindow
from data.config import Config

class Main(QtCore.QObject):
    def __init__(self):
        super().__init__()

        self.config = Config()

        self.window = MainWindow()

def main():
    app = QtWidgets.QApplication(sys.argv)
    main_application = Main()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()