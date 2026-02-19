import struct
import serial
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets

# ---------------- SERIAL ----------------
ser = serial.Serial("COM4", 115200)

FORMAT = "<ff40H40B"
SIZE = struct.calcsize(FORMAT)

# ---------------- HEATMAP SETTINGS ----------------
NUM_SENSORS = 40
TIME_HISTORY = 300

heatmap_data = np.zeros((TIME_HISTORY, NUM_SENSORS), dtype=np.float32)

# ---------------- QT APP ----------------
app = QtWidgets.QApplication([])

win = pg.GraphicsLayoutWidget(show=True, title="IR Sensor Heatmap")
win.resize(800, 600)

plot = win.addPlot()
img = pg.ImageItem()
plot.addItem(img)

plot.setLabel('bottom', 'Time')
plot.setLabel('left', 'Sensor Index')

colormap = pg.colormap.get("inferno")
img.setLookupTable(colormap.getLookupTable())
img.setLevels([0, 4096])

def update():
    global heatmap_data

    data = ser.read(SIZE)
    if len(data) != SIZE:
        return

    unpacked = struct.unpack(FORMAT, data)
    ir_raw = np.array(unpacked[2:42], dtype=np.float32)

    heatmap_data = np.roll(heatmap_data, -1, axis=0)
    heatmap_data[-1, :] = ir_raw

    img.setImage(heatmap_data, autoLevels=False)

timer = QtCore.QTimer()
timer.timeout.connect(update)
timer.start(5)

app.exec()
