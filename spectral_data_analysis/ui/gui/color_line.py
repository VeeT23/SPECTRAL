from geometry.polyline import Polyline
import matplotlib
import numpy as np
import pyqtgraph as pg

color_modes = ['solid', 'length', 'curvature']

class ColorLine:
    def __init__(self, polyline: Polyline, parent_plot=None):
        """
        A visual representation of a PolyLine
        Args:
            polyline: The PolyLine object to visualize
            parent_plot: Optional reference to the parent plot widget
        """
        self.polyline = polyline
        self.parent_plot = parent_plot  # Reference to parent plot widget
        self.visible = False  # Track visibility state
        self.graphics_item = None  # Will hold the pyqtgraph graphics item
        self.graphics_items = []  # List to hold individual segment line items
        self.set_colormap('viridis')  # Default colormap
        self.set_color_mode('solid')  # Default color mode
    
    def _data_to_color(self, data: list) -> list:
        """
        Convert a list of data values to corresponding colors using the current colormap.
        
        Args:
            data: A list of numerical values to be mapped to colors.
        
        Returns:
            A list of RGBA color tuples corresponding to the input data values.
        """
        # Normalize data to range [0, 1]
        norm_data = (data - min(data)) / (max(data) - min(data))
        
        # Map normalized data to colors using the colormap
        colors = []

        for value in norm_data:
            rgba = self.cmap(value)  # Returns RGBA tuple with values in [0, 1]
            # Convert to QColor format (0-255 range)
            colors.append(pg.mkColor(int(rgba[0]*255), int(rgba[1]*255), int(rgba[2]*255)))

        return colors

    def set_colormap(self, colormap: str):
        """
        Uses matplotlib colormaps to set the color of the line based on the chosen colormap.
        Args:
            colormap: A string representing the colormap to use (e.g., 'viridis', 'plasma', 'inferno', etc.)
        """
        self.cmap = matplotlib.colormaps[colormap]

    def set_color_mode(self, mode: str):
        """
        Set the color mode for the line and generate segment colors.
        
        Args:
            mode: A string representing the color mode [solid, length, curvature]
        """

        print(f"Setting color mode to: {mode}")
        self.color_mode = mode
        num_segments = len(self.polyline) - 1
        
        if mode == 'solid':
            # All segments get the same color (grey)
            self.segment_colors = [pg.mkColor(128, 128, 128)] * num_segments
        
        elif mode == 'length':
            # Color segments based on their lengths
            segment_lengths = self.polyline.get_segment_lengths()
            self.segment_colors = self._data_to_color(np.array(segment_lengths))
        
        elif mode == 'curvature':
            # Color segments based on curvature at vertices
            curvatures = self.polyline.get_segment_curvature()
            if curvatures:
                # Pad with 0s at endpoints to match number of segments
                # We have len(points) - 2 curvatures, but len(points) - 1 segments
                padded_curvatures = [0] + curvatures + [0]
                self.segment_colors = self._data_to_color(np.array(padded_curvatures))
            else:
                self.segment_colors = [pg.mkColor(128, 128, 128)] * num_segments
        
        else:
            raise ValueError(f"Unknown color mode: {mode}. Must be 'solid', 'length', or 'curvature'.")
        
        # Redraw if parent plot is set
        if self.parent_plot is not None:
            self.draw(self.parent_plot)
    
    def show(self):
        """
        Show the color line.
        
        If parent plot is set, draws the line. Otherwise, makes existing graphics items visible.
        Sets the visibility flag to True.
        """
        print("Showing color line")
        self.visible = True
        
        # If parent plot is set but we haven't drawn yet, draw now
        if self.parent_plot is not None and not self.graphics_items:
            self.draw(self.parent_plot)
        
        # Show existing graphics items
        for item in self.graphics_items:
            item.show()
    
    def hide(self):
        """
        Hide the color line.
        
        If a graphics item exists, makes it invisible.
        Sets the visibility flag to False.
        """
        print("Hiding color line")
        self.visible = False
        if self.graphics_item is not None:
            self.graphics_item.hide()
        for item in self.graphics_items:
            item.hide()
    
    def draw(self, plot_item):
        """
        Draw the colored polyline on the given plot item.
        
        Creates line segments for each part of the polyline, colored according 
        to the current color mode. Adds all segments to the parent plot widget.
        
        Args:
            plot_item: The parent pyqtgraph PlotItem (e.g., TrackMapWidget) 
                      to add the line segments to.
        """

        print("Drawing color line")
        self.parent_plot = plot_item
        self.erase()  # Clear any existing graphics items
        
        points = self.polyline.get_points()
        colors = self.segment_colors
        
        # Create a line item for each segment
        for i in range(len(points) - 1):
            p1 = np.array(points[i][:2])  # Take only x, y for 2D plotting
            p2 = np.array(points[i + 1][:2])
            
            # Extract x and y coordinates separately
            x_coords = np.array([p1[0], p2[0]], dtype=float)
            y_coords = np.array([p1[1], p2[1]], dtype=float)
            
            # Create PlotCurveItem with appropriate color
            color = colors[i]
            curve = pg.PlotCurveItem(x=x_coords, y=y_coords, pen=pg.mkPen(color, width=4))
            
            # Add to plot and track
            plot_item.addItem(curve)
            self.graphics_items.append(curve)
            
            if not self.visible:
                curve.hide()
    
    def erase(self):
        """
        Remove all graphics items from the parent plot and clear references.
        """
        if self.parent_plot is not None:
            for item in self.graphics_items:
                self.parent_plot.removeItem(item)
        self.graphics_items = []

