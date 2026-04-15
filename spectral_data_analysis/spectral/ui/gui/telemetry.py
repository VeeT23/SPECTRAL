
import pyqtgraph as pg
import numpy as np
from scipy.signal import savgol_filter
from PyQt6.QtGui import QCursor


class TelemetryWidget(pg.PlotItem):
    """
    A widget for visualizing telemetry data from packets across distance.
    
    Displays metrics such as line error, PID output, velocity, and steering angle
    plotted against distance traveled along the track.
    """
    
    def __init__(self, parent=None):
        """
        Initialize the TelemetryWidget.
        
        Args:
            parent: Optional parent widget
        """
        super().__init__(parent)
        
        # Data storage
        self.distance_data = []
        self.error_data = []
        self.pid_data = []
        self.velocity_data = []
        self.steering_data = []
        
        # Plot curves
        self.error_curve = None
        self.highlight_regions = []
        
        # Mouse tracking variables
        self.mouse_line = None
        self.last_mouse_x = None
        self.mouse_is_hovering = False
        
        # Configure plot
        self.setLabel('bottom', 'Distance', units='m')
        self.setLabel('left', 'Line Error')
        self.setTitle('Telemetry - Error vs Distance')
        self.showGrid(x=True, y=True)
        
    def update_with_packets(self, packets_dict: dict) -> None:
        """
        Update the telemetry plot with packet data.
        
        Extracts distance and error values from packets sorted by ticks_since_idle
        and updates the plot accordingly.
        
        Args:
            packets_dict: Dictionary of packets keyed by ticks_since_idle
        """
        if not packets_dict:
            return
        
        # Sort packets by tick to maintain order
        sorted_ticks = sorted(packets_dict.keys())
        
        # Extract data
        distance_values = []
        error_values = []
        pid_values = []
        velocity_values = []
        steering_values = []
        
        for tick in sorted_ticks:
            packet = packets_dict[tick]
            distance_values.append(packet.distance)
            error_values.append(packet.line_error)
            pid_values.append(packet.pid_output)
            velocity_values.append(packet.velocity)
            steering_values.append(packet.steering)
        
        self.distance_data = np.array(distance_values)
        self.error_data = np.array(error_values)
        self.pid_data = np.array(pid_values)
        self.velocity_data = np.array(velocity_values)
        self.steering_data = np.array(steering_values)
        
        # Update the plot
        self._update_plot()
    
    def _update_plot(self) -> None:
        """Update the plot to display line error vs distance."""
        # Clear previous plot items
        self.clear()
        
        if len(self.distance_data) == 0:
            return
        
        self._plot_error()
    
    def _plot_error(self) -> None:
        """Plot line error vs distance."""
        self.setLabel('left', 'Line Error', units='rad/m')
        self.setTitle('Telemetry - Error vs Distance')
        
        # Take the cube of the error to exaggerate differences, then clamp
        error = self.error_data ** 3

        # Smooth sharp spikes while preserving maintained stretches using Savitzky-Golay filter
        if len(error) >= 5:
            error = savgol_filter(error, window_length=5, polyorder=2)

        error = np.clip(error, -100, 100)
        # Round values between -20 and 20 to zero
        error = np.where(np.abs(error) < 20, 0, error)
        
        
        
        # Find and highlight regions where error > 20 until 5 consecutive zeros
        regions = self._find_highlight_regions(error)
        for start, end in regions:
            region = pg.LinearRegionItem(values=[start, end], orientation='vertical',
                                        brush=pg.mkBrush(255, 0, 0, 30))
            self.addItem(region)
            self.highlight_regions.append(region)
        
        self.error_curve = self.plot(
            self.distance_data,
            error,
            pen=pg.mkPen(color=(255, 0, 0), width=2),
            symbol='o',
            symbolSize=4,
            symbolBrush=(255, 0, 0),
            name='Line Error'
        )
    
    def _find_highlight_regions(self, error: np.ndarray) -> list:
        """
        Find regions where error > 20 and extend until 5 consecutive zeros or sign change.
        
        Args:
            error: Array of error values
            
        Returns:
            List of (start_distance, end_distance) tuples for regions to highlight
        """
        regions = []
        in_region = False
        region_start = None
        region_sign = None
        consecutive_zeros = 0
        
        for i, err in enumerate(error):
            if abs(err) > 20:
                if not in_region:
                    region_start = self.distance_data[i]
                    region_sign = np.sign(err)
                    in_region = True
                else:
                    # Check for sign change while still > 20
                    if np.sign(err) != region_sign:
                        # Sign change detected - end the region
                        region_end = self.distance_data[i]
                        regions.append((region_start, region_end))
                        # Start a new region with the new sign
                        region_start = self.distance_data[i]
                        region_sign = np.sign(err)
                consecutive_zeros = 0
            elif in_region:
                if abs(err) == 0:  # Zero value
                    consecutive_zeros += 1
                    if consecutive_zeros == 5:
                        # 5 consecutive zeros - end the region
                        region_end = self.distance_data[i]
                        regions.append((region_start, region_end))
                        in_region = False
                        consecutive_zeros = 0
                        region_sign = None
                else:  # Non-zero value below threshold
                    # Check if this is a sign change
                    if np.sign(err) != region_sign:
                        # Sign change detected - end the region
                        region_end = self.distance_data[i]
                        regions.append((region_start, region_end))
                        in_region = False
                        consecutive_zeros = 0
                        region_sign = None
                    else:
                        consecutive_zeros = 0
        
        # Handle case where region extends to end of data
        if in_region:
            regions.append((region_start, self.distance_data[-1]))
        
        return regions
    

    
    def clear_data(self) -> None:
        """Clear all telemetry data and reset the plot."""
        self.distance_data = []
        self.error_data = []
        self.pid_data = []
        self.velocity_data = []
        self.steering_data = []
        self.highlight_regions = []
        self.clear()
    
    def get_telemetry_data(self) -> dict:
        """
        Get current telemetry data.
        
        Returns:
            Dictionary with keys 'distance', 'error', 'pid', 'velocity', 'steering'
        """
        return {
            'distance': np.array(self.distance_data),
            'error': np.array(self.error_data),
            'pid': np.array(self.pid_data),
            'velocity': np.array(self.velocity_data),
            'steering': np.array(self.steering_data),
        }
    
    def track_mouse_position(self) -> float:
        """
        Get the current mouse position and manage a blue vertical line at that x coordinate.
        
        Returns:
            float: The x value (distance in meters) of the mouse position over the graph,
                   clamped to the data domain, or None if the mouse is not hovering
        """
        view_box = self.getViewBox()
        if view_box is None:
            return None
        
        scene = self.scene()
        if scene is None:
            return None
        
        views = scene.views()
        if not views:
            return None
        
        view = views[0]
        
        # Get global mouse position and convert to view coordinates
        global_mouse_pos = QCursor.pos()
        local_mouse_pos = view.mapFromGlobal(global_mouse_pos)
        
        # Convert to scene coordinates
        scene_pos = view.mapToScene(local_mouse_pos)
        
        # Convert to data coordinates
        data_pos = view_box.mapSceneToView(scene_pos)
        
        # Get the plot's scene bounding rectangle
        plot_rect = view_box.sceneBoundingRect()
        
        # Check if mouse is within the plot bounds
        if plot_rect.contains(scene_pos):
            # Mouse is hovering over the graph
            x_value = data_pos.x()
            
            # Clamp to curve domain if we have distance values
            if len(self.distance_data) > 0:
                min_distance = float(np.min(self.distance_data))
                max_distance = float(np.max(self.distance_data))
                x_value = np.clip(x_value, min_distance, max_distance)
            
            self.last_mouse_x = x_value
            self.mouse_is_hovering = True
            
            # Create or update the line
            if self.mouse_line is None:
                self.mouse_line = pg.InfiniteLine(
                    pos=x_value,
                    angle=90,
                    pen=pg.mkPen(color=(0, 0, 255), width=2),
                )
                self.addItem(self.mouse_line)
            else:
                self.mouse_line.setValue(x_value)
            
            return x_value
        else:
            # Mouse is not hovering over the graph
            self.mouse_is_hovering = False
            
            if self.mouse_line is not None:
                self.removeItem(self.mouse_line)
                self.mouse_line = None
            
            self.last_mouse_x = None
            return None
    
    def set_highlight_line(self, distance: float = None) -> None:
        """
        Set the position of the highlight line externally.
        
        Args:
            distance: The distance value for the highlight line, or None to hide it
        """
        if distance is None:
            # Hide the line
            if self.mouse_line is not None:
                self.removeItem(self.mouse_line)
                self.mouse_line = None
            self.last_mouse_x = None
        else:
            # Clamp to data domain if available
            clamped_distance = distance
            if len(self.distance_data) > 0:
                min_distance = float(np.min(self.distance_data))
                max_distance = float(np.max(self.distance_data))
                clamped_distance = np.clip(distance, min_distance, max_distance)
            
            self.last_mouse_x = clamped_distance
            
            # Create or update the line
            if self.mouse_line is None:
                self.mouse_line = pg.InfiniteLine(
                    pos=clamped_distance,
                    angle=90,
                    pen=pg.mkPen(color=(0, 0, 255), width=2),
                )
                self.addItem(self.mouse_line)
            else:
                self.mouse_line.setValue(clamped_distance)
    
    def mouseMoveEvent(self, event):
        """Handle mouse movement over the plot."""
        super().mouseMoveEvent(event)
    
    def leaveEvent(self, event):
        """Handle mouse leaving the plot area."""
        super().leaveEvent(event)
