
import pyqtgraph as pg
import numpy as np
from spectral.geometry.polyline import Polyline
from spectral.ui.gui.color_line import ColorLine
from spectral.data.image_processor import generate_path_from_skeleton

class TrackMapWidget(pg.PlotItem):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Ensure image arrays are interpreted in standard numpy row-major order.
        pg.setConfigOption('imageAxisOrder', 'row-major')
        
        # Storage for multiple images
        self.images = {}
        self.current_image_name = None
        
        self.actual_size_meters = None  # To be set when loading image with known scale
        self.prescaled_size_pixels = None  # Original pixel dimensions before scaling to meters

        # ImageItem for displaying the current image
        self.image_item = pg.ImageItem(axisOrder='row-major')
        
        self.addItem(self.image_item)
        
        # ColorLine for path visualization
        self.path_line = None
       
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
        
        # Extract pixel dimensions from the first available image
        if images_dict:
            first_image = next(iter(images_dict.values()))
            if first_image.ndim >= 2:
                height, width = first_image.shape[:2]
                self.prescaled_size_pixels = (width, height)
    
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
                
                # Apply scaling based on actual_size_meters if set
                if self.actual_size_meters is not None:
                    self._apply_image_scaling(image_data)
                    
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
    
    def _apply_image_scaling(self, image_data):
        """
        Apply scaling to the image based on actual_size_meters.
        
        Calculates scale factor from image pixel dimensions and actual_size_meters,
        then applies it to the ImageItem so axes show actual physical coordinates.
        Stores prescaled pixel dimensions for later use in scaling paths.
        
        Args:
            image_data: The image array (2D for grayscale, 3D for color)
        """
        if image_data.ndim >= 2:
            # Get image dimensions (height, width in pixels)
            height, width = image_data.shape[:2]
            
            # Store prescaled pixel dimensions for later use in path scaling
            self.prescaled_size_pixels = (width, height)
            
            # Extract width dimension from actual_size_meters
            # Format can be a single value or [width, height] list
            if isinstance(self.actual_size_meters, (list, tuple)):
                actual_width_meters = self.actual_size_meters[0]
            else:
                actual_width_meters = self.actual_size_meters
            
            # Scale factor converts pixels to meters
            scale_factor = actual_width_meters / width
            
            # Apply scale to the ImageItem
            # setScale sets the pixel size in plot coordinates
            self.image_item.setScale(scale_factor)
            
            print(f"Image scaled: {width}px = {actual_width_meters}m, scale factor: {scale_factor}")
    
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
        if self.path_line is not None:
            self.path_line.erase()
        
        try:
            # Generate path from skeleton (in pixel coordinates)
            polyline = generate_path_from_skeleton(skeleton, position=position, epsilon=epsilon)
            
            # Scale polyline from pixel coordinates to real-world meters if scaling is available
            if self.actual_size_meters is not None and self.prescaled_size_pixels is not None:
                # Extract prescaled pixel dimensions
                prescaled_width, prescaled_height = self.prescaled_size_pixels
                
                # Extract meter dimensions from actual_size_meters
                if isinstance(self.actual_size_meters, (list, tuple)):
                    actual_width_meters = self.actual_size_meters[0]
                    actual_height_meters = self.actual_size_meters[1] if len(self.actual_size_meters) > 1 else actual_width_meters
                else:
                    actual_width_meters = self.actual_size_meters
                    actual_height_meters = self.actual_size_meters
                
                # Calculate scale factors from pixels to meters
                scale_x = actual_width_meters / prescaled_width
                scale_y = actual_height_meters / prescaled_height
                
                polyline = polyline.scale(scale_x, scale_y)
            
            # Use the Polyline directly
            self.path_line = ColorLine(polyline, parent_plot=self)
            self.path_line.set_color_mode(color_mode)
            
            self.path_line.hide()  # Start hidden by default
            
            return self.path_line
        
        except ValueError as e:
            print(f"Error creating path from skeleton: {e}")
            return None
        
    def create_boundary_lines(self, width: float):
        left_boundary_polyline, right_boundary_polyline = self.path_line.polyline.offset_polyline(offset=(width / 2))

        self.left_boundary_line = ColorLine(left_boundary_polyline, parent_plot=self)
        self.right_boundary_line = ColorLine(right_boundary_polyline, parent_plot=self)

        return self.left_boundary_line, self.right_boundary_line
    
    def update_robot_position(self, distance_along_path : float):
        """
        Update and display the robot position marker along the path.
        
        Args:
            distance_along_path: Distance from the start of the path in meters.
        """
        x, y = self.path_line.polyline.point_at_distance(distance_along_path)
        
        # Create or update robot position marker
        if not hasattr(self, 'robot_marker'):
            self.robot_marker = pg.ScatterPlotItem(pxMode=False)
            self.addItem(self.robot_marker)
        
        self.robot_marker.setData(x=[x], y=[y], size=0.05, brush=pg.mkBrush('red'))
