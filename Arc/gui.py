from PyQt6 import QtWidgets, QtCore
from PyQt6.QtGui import QAction, QActionGroup
import pyqtgraph as pg

def make_menu(self):
    # Create menu bar
    self.menu_bar = self.win.menuBar()
    self.file_menu = self.menu_bar.addMenu("File")
    self.view_menu = self.menu_bar.addMenu("View")

    # ---------------- View Line Path Toggle ----------------
    self.view_path_menu = self.view_menu.addMenu("View Path")

    self.path_group = QActionGroup(self.win)
    self.path_group.setExclusive(True)

    path_names = ["None", "Curvature", "Solid", "Arc Length", "Length From Start"]


    for i, name in enumerate(path_names):
        action = QAction(name, self.win)
        action.setCheckable(True)
        if i == 0:
            action.setChecked(True)

        # When triggered, change segment mode
        action.triggered.connect(lambda checked, mode=name: self.set_segment_mode(mode))

        self.path_group.addAction(action)
        self.view_path_menu.addAction(action)

    self.view_path_menu.addSeparator()
    self.boundary_toggle_action = QAction("Show Boundaries", self.win)
    self.boundary_toggle_action.setCheckable(True)
    self.boundary_toggle_action.setChecked(False)
    self.boundary_toggle_action.toggled.connect(self.toggle_boundaries_visibility)
    self.view_path_menu.addAction(self.boundary_toggle_action)


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

    control_panel = QtWidgets.QHBoxLayout()

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

    spin_box_layout = QtWidgets.QHBoxLayout()

    self.path_epsilon_spin = QtWidgets.QDoubleSpinBox()
    self.path_epsilon_spin.setRange(0.0, 100.0)
    self.path_epsilon_spin.setDecimals(3)
    self.path_epsilon_spin.setSingleStep(0.1)
    self.path_epsilon_spin.setValue(1.0)

    self.path_epsilon_spin.editingFinished.connect(self.commit_path_epsilon)

    spin_box_layout.addWidget(QtWidgets.QLabel("Path Epsilon:"))
    spin_box_layout.addWidget(self.path_epsilon_spin)

    stage_interface.addLayout(spin_box_layout)
    
    control_panel.addLayout(stage_interface)

    # ============== Simulation Interface ==============

    simulation_interface = QtWidgets.QVBoxLayout()

    # Horizontal row for tick and toggle buttons
    sim_btn_row = QtWidgets.QHBoxLayout()

    tick_sim_btn = QtWidgets.QPushButton()
    tick_sim_btn.setText("Tick Sim")
    tick_sim_btn.pressed.connect(self.tick_simulation_loop)

    self.toggle_sim_btn = QtWidgets.QPushButton()
    self.toggle_sim_btn.setText("Start Loop")
    self.toggle_sim_btn.setCheckable(True)
    self.toggle_sim_btn.pressed.connect(self.toggle_simulation)

    sim_btn_row.addWidget(tick_sim_btn)
    sim_btn_row.addWidget(self.toggle_sim_btn)

    simulation_interface.addLayout(sim_btn_row)

    control_panel.addLayout(simulation_interface)

    layout.addLayout(control_panel)

    # Set as central widget
    self.win.setCentralWidget(container)