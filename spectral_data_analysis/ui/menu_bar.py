

from PyQt6 import QtWidgets
from PyQt6.QtGui import QAction, QActionGroup


class MenuBar(QtWidgets.QMenuBar):
    def __init__(self, parent=None, main_window_instance=None):
        super().__init__(parent)
        self.main_window = main_window_instance
        
        # Create File menu
        self.file_menu = self.addMenu('File')
        
        # Create Edit menu
        self.edit_menu = self.addMenu('Edit')
        
        # Create View menu
        self.view_menu = self.addMenu('View')

        self.track_map_menu = self.view_menu.addMenu('Track Map')

        self.stage_group = QActionGroup(parent)
        self.stage_group.setExclusive(True)


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
            self.track_map_menu.addAction(action)

        