import math
from typing import List, Tuple, Union
import cv2
import numpy as np


class Polyline:
    """
    A class representing a polyline made up of connected line segments.
    
    Attributes:
        points: List of points defining the polyline. Each point can be a tuple (2D or 3D).
    """
    
    def __init__(self, points: List[Tuple[float, ...]]):
        """
        Initialize a Polyline with a list of points.
        
        Args:
            points: List of tuples representing points. 
                   Can be 2D [(x1, y1), (x2, y2), ...] or 3D [(x1, y1, z1), ...].
        
        Raises:
            ValueError: If fewer than 2 points are provided.
        """
        if len(points) < 2:
            raise ValueError("A polyline must have at least 2 points")
        
        self.points = points
    
    def _euclidean_distance(self, point1: Tuple[float, ...], point2: Tuple[float, ...]) -> float:
        """
        Calculate the Euclidean distance between two points.
        
        Args:
            point1: First point as a tuple.
            point2: Second point as a tuple.
        
        Returns:
            The Euclidean distance between the two points.
        """
        return math.sqrt(sum((p2 - p1) ** 2 for p1, p2 in zip(point1, point2)))
    
    def get_segment_lengths(self) -> List[float]:
        """
        Get the lengths of all segments in the polyline.
        
        Returns:
            A list of segment lengths. The list has length = len(points) - 1.
        """
        segment_lengths = []
        for i in range(len(self.points) - 1):
            distance = self._euclidean_distance(self.points[i], self.points[i + 1])
            segment_lengths.append(distance)
        return segment_lengths
    
    def get_total_length(self) -> float:
        """
        Get the total length of the polyline.
        
        Returns:
            The sum of all segment lengths.
        """
        return sum(self.get_segment_lengths())
    
    def add_point(self, point: Tuple[float, ...]) -> None:
        """
        Add a new point to the end of the polyline.
        
        Args:
            point: A tuple representing the new point.
        """
        self.points.append(point)
    
    def get_points(self) -> List[Tuple[float, ...]]:
        """
        Get the list of points in the polyline.
        
        Returns:
            The list of points.
        """
        return self.points
    
    def scale(self, factor_x: float, factor_y: float) -> 'Polyline':
        """
        Scale the polyline by separate x and y factors.
        
        Args:
            factor_x: Scaling factor to apply to x coordinates.
                     Values > 1 enlarge, values < 1 shrink, values < 0 flip.
            factor_y: Scaling factor to apply to y coordinates.
                     Values > 1 enlarge, values < 1 shrink, values < 0 flip.
        
        Returns:
            A new scaled Polyline object.
        """
        scaled_points = []
        for point in self.points:
            scaled_point = (point[0] * factor_x, point[1] * factor_y) + point[2:]
            scaled_points.append(scaled_point)
        return Polyline(scaled_points)
    
    def get_segment_curvature(self) -> List[float]:
        """
        Get the curvature at each interior vertex (angle change between consecutive segments).
        
        Returns:
            A list of curvature values (in radians). The list has length = len(points) - 2.
            Each value represents the turning angle at that vertex.
            Returns empty list if fewer than 3 points.
        """
        if len(self.points) < 3:
            return []
        
        curvatures = []
        for i in range(1, len(self.points) - 1):
            p0 = np.array(self.points[i - 1][:2])
            p1 = np.array(self.points[i][:2])
            p2 = np.array(self.points[i + 1][:2])
            
            # Vectors for the two segments
            v1 = p1 - p0
            v2 = p2 - p1
            
            # Normalize vectors
            len_v1 = np.linalg.norm(v1)
            len_v2 = np.linalg.norm(v2)
            
            if len_v1 > 0 and len_v2 > 0:
                v1_norm = v1 / len_v1
                v2_norm = v2 / len_v2
                
                # Calculate angle using dot product and cross product
                dot_product = np.dot(v1_norm, v2_norm)
                cross_product = v1_norm[0] * v2_norm[1] - v1_norm[1] * v2_norm[0]
                
                # Angle in radians
                angle = math.atan2(cross_product, dot_product)
                curvatures.append(angle)
            else:
                curvatures.append(0.0)
        
        return curvatures
    
    def __repr__(self) -> str:
        """String representation of the Polyline."""
        return f"Polyline(points={self.points})"
    
    def __len__(self) -> int:
        """Return the number of points in the polyline."""
        return len(self.points)
    
    def simplify(self, epsilon: float = 1.0) -> 'Polyline':
        """
        Simplify the polyline using Ramer-Douglas-Peucker (RDP) simplification.
        
        Args:
            epsilon: Maximum distance in pixels from original to simplified path.
                    Larger epsilon → fewer points on straight segments.
        
        Returns:
            A new simplified Polyline object.
        """
        if len(self.points) < 3:
            return Polyline(self.points)
        
        # Convert points to numpy array for OpenCV
        points_array = np.array(self.points, dtype=np.float32)
        points_int = points_array.astype(np.int32).reshape(-1, 1, 2)
        simplified = cv2.approxPolyDP(points_int, epsilon=epsilon, closed=False)
        simplified = simplified.reshape(-1, 2).astype(float)
        simplified_points = [tuple(p) for p in simplified]
        
        return Polyline(simplified_points)
