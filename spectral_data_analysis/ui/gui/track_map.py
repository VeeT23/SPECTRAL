

import pyqtgraph as pg
import numpy as np


class TrackMapWidget(pg.PlotItem):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Storage for multiple images
        self.images = []
        self.current_index = -1
        
        # ImageItem for displaying the current image
        self.image_item = pg.ImageItem()
        self.addItem(self.image_item)
        
        # Real world dimensions (width, height in real units)
        self.real_world_size = None
        
        # Configure plot
        self.setAspectLocked(True)
        self.invertY(True)  # Typical image coordinate system
        
    def add_image(self, image_data, real_world_size=None):
        """
        Add an image to the storage array.
        
        Args:
            image_data: numpy array containing image data
            real_world_size: tuple (width, height) in real world units
        
        Returns:
            Index of the added image
        """
        self.images.append({
            'data': np.array(image_data),
            'real_world_size': real_world_size
        })
        
        # If this is the first image, display it
        if len(self.images) == 1:
            self.select_image(0)
            
        return len(self.images) - 1
    
    def select_image(self, index):
        """
        Select and display a specific image from the array.
        
        Args:
            index: Index of the image to display
        """
        if 0 <= index < len(self.images):
            self.current_index = index
            image_info = self.images[index]
            
            # Set the image data
            self.image_item.setImage(image_info['data'])
            
            # Apply real world scaling if available
            if image_info['real_world_size'] is not None:
                self.real_world_size = image_info['real_world_size']
                self._apply_real_world_scaling()
            else:
                self.real_world_size = None
                
    def _apply_real_world_scaling(self):
        """
        Apply real world scaling to the image display.
        """
        if self.real_world_size is not None and self.current_index >= 0:
            image_data = self.images[self.current_index]['data']
            width, height = self.real_world_size
            
            # Calculate scale factors
            img_height, img_width = image_data.shape[:2]
            scale_x = width / img_width
            scale_y = height / img_height
            
            # Create transform for scaling
            tr = pg.QtGui.QTransform()
            tr.scale(scale_x, scale_y)
            
            self.image_item.setTransform(tr)
            
            # Update axis labels
            self.setLabel('bottom', 'X', units='m')
            self.setLabel('left', 'Y', units='m')
    
    def get_current_image(self):
        """
        Get the currently displayed image data.
        
        Returns:
            numpy array of current image or None
        """
        if self.current_index >= 0:
            return self.images[self.current_index]['data']
        return None
    
    def clear_images(self):
        """
        Clear all stored images.
        """
        self.images = []
        self.current_index = -1
        self.image_item.clear()
        self.real_world_size = None