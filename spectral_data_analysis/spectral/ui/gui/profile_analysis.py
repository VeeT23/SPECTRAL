import pyqtgraph as pg
import numpy as np
from spectral.geometry.polyline import Polyline


class ProfileAnalysisWidget(pg.PlotItem):
    """
    A widget for visualizing polyline characteristics (e.g., curvature) against distance.
    
    Displays one or more profiles as line plots where the X-axis represents distance
    along the polyline and the Y-axis represents the characteristic value (curvature, etc).
    """
    
    def __init__(self, parent=None):
        """
        Initialize the ProfileAnalysisWidget.
        
        Args:
            parent: Optional parent widget
        """
        super().__init__(parent)
        
        self.polyline = None
        self.distance_values = []
        self.curvature_values = []
        self.angle_values = []
        self.curve = None  # Current plotted curve
        self.robot_distance = None
        self.robot_line = None  # Vertical line for robot position
        self.mode = 'angle'  # Current analysis mode
        
        # Configure plot
        self.setLabel('bottom', 'Distance', units='m')
        self.setLabel('left', 'Interior Angle', units='rad')
        self.setTitle('Polyline Profile Analysis')
        self.showGrid(x=True, y=True)
            
    def set_polyline(self, polyline_obj: Polyline) -> None:
        """
        Set the polyline to analyze and update the profile plot.
        
        Args:
            polyline_obj: A Polyline object to analyze
        """
        self.polyline = polyline_obj
        self._update_profile_for_mode()
    
    def _calculate_cumulative_distances(self) -> np.ndarray:
        """
        Calculate cumulative distances along the polyline at each vertex.
        
        Returns:
            numpy array of cumulative distances at each vertex
        """
        segment_lengths = self.polyline.get_segment_lengths()
        cumulative = [0.0]
        for length in segment_lengths:
            cumulative.append(cumulative[-1] + length)
        return np.array(cumulative)
    
    def _update_curvature_profile(self) -> None:
        """
        Update the curvature profile plot based on the current polyline.
        """
        if self.polyline is None or len(self.polyline.get_points()) < 3:
            self.clear()
            return
        
        # Get curvatures at interior vertices
        curvatures = self.polyline.get_segment_curvature()
        
        if not curvatures:
            self.clear()
            return
        
        # Calculate cumulative distances
        cumulative_distances = self._calculate_cumulative_distances()
        
        # Map curvatures to distances at interior vertices
        # Curvature[i] is the turning angle at vertex i+1
        # So it should be plotted at the distance to vertex i+1
        distance_values = cumulative_distances[1:-1]  # Distances to vertices 1 to N-2
        curvature_values = np.array(curvatures)
        
        self.distance_values = distance_values
        self.curvature_values = curvature_values
        
        # Clear previous plot
        self.clear()
        
        # Plot the curvature profile
        self.curve = self.plot(
            distance_values,
            curvature_values,
            pen=pg.mkPen(color=(0, 200, 255), width=2),
            symbol='o',
            symbolSize=5,
            symbolBrush=(50, 150, 200)
        )
    
    def _update_angle_profile(self) -> None:
        """
        Update the angle profile plot based on the current polyline.
        """
        if self.polyline is None or len(self.polyline.get_points()) < 3:
            self.clear()
            return
        
        # Get interior angles at vertices
        angles = self.polyline.compute_segment_angles()
        
        if len(angles) == 0:
            self.clear()
            return
        
        # Calculate cumulative distances
        cumulative_distances = self._calculate_cumulative_distances()
        
        # Map angles to distances at interior vertices
        # angle[i] is the interior angle at vertex i+1
        # So it should be plotted at the distance to vertex i+1
        distance_values = cumulative_distances[1:-1]  # Distances to vertices 1 to N-2
        angle_values = np.array(angles)
        
        self.distance_values = distance_values
        self.angle_values = angle_values
        
        # Clear previous plot
        self.clear()
        
        # Plot the angle profile - ensure arrays are compatible lengths
        if len(distance_values) > 0 and len(angle_values) > 0:
            self.curve = self.plot(
                distance_values,
                angle_values,
                pen=pg.mkPen(color=(0, 255, 100), width=2),
                symbol='s',
                symbolSize=5,
                symbolBrush=(100, 200, 50)
            )
    
    def _update_profile_for_mode(self) -> None:
        """
        Update the profile plot based on the current mode.
        """
        if self.mode == 'curvature':
            self._update_curvature_profile()
        elif self.mode == 'angle':
            self._update_angle_profile()
        else:
            raise ValueError(f"Unknown mode: {self.mode}")
    
    def get_profile_data(self) -> tuple:
        """
        Get the current profile data points.
        
        Returns:
            Tuple of (distance_values, curvature_values) as numpy arrays
        """
        return np.array(self.distance_values), np.array(self.curvature_values)
    
    def set_mode(self, mode: str = 'curvature') -> None:
        """
        Set the profile analysis mode ('curvature' or 'angle').
        
        Args:
            mode: Analysis mode ('curvature' or 'angle')
        
        Raises:
            ValueError: If an unsupported mode is specified
        """
        if mode not in ('curvature', 'angle'):
            raise ValueError(f"Unknown mode: {mode}. Currently supported: 'curvature', 'angle'")
        
        self.mode = mode
        
        if self.polyline is not None:
            self._update_profile_for_mode()
            
            if mode == 'curvature':
                self.setLabel('left', 'Segment Curvature', units='rad')
            elif mode == 'angle':
                self.setLabel('left', 'Interior Angle', units='rad')

    def update_robot_position(self, robot_distance: float) -> None:
        """
        Update the robot position vertical line on the profile plot.
        
        Args:
            robot_distance: The distance along the polyline where the robot is located (in meters)
        """
        self.robot_distance = robot_distance
        
        # Remove the old line if it exists
        if self.robot_line is not None:
            self.removeItem(self.robot_line)
        
        # Create a new vertical line at the robot distance
        self.robot_line = pg.InfiniteLine(
            pos=robot_distance,
            angle=90,  # Vertical line
            pen=pg.mkPen(color=(255, 0, 0), width=2, style=pg.QtCore.Qt.PenStyle.DashLine),
        )
        self.addItem(self.robot_line)
