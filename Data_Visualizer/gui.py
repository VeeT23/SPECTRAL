# gui.py
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets
import numpy as np

class MapWidget:
    def __init__(self, title="Map", width=400, height=400):
        # Container plot
        self.plot = pg.PlotItem(title=title)
        self.plot.setAspectLocked(True)  # Keep x/y scale equal
        self.plot.showGrid(x=True, y=True, alpha=0.3)
        self.plot.setMenuEnabled(False)
        self.plot.hideButtons()

        # Background image
        self.image_item = pg.ImageItem()
        self.plot.addItem(self.image_item)

        # Dynamic graphics
        self.lines = []  # pg.PlotDataItem
        self.dots = []   # pg.ScatterPlotItem

        # Default size
        self.width = width
        self.height = height
        

    # ---------------- Background ----------------
    def set_background(self, img_array):
        """
        img_array: 2D or 3D numpy array (grayscale or RGB)
        """
        self.image_item.setImage(img_array)
        self.image_item.setRect(QtCore.QRectF(0, 0, self.width, self.height))

    # ---------------- Update ----------------
    def update(self, line_coords=None, dot_coords=None, line_pen=None, dot_brush=None, dot_size=8):
        """
        Draw multiple lines and dots.
        :param line_coords: list of lists of (x, y) coordinates for each line
        :param dot_coords: list of (x, y) coordinates for dots
        :param line_pen: pg.mkPen object or list of pens (one per line)
        :param dot_brush: pg.mkBrush object or color string
        :param dot_size: size of the dots
        """
        # Clear previous lines
        for line in self.lines:
            self.plot.removeItem(line)
        self.lines = []

        # Draw new lines
        if line_coords:
            for i, coords in enumerate(line_coords):
                pen = line_pen
                if isinstance(line_pen, list):
                    pen = line_pen[i] if i < len(line_pen) else pg.mkPen('y', width=2)
                elif pen is None:
                    pen = pg.mkPen('y', width=2)
                line = pg.PlotDataItem(
                    x=[p[0] for p in coords],
                    y=[p[1] for p in coords],
                    pen=pen,
                    symbol=None
                )
                self.plot.addItem(line)
                self.lines.append(line)

        # Clear previous dots
        for dot in self.dots:
            self.plot.removeItem(dot)
        self.dots = []

        # Draw new dots
        if dot_coords:
            brush = dot_brush or pg.mkBrush('r')
            if dot_coords:
                dot = pg.ScatterPlotItem(
                    x=[p[0] for p in dot_coords],
                    y=[p[1] for p in dot_coords],
                    brush=brush,
                    size=dot_size
                )
                self.plot.addItem(dot)
                self.dots.append(dot)

class HeatmapWidget:
    def __init__(self, title, levels=(0, 1), colormap="inferno"):
        self.plot = pg.PlotItem(title=title)

        self.img = pg.ImageItem()
        self.plot.addItem(self.img)

        self.plot.setLabel("left", "Sensor")
        self.plot.setLabel("bottom", "Ticks")
        self.plot.invertY(True)

        cmap = pg.colormap.get(colormap)
        self.img.setLookupTable(cmap.getLookupTable())
        self.levels = levels

    def update(self, data):
        self.img.setImage(data, autoLevels=False, levels=self.levels)

class LineGraphWidget:
    def __init__(self, title, y_label="Value", curve_names=None, pens=None):
        """
        :param title: Plot title
        :param y_label: Label for Y axis
        :param curve_names: List of names for each line
        :param pens: List of pens (pyqtgraph.mkPen) for each line
        """
        self.plot = pg.PlotItem(title=title)
        self.plot.setLabel("left", y_label)
        self.plot.setLabel("bottom", "Ticks")

        self.curves = []

        if curve_names is None:
            curve_names = ["Line1"]
        if pens is None:
            # Automatically generate different colors
            default_colors = [(255,0,0), (0,255,0), (0,0,255), (255,255,0)]
            pens = [pg.mkPen(color=c, width=2) for c in default_colors[:len(curve_names)]]

        for name, pen in zip(curve_names, pens):
            curve = self.plot.plot(pen=pen, name=name)
            self.curves.append(curve)

    def update(self, x, ys):
        """
        :param x: X-axis data (shared for all curves)
        :param ys: List of Y-axis data arrays, one per curve
                If single curve, can also pass a single list
        """
        # Auto-wrap single list for single-curve plot
        if len(self.curves) == 1 and (not isinstance(ys[0], (list, np.ndarray))):
            ys = [ys]

        if len(ys) != len(self.curves):
            raise ValueError(f"Expected {len(self.curves)} y arrays, got {len(ys)}")
        for curve, y in zip(self.curves, ys):
            curve.setData(x=x, y=y)

class TelemetryDashboard:
    def __init__(self, title="SPECTRAL TELEMETRY", max_cols=3):
        self.app = pg.mkQApp()
        self.win = pg.GraphicsLayoutWidget(show=True, title=title)

        self.widgets = []
        self.label = pg.LabelItem(size="16pt")

        self.max_cols = max_cols
        self._occupied = set()   # tracks used grid cells

    # ---------------- Placement ----------------
    def _mark_occupied(self, row, col, rowspan, colspan):
        for r in range(row, row + rowspan):
            for c in range(col, col + colspan):
                self._occupied.add((r, c))

    def _cells_free(self, row, col, rowspan, colspan):
        for r in range(row, row + rowspan):
            for c in range(col, col + colspan):
                if (r, c) in self._occupied:
                    return False
        return True

    def _next_available_position(self, rowspan=1, colspan=1):
        row = 0
        while True:
            for col in range(self.max_cols - colspan + 1):
                if self._cells_free(row, col, rowspan, colspan):
                    return row, col
            row += 1

    def _place(self, item, row=None, col=None, rowspan=1, colspan=1):
        if row is None or col is None:
            row, col = self._next_available_position(rowspan, colspan)
        else:
            if not self._cells_free(row, col, rowspan, colspan):
                raise ValueError(
                    f"Grid cells ({row},{col}) span {rowspan}x{colspan} already occupied."
                )

        self.win.addItem(item, row=row, col=col, rowspan=rowspan, colspan=colspan)
        self._mark_occupied(row, col, rowspan, colspan)

        return row, col

    # ---------------- Map Widget ----------------
    def add_map(self, title="Map", row=None, col=None,
                rowspan=1, colspan=1, width=400, height=400):
        widget = MapWidget(title, width=width, height=height)
        row, col = self._place(widget.plot, row, col, rowspan, colspan)
        widget._grid_pos = (row, col, rowspan, colspan)
        self.widgets.append(widget)
        return widget

    # ---------------- Heatmap ----------------
    def add_heatmap(self, title, levels=(0, 1),
                    row=None, col=None, rowspan=1, colspan=1):
        widget = HeatmapWidget(title, levels)
        row, col = self._place(widget.plot, row, col, rowspan, colspan)
        widget._grid_pos = (row, col, rowspan, colspan)
        self.widgets.append(widget)
        return widget

    # ---------------- Line Graph ----------------
    def add_line(self, title, y_label="Value",
                 curve_names=None, pens=None,
                 row=None, col=None, rowspan=1, colspan=1):
        widget = LineGraphWidget(
            title,
            y_label=y_label,
            curve_names=curve_names,
            pens=pens
        )
        row, col = self._place(widget.plot, row, col, rowspan, colspan)
        widget._grid_pos = (row, col, rowspan, colspan)
        self.widgets.append(widget)
        return widget

    # ---------------- Label Row ----------------
    def add_label_row(self, row=None, col=0, colspan=None):
        if colspan is None:
            colspan = self.max_cols

        if row is None:
            row, col = self._next_available_position(1, colspan)

        self.win.addItem(self.label, row=row, col=col, colspan=colspan)
        self._mark_occupied(row, col, 1, colspan)

    def update_label(self, text):
        self.label.setText(text)

    # ---------------- Start Qt Loop ----------------
    def start(self):
        self.app.exec()