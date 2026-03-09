import pyqtgraph as pg

class IRSensorWidget(pg.PlotItem):
    def __init__(self,parent=None, colormap="inferno"):
        super().__init__(parent)
        self.setTitle("IR Sensor Data")

        self.img = pg.ImageItem()
        self.addItem(self.img)

        self.setLabel("left", "Sensor")
        self.setLabel("bottom", "Ticks")

        cmap = pg.colormap.get(colormap)
        self.img.setLookupTable(cmap.getLookupTable())

    def update(self, data):
        self.img.setImage(data.T, autoLevels=False, levels=(0,4096))

