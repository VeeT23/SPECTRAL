
import pyqtgraph as pg
import numpy as np
from geometry.polyline import Polyline
from ui.gui.color_line import ColorLine
from data.image_processor import generate_path_from_skeleton

class TrackMapWidget(pg.PlotItem):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Ensure image arrays are interpreted in standard numpy row-major order.
        pg.setConfigOption('imageAxisOrder', 'row-major')
        
        # Storage for multiple images
        self.images = {}
        self.current_image_name = None
        
        self.actual_size_meters = None  # To be set when loading image with known scale

        # ImageItem for displaying the current image
        self.image_item = pg.ImageItem(axisOrder='row-major')
        
        self.addItem(self.image_item)
        
        # ColorLine for path visualization
        self.color_line = None
       
        # Configure plot
        self.setAspectLocked(True)
        self.invertY(True)  # Invert Y-axis to match image coordinates

        # Show X coordinates on the top axis instead of bottom.
        self.showAxis('top')
        self.hideAxis('bottom')
        
    def set_images(self, images_dict):
        """
        Set the entire images dictionary.
        
        Args:
            images_dict: Dictionary with format {"image_name": image_array, ...}
        """
        self.images = images_dict
        self.current_image_name = None
        self.image_item.clear()
    
    def select_image(self, image_name):
        """
        Select and display a specific image from the dictionary.
        
        Args:
            image_name: Name/key of the image to display
        """
        if image_name in self.images:
            print(f"Selecting image: {image_name}")

            self.current_image_name = image_name
            image_data = self.images[image_name]
            
            # Ensure image data is in proper format for pyqtgraph
            # For grayscale (2D) or color (3D) images, setImage handles both
            try:
                self.image_item.setImage(image_data, axisOrder='row-major', autoLevels=True)
            except Exception as e:
                print(f"Warning: Error setting image: {e}")
                print(f"Image shape: {image_data.shape}, dtype: {image_data.dtype}")
                return
        elif image_name == "None":
            print("Clearing image display")
            self.current_image_name = None
            self.image_item.clear()
                
    
    def get_current_image(self):
        """
        Get the currently displayed image data.
        
        Returns:
            numpy array of current image or None
        """
        if self.current_image_name is not None and self.current_image_name in self.images:
            return self.images[self.current_image_name]
        return None
    
    def clear_images(self):
        """
        Clear all stored images.
        """
        self.images = {}
        self.current_image_name = None
        self.image_item.clear()
    
    def set_path_from_skeleton(self, skeleton, position=None, epsilon=1.0, color_mode='solid'):
        """
        Create and draw a colored polyline path from a skeleton.
        
        Uses generate_path_from_skeleton to trace the path in pixel coordinates,
        then creates and draws a ColorLine on this widget.
        
        Args:
            skeleton: Binary image where non-zero pixels represent the skeleton
            position: Optional (x, y) tuple to seed the path generation. 
                     If None, starts from the left-most pixel.
            epsilon: Maximum distance in pixels for path simplification.
                    Larger epsilon → fewer points on straight segments.
            color_mode: Color mode for the line ['solid', 'length', 'curvature']
        
        Returns:
            The created ColorLine object, or None if path generation fails
        """
        # Erase any existing color line
        if self.color_line is not None:
            self.color_line.erase()
        
        try:
            # Generate path from skeleton (in pixel coordinates)
            path_points = generate_path_from_skeleton(skeleton, position=position, epsilon=epsilon)
            
            # Convert to list of tuples for Polyline
            points = [tuple(p) for p in path_points]
            
            # Create Polyline in pixel coordinates
            polyline = Polyline(points)
            
            # Create and draw ColorLine
            self.color_line = ColorLine(polyline)
            self.color_line.set_color_mode(color_mode)
            self.color_line.draw(self)
            
            return self.color_line
        
        except ValueError as e:
            print(f"Error creating path from skeleton: {e}")
            return None