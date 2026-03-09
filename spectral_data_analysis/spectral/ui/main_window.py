from PyQt6 import QtWidgets
import pyqtgraph as pg
from spectral.io.packet import TelemetryPacket
from spectral.ui.menu_bar import MenuBar
from spectral.ui.gui.track_map import TrackMapWidget
from spectral.data.image_processor import process_image


class MainWindow():
    def __init__(self, config=None):

        self.packets = {}
        self.prev_tick = None

        self.win = QtWidgets.QMainWindow()
        self.win.setWindowTitle("Spectral Data Analysis")
        self.win.resize(900, 700)
        
        # Create and set menubar
        self.menu_bar = MenuBar(self.win, main_window_instance=self)
        self.win.setMenuBar(self.menu_bar)
        
        # Create central widget with GraphicsLayoutWidget to hold the PlotItem
        self.graphics_widget = pg.GraphicsLayoutWidget()
        self.win.setCentralWidget(self.graphics_widget)
        
        # Create and add TrackMapWidget
        self.track_map = TrackMapWidget()
        self.track_map.actual_size_meters = config.data.get('course_size_meters') if config is not None else None
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
                stages = process_image(image_path)
                
                # Convert list of [name, image] to dict for backward compatibility
                stages_dict = {name: image for name, image in stages}
                stage_names = [name for name, _ in stages]
                
                self.track_map.set_images(stages_dict)
                self.track_map.set_path_from_skeleton(stages_dict["Final"])
                self.track_map.actual_size_meters = config.data.get('course_size_meters')
                

                self.track_map.create_boundary_lines(width=config.data.get('robot_sensor_sweep_width_meters', 0.1))
                self.menu_bar.create_stages_menu(["None"] + stage_names)
                
        except Exception as e:
            import traceback
            print(f"Error loading image: {e}")
            traceback.print_exc()
    
    def select_stage(self, stage_name):
        """Select a specific stage to display on the track map."""
        self.track_map.select_image(stage_name)
    
    def set_path_color_mode(self, mode):
        """Set the color mode for the path visualization."""
        print(f"Setting path color mode to: {mode}")
        if self.track_map.path_line is not None:
            self.track_map.path_line.set_color_mode(mode)
    
    def set_path_visibility(self, visible):
        """Show or hide the path visualization."""

        print(f"Setting path visibility to: {visible}")
        if self.track_map.path_line is not None:
            if visible:
                self.track_map.path_line.show()
            else:
                self.track_map.path_line.hide()
    
    def set_boundary_visibility(self, visible):
        """Show or hide the boundary visualization."""

        print(f"Setting boundary visibility to: {visible}")
        if self.track_map.left_boundary_line is not None:
            if visible:
                self.track_map.left_boundary_line.show()
            else:
                self.track_map.left_boundary_line.hide()
        if self.track_map.right_boundary_line is not None:
            if visible:
                self.track_map.right_boundary_line.show()
            else:
                self.track_map.right_boundary_line.hide()

    def on_packet(self, packet : TelemetryPacket):

        if self.prev_tick is not None and packet.ticks_since_idle < self.prev_tick: # New run, reset packets
            self.packets = {}
        
        self.prev_tick = packet.ticks_since_idle
        self.packets[packet.ticks_since_idle] = packet
        ticks = sorted(self.packets.keys())
        if len(ticks) == 0:
            return
        most_recent = self.packets[ticks[len(ticks) - 1]]
        self.track_map.update_robot_position(most_recent.distance)