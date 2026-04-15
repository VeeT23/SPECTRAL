
import pyqtgraph as pg
import numpy as np


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
        self.pid_curve = None
        
        # Current plot mode
        self.plot_mode = 'error'  # 'error', 'pid', or 'both'
        
        # Configure plot
        self.setLabel('bottom', 'Distance', units='m')
        self.setLabel('left', 'Line Error Cubed', units='rad³')
        self.setTitle('Telemetry - Error Cubed vs Distance')
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
        """Update the plot based on the current plot mode and data."""
        # Clear previous plot items
        self.clear()
        
        if len(self.distance_data) == 0:
            return
        
        if self.plot_mode == 'error':
            self._plot_error()
        elif self.plot_mode == 'pid':
            self._plot_pid()
        elif self.plot_mode == 'both':
            self._plot_both()
    
    def _plot_error(self) -> None:
        """Plot line error cubed vs distance with rolling average."""
        self.setLabel('left', 'Line Error Cubed', units='rad³')
        self.setTitle('Telemetry - Error Cubed vs Distance')
        
        # Calculate cubed error
        error_cubed = self.error_data ** 3
        
        # Apply rolling average with window of 5 packets
        window = 5
        if len(error_cubed) >= window:
            # Use convolution for rolling average
            rolling_avg = np.convolve(error_cubed, np.ones(window) / window, mode='valid')
            # Adjust distance data to match the smoothed data
            distance_for_plot = self.distance_data[window - 1:]
        else:
            # If we have fewer packets than window, just use the data as-is
            rolling_avg = error_cubed
            distance_for_plot = self.distance_data
        
        self.error_curve = self.plot(
            distance_for_plot,
            rolling_avg,
            pen=pg.mkPen(color=(255, 0, 0), width=2),
            symbol='o',
            symbolSize=4,
            symbolBrush=(255, 0, 0),
            name='Line Error Cubed (5-packet rolling avg)'
        )
    
    def _plot_pid(self) -> None:
        """Plot PID output vs distance."""
        self.setLabel('left', 'PID Output', units='V')
        self.setTitle('Telemetry - PID Output vs Distance')
        
        self.pid_curve = self.plot(
            self.distance_data,
            self.pid_data,
            pen=pg.mkPen(color=(0, 255, 0), width=2),
            symbol='s',
            symbolSize=4,
            symbolBrush=(0, 255, 0),
            name='PID Output'
        )
    
    def _plot_both(self) -> None:
        """Plot both line error and PID output on same graph with dual axes."""
        # Plot error on left axis
        self.setLabel('left', 'Line Error Cubed', units='rad³')
        self.setTitle('Telemetry - Error Cubed & PID vs Distance')
        
        self.error_curve = self.plot(
            self.distance_data,
            self.error_data,
            pen=pg.mkPen(color=(255, 0, 0), width=2),
            symbol='o',
            symbolSize=4,
            symbolBrush=(255, 0, 0),
            name='Line Error'
        )
        
        # Create right axis for PID output
        right_axis = pg.ViewBox()
        self.showAxis('right')
        self.scene().addItem(right_axis)
        self.getAxis('right').linkToView(right_axis)
        right_axis.setLabel('PID Output', units='V')
        
        # Plot PID on right axis
        pid_curve_item = pg.PlotCurveItem(
            self.distance_data,
            self.pid_data,
            pen=pg.mkPen(color=(0, 255, 0), width=2),
            symbol='s',
            symbolSize=4,
            symbolBrush=(0, 255, 0)
        )
        right_axis.addItem(pid_curve_item)
        self.pid_curve = pid_curve_item
    
    def set_plot_mode(self, mode: str) -> None:
        """
        Set the telemetry plot mode.
        
        Args:
            mode: One of 'error', 'pid', or 'both'
        """
        if mode not in ('error', 'pid', 'both'):
            raise ValueError(f"Unknown mode: {mode}. Must be 'error', 'pid', or 'both'")
        
        self.plot_mode = mode
        self._update_plot()
    
    def clear_data(self) -> None:
        """Clear all telemetry data and reset the plot."""
        self.distance_data = []
        self.error_data = []
        self.pid_data = []
        self.velocity_data = []
        self.steering_data = []
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
