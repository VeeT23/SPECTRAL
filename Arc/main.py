import sys
import cv2
import math
import numpy as np
import matplotlib.cm as cm  # for colormap
from skimage.morphology import skeletonize
import pyqtgraph as pg
from PyQt6 import QtWidgets, QtCore
from PyQt6.QtGui import QAction
from pathfinder import generate_path_from_skeleton, compute_relative_angles

class Arc:
    def __init__(self, image_path):
        self.app = QtWidgets.QApplication(sys.argv)

        # Use a QMainWindow for menu support
        self.win = QtWidgets.QMainWindow()
        self.win.setWindowTitle("Arc")
        self.win.resize(900, 700)

        # Create menu bar
        self.menu_bar = self.win.menuBar()
        self.file_menu = self.menu_bar.addMenu("File")
        self.view_menu = self.menu_bar.addMenu("View")

        view_path_action = QAction("View Line Path", self.win)
        view_path_action.setCheckable(True)
        view_path_action.setChecked(False)
        view_path_action.triggered.connect(self.toggle_path_visibility)
        self.view_menu.addAction(view_path_action)


        # Central widget: GraphicsLayoutWidget
        self.central_widget = pg.GraphicsLayoutWidget()
        self.win.setCentralWidget(self.central_widget)

        # All PyQtGraph setup now uses central_widget
        self.view = self.central_widget.addViewBox()
        self.view.setAspectLocked(True)
        self.img_item = pg.ImageItem()
        self.view.addItem(self.img_item)

        # Slider
        self.slider = QtWidgets.QSlider()
        self.slider.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(0)
        proxy = QtWidgets.QGraphicsProxyWidget()
        proxy.setWidget(self.slider)
        self.central_widget.addItem(proxy, row=1, col=0)
        self.slider.valueChanged.connect(self.update_stage_from_slider)

        # Path item
        self.path_item = pg.PlotDataItem(
            pen=pg.mkPen('r', width=2),
            symbol='o',
            symbolSize=6,
            symbolBrush='r'
        )
        self.view.addItem(self.path_item)

        # Image processing
        self.stages = []
        self.stage_index = 0
        self.process_image(image_path)
        self.update_display()

        self.win.show()

    def keep_largest_component(self, skeleton):
        # Convert to binary 0/1
        binary = skeleton > 0

        # Label connected components
        num_labels, labels = cv2.connectedComponents(binary.astype(np.uint8))

        if num_labels <= 1:
            return skeleton  # nothing to filter

        # Count pixels in each label
        counts = np.bincount(labels.flatten())

        # Ignore label 0 (background)
        counts[0] = 0

        # Find largest component
        largest_label = np.argmax(counts)

        # Keep only largest
        filtered = (labels == largest_label).astype(np.uint8) * 255

        return filtered

    # ---------------- Image Pipeline ----------------
    def process_image(self, path):
        original = cv2.imread(path)
        if original is None:
            raise FileNotFoundError(path)

        original_rgb = cv2.cvtColor(original, cv2.COLOR_BGR2RGB)
        self.stages.append(original_rgb)

        # Grayscale
        gray = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)
        self.stages.append(gray)

        # Threshold
        _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        self.stages.append(thresh)

        # Invert for skeleton (black track becomes foreground)
        binary = thresh == 0

        skeleton = skeletonize(binary)
        skeleton = (skeleton * 255).astype(np.uint8)
        self.stages.append(skeleton)

        # Keep only longest connected skeleton
        filtered = self.keep_largest_component(skeleton)
        self.stages.append(filtered)

        self.slider.setMaximum(len(self.stages) - 1)


        self.path = generate_path_from_skeleton(filtered, epsilon=1.2)
        self.draw_path_segments()
        self.toggle_path_visibility(False)
    # ---------------- UI ----------------
    def update_stage_from_slider(self, value):
        self.stage_index = value
        self.update_display()

    def update_display(self):
        img = self.stages[self.stage_index]
        img = np.flipud(img)

        if img.ndim == 2:
            self.img_item.setImage(img.T)
        else:
            self.img_item.setImage(img.transpose(1, 0, 2))
    
    def draw_path_segments(self):
        """Draw the path segments once and store them in self.segment_items."""
        if not hasattr(self, "path") or self.path is None:
            return

        # Flip Y coordinates to match display
        path_y = self.stages[0].shape[0] - self.path[:, 1]  # base on first image for coords
        path_x = self.path[:, 0]

        angles = compute_relative_angles(self.path)
        if len(angles) == 0:
            angles = np.array([0.0])
        angles = np.append(angles, angles[-1])

        max_angle = np.pi / 4
        norm_angles = np.clip(np.abs(angles) / max_angle, 0, 1)

        cmap = cm.get_cmap("RdYlGn_r")  # green=straight, red=turn

        self.segment_items = []

        for i, angle_norm in enumerate(norm_angles):
            color = cmap(angle_norm)
            pen_color = pg.mkColor(
                int(color[0]*255),
                int(color[1]*255),
                int(color[2]*255)
            )
            seg = pg.PlotDataItem(
                [path_x[i], path_x[i+1]],
                [path_y[i], path_y[i+1]],
                pen=pg.mkPen(pen_color, width=4),
                symbol='o',
                symbolSize=3,
                symbolBrush=pen_color
            )
            self.view.addItem(seg)
            self.segment_items.append(seg)
    
    def toggle_path_visibility(self, checked):
        print(f"Toggle path visibility: {checked}")
        if hasattr(self, "segment_items"):
            for item in self.segment_items:
                item.setVisible(checked)


    def run(self):
        sys.exit(self.app.exec())


if __name__ == "__main__":
    arc = Arc("../pathfinder_2026.png")
    arc.run()