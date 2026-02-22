from PyQt6 import QtWidgets, QtCore
from PyQt6.QtGui import QAction, QActionGroup
import pyqtgraph as pg

def make_menu(self):
    # Create menu bar
    self.menu_bar = self.win.menuBar()
    self.file_menu = self.menu_bar.addMenu("File")
    self.view_menu = self.menu_bar.addMenu("View")

    # ---------------- View Line Path Toggle ----------------
    self.view_path_action = QAction("View Line Path", self.win)
    self.view_path_action.setCheckable(True)
    self.view_path_action.setChecked(False)
    self.view_path_action.triggered.connect(self.toggle_path_visibility)
    self.view_menu.addAction(self.view_path_action)

    # ---------------- View Map Submenu ----------------
    self.view_map_menu = self.view_menu.addMenu("View Map")

    # Create exclusive action group
    self.map_group = QActionGroup(self.win)
    self.map_group.setExclusive(True)

    # Stage names
    stage_names = [
        "None",
        "Original",
        "Grayscale",
        "Threshold",
        "Skeleton",
        "Filtered Skeleton"
    ]

    for i, name in enumerate(stage_names):
        action = QAction(name, self.win)
        action.setCheckable(True)
        if i == 1:
            action.setChecked(True)

        # When triggered, change stage index
        action.triggered.connect(lambda checked, index=i: self.stage_slider.setValue(index))

        self.map_group.addAction(action)
        self.view_map_menu.addAction(action)


def make_central_widgets(self):
    # Container widget
    container = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(container)

    # ---------------- Data interface ----------------
    self.data_interface = QtWidgets.QHBoxLayout()

    # Data graph
    self.data_graph = pg.PlotWidget()
    self.data_interface.addWidget(self.data_graph, stretch=1)

    # Data controls (right side of the data graph)
    data_controls = QtWidgets.QVBoxLayout()

    # Drop-down box for selecting what to plot
    self.data_selector = QtWidgets.QComboBox()
    self.data_selector.addItems([
        "Curvature vs Distance",
        "Velocity vs Distance"
    ])
    #self.data_selector.currentIndexChanged.connect(self.update_data_graph)

    data_controls.addWidget(QtWidgets.QLabel("Select Data:"))
    data_controls.addWidget(self.data_selector)
    data_controls.addStretch(1)  # pushes controls to top

    self.data_interface.addLayout(data_controls)

    layout.addLayout(self.data_interface, stretch=1)

    # ---------------- Graphics view ----------------
    self.graphics = pg.GraphicsLayoutWidget()
    layout.addWidget(self.graphics, stretch=3)
    self.view = self.graphics.addViewBox()
    self.view.setAspectLocked(True)
    self.img_item = pg.ImageItem()
    self.view.addItem(self.img_item)

    # =============== Stage interface ===============

    stage_interface = QtWidgets.QVBoxLayout()

    # ---------------- Current Stage slider ----------------

    slider_box = QtWidgets.QHBoxLayout()
    self.stage_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
    self.stage_slider.setMinimum(0)
    self.stage_slider.setMaximum(0)
    self.stage_slider.valueChanged.connect(self.set_stage)

    self.current_stage_label = QtWidgets.QLabel("Original")

    slider_box.addWidget(QtWidgets.QLabel("Stage:"))
    slider_box.addWidget(self.stage_slider)
    slider_box.addWidget(self.current_stage_label, alignment=QtCore.Qt.AlignmentFlag.AlignRight)
    stage_interface.addLayout(slider_box)

    # ---------------- Path controls ----------------

    slider_box = QtWidgets.QHBoxLayout()
    self.path_epsilon_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
    self.path_epsilon_slider.setMinimum(0)
    self.path_epsilon_slider.setMaximum(100)
    self.path_epsilon_slider.valueChanged.connect(self.set_path_epsilon)

    self.path_epsilon_label = QtWidgets.QLabel("1.0")

    slider_box.addWidget(QtWidgets.QLabel("Path Epsilon:"))
    slider_box.addWidget(self.path_epsilon_slider)
    slider_box.addWidget(self.path_epsilon_label, alignment=QtCore.Qt.AlignmentFlag.AlignRight)
    stage_interface.addLayout(slider_box)




    layout.addLayout(stage_interface)

    # Set as central widget
    self.win.setCentralWidget(container)