

from PyQt6 import QtWidgets


class MenuBar(QtWidgets.QMenuBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Create File menu
        self.file_menu = self.addMenu('File')
        
        # Create Edit menu
        self.edit_menu = self.addMenu('Edit')
        
        # Create View menu
        self.view_menu = self.addMenu('View')