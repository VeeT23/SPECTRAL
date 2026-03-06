from PyQt6 import QtWidgets
import pyqtgraph as pg
from ui.menu_bar import MenuBar
from ui.gui.track_map import TrackMapWidget
from data.image_processor import process_image

class MainWindow():
    def __init__(self, config=None):
        
        self.win = QtWidgets.QMainWindow()
        self.win.setWindowTitle("Spectral Data Analysis")
        self.win.resize(900, 700)
        
        # Create and set menubar
        self.menu_bar = MenuBar(self.win)
        self.win.setMenuBar(self.menu_bar)
        
        # Create central widget with GraphicsLayoutWidget to hold the PlotItem
        self.graphics_widget = pg.GraphicsLayoutWidget()
        self.win.setCentralWidget(self.graphics_widget)
        
        # Create and add TrackMapWidget
        self.track_map = TrackMapWidget()
        self.graphics_widget.addItem(self.track_map)
        
        # Load and process image if config is provided
        if config is not None:
            self._load_image_from_config(config)

        self.win.show()
    
    def _load_image_from_config(self, config):
        """Load and process image from config file path."""
        try:
            image_path = config.data.get('course_filepath')
            if image_path:
                # Process the image
                stages, filtered = process_image(image_path)
                
                # Add all processing stages to the widget
                for stage in stages:
                    self.track_map.add_image(stage, config.data.get('course_size_meters'))
                    
                # Display the first image (original)
                self.track_map.select_image(0)
        except Exception as e:
            print(f"Error loading image: {e}")
    