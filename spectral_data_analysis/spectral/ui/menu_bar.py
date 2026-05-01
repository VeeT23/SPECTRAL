from spectral.ui.gui.color_line import color_modes
from PyQt6 import QtWidgets
from PyQt6.QtGui import QAction, QActionGroup



class MenuBar(QtWidgets.QMenuBar):
    def __init__(self, parent=None, main_window_instance=None):
        super().__init__(parent)
        self.main_window = main_window_instance
        
        # Create File menu
        self.file_menu = self.addMenu('File')
        
        # Session actions
        self.load_session_action = QAction('Load Session', self)
        self.load_session_action.triggered.connect(lambda: self.main_window.load_file())
        self.file_menu.addAction(self.load_session_action)

        # Solution actions
        self.save_solution_action = QAction('Save Solution', self)
        self.save_solution_action.triggered.connect(lambda: self.main_window.save_solution_file())
        self.file_menu.addAction(self.save_solution_action)

        self.load_solution_action = QAction('Load Solution', self)
        self.load_solution_action.triggered.connect(lambda: self.main_window.load_solution_file())
        self.file_menu.addAction(self.load_solution_action)

        self.export_solution_action = QAction('Export Solution', self)
        self.export_solution_action.triggered.connect(lambda: self.main_window.export_solution_file())
        self.file_menu.addAction(self.export_solution_action)
        
        # Create Edit menu
        self.edit_menu = self.addMenu('Edit')

        self.edit_mode_group = QActionGroup(self)
        self.edit_mode_group.setExclusive(True)

        self.edit_points_action = QAction('Edit Points', self)
        self.edit_points_action.setCheckable(True)
        self.edit_points_action.setChecked(True)
        self.edit_points_action.triggered.connect(
            lambda checked: checked and self.main_window.set_edit_mode('points')
        )
        self.edit_mode_group.addAction(self.edit_points_action)
        self.edit_menu.addAction(self.edit_points_action)

        self.edit_spans_action = QAction('Edit Spans', self)
        self.edit_spans_action.setCheckable(True)
        self.edit_spans_action.triggered.connect(
            lambda checked: checked and self.main_window.set_edit_mode('spans')
        )
        self.edit_mode_group.addAction(self.edit_spans_action)
        self.edit_menu.addAction(self.edit_spans_action)
        
        # Create View menu
        self.view_menu = self.addMenu('View')

        self.track_map_menu = self.view_menu.addMenu('Track Map')
        self.select_stage_menu = self.track_map_menu.addMenu('Select Stage')
        self.path_menu = self.track_map_menu.addMenu('Path')

        self.show_path_action = QAction('Show Path', self)
        self.show_path_action.setCheckable(True)
        self.show_path_action.triggered.connect(lambda checked: self.main_window.set_path_visibility(checked))
        self.path_menu.addAction(self.show_path_action)

        self.color_mode_menu = self.path_menu.addMenu('Color Mode')
        self.color_mode_group = QActionGroup(self)
        self.color_mode_group.setExclusive(True)
        for mode in color_modes:
            action = QAction(mode.capitalize(), self)
            action.setCheckable(True)
            if mode == 'solid':
                action.setChecked(True)
            action.triggered.connect(lambda checked, m=mode: self.main_window.set_path_color_mode(m))
            self.color_mode_group.addAction(action)
            self.color_mode_menu.addAction(action)

        self.boundary_menu = self.track_map_menu.addMenu('Boundaries')
        
        self.show_boundary_action = QAction('Show Boundaries', self)
        self.show_boundary_action.setCheckable(True)
        self.show_boundary_action.triggered.connect(lambda checked: self.main_window.set_boundary_visibility(checked))
        self.boundary_menu.addAction(self.show_boundary_action)

        

    def create_stages_menu(self, stages):
        self.stage_group = QActionGroup(self)
        self.stage_group.setExclusive(True)

        for stage_name in stages:
            action = QAction(stage_name, self)
            action.setCheckable(True)
            action.triggered.connect(lambda checked, name=stage_name: self.main_window.select_stage(name))
            if stage_name == "None":
                action.setChecked(True)
            self.stage_group.addAction(action)
            self.select_stage_menu.addAction(action)

        