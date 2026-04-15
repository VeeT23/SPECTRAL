from PyQt6 import QtWidgets
import numpy as np
import pyqtgraph as pg
from spectral.io.packet import TelemetryPacket
from spectral.ui.menu_bar import MenuBar
from spectral.ui.gui.track_map import TrackMapWidget
from spectral.ui.gui.ir_sensor_map import IRSensorWidget
from spectral.ui.gui.profile_analysis import ProfileAnalysisWidget
from spectral.ui.gui.telemetry import TelemetryWidget
from spectral.data.image_processor import process_image
from spectral.data.packet_database import TelemetryPacketDatabase

class MainWindow():
    # Default grid layout configuration for widgets
    DEFAULT_LAYOUT = {
        'track_map': {'row': 0, 'col': 0, 'rowspan': 2, 'colspan': 1},
        'ir_sensor': {'row': 0, 'col': 1, 'rowspan': 1, 'colspan': 1},
        'profile_analysis': {'row': 1, 'col': 1, 'rowspan': 1, 'colspan': 1},
        'telemetry': {'row': 2, 'col': 0, 'rowspan': 1, 'colspan': 2},
    }

    def __init__(self, config=None, layout=None):

        self.packet_database = TelemetryPacketDatabase()

        self.win = QtWidgets.QMainWindow()
        self.win.setWindowTitle("Spectral Data Analysis")
        self.win.resize(1000, 1000)
        
        # Create and set menubar
        self.menu_bar = MenuBar(self.win, main_window_instance=self)
        self.win.setMenuBar(self.menu_bar)
        
        # Create central widget with GraphicsLayoutWidget to hold the PlotItem
        self.graphics_widget = pg.GraphicsLayoutWidget()
        self.win.setCentralWidget(self.graphics_widget)
        
        # Use provided layout or default layout
        grid_layout = layout if layout is not None else self.DEFAULT_LAYOUT

        # Create and add TrackMapWidget
        self.track_map = TrackMapWidget()
        self.track_map.actual_size_meters = config.data.get('course_size_meters') if config is not None else None
        self._add_widget_to_grid(self.track_map, grid_layout['track_map'])

        # Create and Add IRSensorWidget
        self.ir_sensor = IRSensorWidget()
        self._add_widget_to_grid(self.ir_sensor, grid_layout['ir_sensor'])
        
        # Create and Add ProfileAnalysisWidget
        self.profile_analysis = ProfileAnalysisWidget()
        self.profile_analysis.set_mode('angle')  # Default to angle mode
        self._add_widget_to_grid(self.profile_analysis, grid_layout['profile_analysis'])
        
        # Create and Add TelemetryWidget
        self.telemetry = TelemetryWidget()
        self._add_widget_to_grid(self.telemetry, grid_layout['telemetry'])
        
        # Load and process image if config is provided
        if config is not None:
            self._load_image_from_config(config)

        
        self.win.show()
    
    def _add_widget_to_grid(self, widget, layout_info):
        """
        Add a widget to the graphics layout grid with row/col positioning.
        
        Args:
            widget: The widget to add
            layout_info: Dict with keys 'row', 'col', 'rowspan', 'colspan'
                Example: {'row': 0, 'col': 0, 'rowspan': 2, 'colspan': 1}
        """
        row = layout_info.get('row', 0)
        col = layout_info.get('col', 0)
        rowspan = layout_info.get('rowspan', 1)
        colspan = layout_info.get('colspan', 1)
        
        self.graphics_widget.addItem(widget, row=row, col=col, rowspan=rowspan, colspan=colspan)
    
    def set_widget_layout(self, widget_name, row, col, rowspan=1, colspan=1):
        """
        Update an existing widget's grid position and span.
        
        Args:
            widget_name: Name of widget ('track_map', 'ir_sensor', or 'profile_analysis')
            row: Row position (0-indexed)
            col: Column position (0-indexed)
            rowspan: Number of rows the widget spans (default: 1)
            colspan: Number of columns the widget spans (default: 1)
        """
        if not hasattr(self, widget_name):
            raise ValueError(f"Widget '{widget_name}' not found")
        
        widget = getattr(self, widget_name)
        # Update the DEFAULT_LAYOUT for reference
        if widget_name in self.DEFAULT_LAYOUT:
            self.DEFAULT_LAYOUT[widget_name] = {
                'row': row, 'col': col, 'rowspan': rowspan, 'colspan': colspan
            }
        
        # Note: PyQtGraph doesn't support dynamic grid repositioning after initial add.
        # To change layout, you would need to rebuild the graphics_widget.
        print(f"Layout info for {widget_name} updated to: row={row}, col={col}, rowspan={rowspan}, colspan={colspan}")
    
    def rebuild_layout(self, new_layout):
        """
        Rebuild the entire widget layout with a new configuration.
        Useful when you want to dynamically change the grid layout.
        
        Args:
            new_layout: Dict mapping widget names to their layout info
                Example: {
                    'track_map': {'row': 0, 'col': 0, 'rowspan': 2, 'colspan': 2},
                    'ir_sensor': {'row': 0, 'col': 2, 'rowspan': 1, 'colspan': 1},
                    'profile_analysis': {'row': 1, 'col': 2, 'rowspan': 1, 'colspan': 1},
                    'telemetry': {'row': 2, 'col': 0, 'rowspan': 1, 'colspan': 2},
                }
        """
        # Store widget references
        widgets = {
            'track_map': self.track_map,
            'ir_sensor': self.ir_sensor,
            'profile_analysis': self.profile_analysis,
            'telemetry': self.telemetry,
        }
        
        # Clear the existing layout
        for item in list(self.graphics_widget.items):
            self.graphics_widget.removeItem(item)
        
        # Re-add widgets with new layout
        for widget_name, layout_info in new_layout.items():
            if widget_name in widgets:
                self._add_widget_to_grid(widgets[widget_name], layout_info)
        
        self.DEFAULT_LAYOUT.update(new_layout)
    
    def get_layout_config(self):
        """Return the current layout configuration."""
        return self.DEFAULT_LAYOUT.copy()
    
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
                
                # Update profile analysis widget with the polyline data
                self._update_profile_analysis()

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
    
    def _update_profile_analysis(self):
        """Update profile analysis widget with polyline data from track map."""
        if self.track_map.path_line is not None:
            polyline = self.track_map.path_line.polyline
            self.profile_analysis.set_polyline(polyline)

    def on_packet(self, packet : TelemetryPacket):

        is_new_run = self.packet_database.add_packet(packet)
        
        if is_new_run:
            self.telemetry.clear_data()
        
        most_recent = self.packet_database.get_most_recent_packet()
        if most_recent is None:
            return
        
        self.track_map.update_robot_position(most_recent.distance)
        self.profile_analysis.update_robot_position(most_recent.distance)
        
        packets_list = self.packet_database.get_all_packets()
        self.ir_sensor.update(np.array([p.ir_raw for p in packets_list]))
        
        # Update telemetry widget with all packets
        self.telemetry.update_with_packets(self.packet_database.get_packets_dict())
    
    def load_file(self):
        """Open a file picker and load a packet file."""
        from pathlib import Path
        
        # Open file picker dialog
        session_folder = Path("session")
        file_dialog = QtWidgets.QFileDialog(self.win)
        file_dialog.setDirectory(str(session_folder))
        file_dialog.setNameFilter("JSONL Files (*.jsonl)")
        
        filepath, _ = file_dialog.getOpenFileName(
            self.win,
            "Load Packet File",
            str(session_folder),
            "JSONL Files (*.jsonl)"
        )
        
        if not filepath:
            # User cancelled
            return
        
        try:
            # Load the file into the database
            self.packet_database.load(filepath)
            
            # Update UI with loaded data
            self.telemetry.clear_data()
            
            packets_list = self.packet_database.get_all_packets()
            if packets_list:
                # Update track map and profile analysis with the most recent packet
                most_recent = self.packet_database.get_most_recent_packet()
                self.track_map.update_robot_position(most_recent.distance)
                self.profile_analysis.update_robot_position(most_recent.distance)
                
                # Update IR sensor with all packets
                self.ir_sensor.update(np.array([p.ir_raw for p in packets_list]))
                
                # Update telemetry widget
                self.telemetry.update_with_packets(self.packet_database.get_packets_dict())
        except Exception as e:
            # Show error dialog
            error_dialog = QtWidgets.QMessageBox(self.win)
            error_dialog.setWindowTitle("Error Loading File")
            error_dialog.setText(f"Failed to load file: {e}")
            error_dialog.setIcon(QtWidgets.QMessageBox.Icon.Warning)
            error_dialog.exec()