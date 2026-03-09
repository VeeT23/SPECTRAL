import math
from typing import List, Tuple, Union, Optional
import cv2
import numpy as np


# ==================== Helper Functions ====================

def normalize(v):
    """Normalize a vector to unit length."""
    norm = np.linalg.norm(v)
    if norm == 0:
        return v
    return v / norm


def perpendicular(v):
    """Compute 90° CCW rotation (left normal) of a vector."""
    return np.array([-v[1], v[0]])


def line_intersection(p1, d1, p2, d2):
    """
    Solve p1 + t*d1 = p2 + u*d2
    
    Returns:
        Intersection point or None if parallel.
    """
    A = np.array([d1, -d2]).T
    b = p2 - p1

    det = np.linalg.det(A)
    if abs(det) < 1e-9:
        return None  # Parallel lines

    t = np.linalg.solve(A, b)[0]
    return p1 + t * d1


def segments_intersect(p1, p2, p3, p4):
    """
    Check if line segments intersect.
    
    Returns:
        Intersection point if segments intersect, else None.
    """
    def cross(a, b):
        return a[0]*b[1] - a[1]*b[0]

    r = p2 - p1
    s = p4 - p3
    denom = cross(r, s)

    if abs(denom) < 1e-9:
        return None  # Parallel

    t = cross(p3 - p1, s) / denom
    u = cross(p3 - p1, r) / denom

    if 0 <= t <= 1 and 0 <= u <= 1:
        return p1 + t * r

    return None


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
    
    def point_at_distance(self, distance: float) -> Tuple[float, ...]:
        """
        Return a point along the polyline at a specified distance from the start.
        
        Args:
            distance: Distance from the start of the polyline. 
                     If distance > total length, returns the last point.
                     If distance < 0, returns the first point.
        
        Returns:
            A point tuple at the specified distance along the polyline.
        
        Raises:
            ValueError: If the polyline has fewer than 2 points.
        """
        if len(self.points) < 2:
            raise ValueError("Polyline must have at least 2 points")
        
        # Handle boundary cases
        if distance <= 0:
            return self.points[0]
        
        segment_lengths = self.get_segment_lengths()
        total_length = sum(segment_lengths)
        
        if distance >= total_length:
            return self.points[-1]
        
        # Find which segment the distance falls into
        cumulative_distance = 0.0
        for i, seg_length in enumerate(segment_lengths):
            if cumulative_distance + seg_length >= distance:
                # Distance falls in this segment
                remaining_distance = distance - cumulative_distance
                
                # Interpolate between points[i] and points[i+1]
                p1 = self.points[i]
                p2 = self.points[i + 1]
                
                # Calculate the ratio along this segment
                ratio = remaining_distance / seg_length if seg_length > 0 else 0
                
                # Linear interpolation
                interpolated_point = tuple(
                    p1[j] + ratio * (p2[j] - p1[j]) for j in range(len(p1))
                )
                return interpolated_point
            
            cumulative_distance += seg_length
        
        # Fallback: return last point
        return self.points[-1]
    
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
    
    def compute_segment_angles(self) -> np.ndarray:
        """
        Compute the interior angle at each vertex of the polyline.

        Returns:
            np.ndarray of length N-2: Angle at each interior vertex in **radians**.
            Measured between vectors p1-p0 and p2-p1.
        """
        path = np.asarray(self.points[:2], dtype=float) if self.points[0].__len__() == 2 else \
               np.asarray([p[:2] for p in self.points], dtype=float)
        n = len(path)
        if n < 3:
            return np.array([])

        angles = []

        for i in range(1, n-1):
            p0, p1, p2 = path[i-1], path[i], path[i+1]

            v1 = p0 - p1
            v2 = p2 - p1

            # Normalize vectors
            v1_norm = v1 / (np.linalg.norm(v1) + 1e-12)
            v2_norm = v2 / (np.linalg.norm(v2) + 1e-12)

            # Angle between vectors using arccos
            dot = np.clip(np.dot(v1_norm, v2_norm), -1.0, 1.0)
            angle = np.arccos(dot)
            angles.append(angle)

        return np.array(angles)
    
    def compute_curvature_radius(self) -> List[float]:
        """
        Compute the radius of curvature at each interior vertex.

        Returns:
            List of curvature radius values. List has length = len(points) - 2.
        """
        path = np.asarray([p[:2] for p in self.points], dtype=float) if len(self.points[0]) > 2 else \
               np.asarray(self.points, dtype=float)

        curvatures = []
        for i in range(1, len(path) - 1):
            p0, p1, p2 = path[i-1], path[i], path[i+1]

            a = np.linalg.norm(p1 - p0)
            b = np.linalg.norm(p2 - p1)
            c = np.linalg.norm(p2 - p0)

            area = abs(np.cross(p1 - p0, p2 - p0)) / 2

            if area == 0:
                curvatures.append(0)
                continue

            radius = (a * b * c) / (4 * area)
            curvatures.append(1 / radius)

        return curvatures
    
    def compute_total_segment_angles(self) -> float:
        """
        Compute the total absolute angle change across all vertices.

        Returns:
            Sum of absolute angles at all interior vertices.
        """
        angles = self.compute_segment_angles()
        total = 0
        for curve in angles:
            total += abs(curve)
        return total
    
    def offset_polyline(self, offset: float, fix_pinches: bool = True, pinches_neighbor_window: int = 5) -> Tuple['Polyline', 'Polyline']:
        """
        Create offset polylines on both sides.
        
        Args:
            offset: Distance to offset. Positive = left, Negative = right.
            fix_pinches: If True, removes local self-intersections.
        
        Returns:
            Tuple of (left_polyline, right_polyline)
        """
        def offset_single_side(points, offset_dist):
            """Returns a single offset polyline."""
            pts = [np.array(p[:2] if len(p) > 2 else p, dtype=float) for p in points]
            n = len(pts)

            if n < 2:
                raise ValueError("Polyline must contain at least 2 points.")

            offset_segments = []

            for i in range(n - 1):
                p0 = pts[i]
                p1 = pts[i + 1]

                direction = normalize(p1 - p0)
                normal = perpendicular(direction)

                p0_off = p0 + offset_dist * normal
                p1_off = p1 + offset_dist * normal

                offset_segments.append((p0_off, p1_off, direction))

            result = []

            # First endpoint
            result.append(offset_segments[0][0])

            # Interior vertices
            for i in range(1, n - 1):
                pA, _, dA = offset_segments[i - 1]
                pB, _, dB = offset_segments[i]

                intersection = line_intersection(pA, dA, pB, dB)

                if intersection is None:
                    intersection = pB

                result.append(intersection)

            # Last endpoint
            result.append(offset_segments[-1][1])

            return [tuple(p) for p in result]

        left = offset_single_side(self.points, offset)
        right = offset_single_side(self.points, -offset)

        if fix_pinches:
            left = self._remove_local_pinches(left, neighbor_window=pinches_neighbor_window)
            right = self._remove_local_pinches(right, neighbor_window=pinches_neighbor_window)

        return Polyline(left), Polyline(right)
    
    def offset_polyline_variable(self, offsets: List[float], fix_pinches: bool = True) -> 'Polyline':
        """
        Apply per-vertex offsets to the polyline.

        Args:
            offsets: List of offset values, same length as points.
                    Positive = left side, Negative = right side.
            fix_pinches: If True, removes local self-intersections.

        Returns:
            New Polyline with variable offsets applied.
        """
        pts = [np.array(p[:2] if len(p) > 2 else p, dtype=float) for p in self.points]
        offsets = np.asarray(offsets, dtype=float)

        n = len(pts)

        if n < 2:
            raise ValueError("Polyline must contain at least 2 points.")

        if len(offsets) != n:
            raise ValueError("Offsets must match number of polyline points.")

        # Compute offset segments (each segment uses average offset)
        offset_segments = []

        for i in range(n - 1):
            p0 = pts[i]
            p1 = pts[i + 1]

            direction = normalize(p1 - p0)
            normal = perpendicular(direction)

            # Smooth transition: use average offset for segment
            seg_offset = 0.5 * (offsets[i] + offsets[i + 1])

            p0_off = p0 + seg_offset * normal
            p1_off = p1 + seg_offset * normal

            offset_segments.append((p0_off, p1_off, direction))

        result = []

        # First endpoint
        result.append(offset_segments[0][0])

        # Interior vertices
        for i in range(1, n - 1):
            pA, _, dA = offset_segments[i - 1]
            pB, _, dB = offset_segments[i]

            intersection = line_intersection(pA, dA, pB, dB)

            if intersection is None:
                intersection = pB

            result.append(intersection)

        # Last endpoint
        result.append(offset_segments[-1][1])

        if fix_pinches:
            result = self._remove_local_pinches(result)

        return Polyline(result)
    
    @staticmethod
    def _remove_local_pinches(polyline, neighbor_window=5):
        """
        Post-process polyline to remove sharp turn pinches
        without changing number of points.
        """
        pts = [np.array(p[:2] if len(p) > 2 else p, dtype=float) for p in polyline]
        n = len(pts)

        for i in range(n - 1):
            a1 = pts[i]
            a2 = pts[i + 1]

            # Check limited neighborhood only
            for j in range(max(i + 2, 0), min(i + neighbor_window, n - 1)):

                # Skip adjacent segments
                if abs(i - j) <= 1:
                    continue

                b1 = pts[j]
                b2 = pts[j + 1]

                intersection = segments_intersect(a1, a2, b1, b2)

                if intersection is not None:
                    # Snap both segment endpoints to intersection
                    pts[i + 1] = intersection
                    pts[j] = intersection

        return [tuple(p) for p in pts]
    
    def vertex_distances(self, other: 'Polyline') -> np.ndarray:
        """
        Compute per-vertex Euclidean distances to another polyline.

        Args:
            other: Another Polyline object.

        Returns:
            np.ndarray of shape (N,) with distances at each vertex.
        """
        p1 = np.asarray([p[:2] if len(p) > 2 else p for p in self.points], dtype=float)
        p2 = np.asarray([p[:2] if len(p) > 2 else p for p in other.points], dtype=float)

        if p1.shape != p2.shape:
            raise ValueError("Polylines must have the same shape.")

        if p1.ndim != 2 or p1.shape[1] != 2:
            raise ValueError("Polylines must be shape (N, 2).")

        # Vectorized difference
        diff = p2 - p1

        # Euclidean norm per row
        distances = np.linalg.norm(diff, axis=1)

        return distances
    
    @staticmethod
    def interpolate_between_polylines(left_polyline: 'Polyline', 
                                      right_polyline: 'Polyline', 
                                      offsets: List[float]) -> 'Polyline':
        """
        Construct a new polyline between two boundary polylines
        using per-vertex offsets in range [-1, 1].

        Args:
            left_polyline: Left boundary polyline.
            right_polyline: Right boundary polyline.
            offsets: Per-vertex offsets in range [-1.0, 1.0].
                    -1.0 = right_polyline, 1.0 = left_polyline.

        Returns:
            New interpolated Polyline.
        """
        left = np.asarray([p[:2] if len(p) > 2 else p for p in left_polyline.points], dtype=float)
        right = np.asarray([p[:2] if len(p) > 2 else p for p in right_polyline.points], dtype=float)
        offsets = np.asarray(offsets, dtype=float)

        if left.shape != right.shape:
            raise ValueError("Polylines must have same shape.")

        if offsets.shape[0] != left.shape[0]:
            raise ValueError("Offsets must match number of vertices.")

        # Convert [-1,1] → [0,1]
        t = (offsets + 1.0) * 0.5

        # Ensure correct shape for broadcasting
        t = t[:, np.newaxis]

        # Linear interpolation
        interpolated = left + t * (right - left)
        interpolated_points = [tuple(p) for p in interpolated]
        
        return Polyline(interpolated_points)
    
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

