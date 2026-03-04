from PyQt6 import QtWidgets


class MainWindow():
    def __init__(self):
        
        self.win = QtWidgets.QMainWindow()
        self.win.setWindowTitle("Spectral Data Analysis")
        self.win.resize(900, 700)

        self.win.show()
    