import pyqtgraph as pg
import numpy as np
from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QCursor

class IRSensorWidget(pg.PlotItem):
    def __init__(self,parent=None, colormap="inferno"):
        super().__init__(parent)
        self.setTitle("IR Sensor Data")

        self.img = pg.ImageItem()
        self.addItem(self.img)

        self.setLabel("left", "Sensor")
        self.setLabel("bottom", "Distance")

        cmap = pg.colormap.get(colormap)
        self.img.setLookupTable(cmap.getLookupTable())
        
        # Mouse tracking variables
        self.mouse_line = None
        self.last_mouse_x = None
        self.mouse_is_hovering = False
        self.min_distance = None
        self.max_distance = None

    def update(self, data, distances=None):
        """
        Update the IR sensor plot.
        
        Args:
            data: IR sensor data array (shape: [num_packets, num_sensors])
            distances: Optional array of distance values corresponding to each packet
        """
        self.img.setImage(data.T, autoLevels=False, levels=(0,4096))
        
        # If distances provided, map the image coordinates to distance values
        if distances is not None and len(distances) > 0:
            min_dist = distances[0]
            max_dist = distances[-1]
            self.min_distance = min_dist
            self.max_distance = max_dist
            dist_range = max_dist - min_dist if max_dist != min_dist else 1
            num_sensors = data.shape[1]
            
            # Set the rectangle to map image pixels to distance coordinates
            rect = QRectF(min_dist, 0, dist_range, num_sensors)
            self.img.setRect(rect)
    
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
            
            # Clamp to data domain if available
            if self.min_distance is not None and self.max_distance is not None:
                x_value = np.clip(x_value, self.min_distance, self.max_distance)
            
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
            if self.min_distance is not None and self.max_distance is not None:
                clamped_distance = np.clip(distance, self.min_distance, self.max_distance)
            
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

