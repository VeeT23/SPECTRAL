
import pyqtgraph as pg
import numpy as np
from PyQt6 import QtCore
from spectral.data.solution import Solution
from spectral.data.solution import SPoint
from spectral.data.solution import SolutionSpan
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
        self.solution_visual_items = []
        self.current_solution = None
        self._solution_click_connected = False
        self._vertex_match_tolerance = 1e-6
        self.edit_mode = 'points'
        self._pending_span_start_distance = None
        self._pending_span_marker = None
        self._span_click_tolerance = 0.12
       
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

    def set_path_from_polyline(self, polyline: Polyline, color_mode='solid'):
        """Create and draw a colored path directly from a Polyline."""
        if self.path_line is not None:
            self.path_line.erase()

        self.path_line = ColorLine(polyline, parent_plot=self)
        self.path_line.set_color_mode(color_mode)
        self.path_line.hide()  # Start hidden by default
        return self.path_line
        
    def create_boundary_lines(self, width: float):
        if hasattr(self, 'left_boundary_line') and self.left_boundary_line is not None:
            self.left_boundary_line.erase()
        if hasattr(self, 'right_boundary_line') and self.right_boundary_line is not None:
            self.right_boundary_line.erase()

        left_boundary_polyline, right_boundary_polyline = self.path_line.polyline.offset_polyline(offset=(width / 2))

        self.left_boundary_line = ColorLine(left_boundary_polyline, parent_plot=self)
        self.right_boundary_line = ColorLine(right_boundary_polyline, parent_plot=self)

        return self.left_boundary_line, self.right_boundary_line

    def clear_solution_visualization(self):
        """Remove previously drawn solution angle/sweep lines."""
        for item in self.solution_visual_items:
            self.removeItem(item)
        self.solution_visual_items = []

    def _ensure_solution_click_handler(self):
        """Connect scene click signal once for SPoint editing."""
        if self._solution_click_connected:
            return

        scene = self.scene()
        if scene is None:
            return

        scene.sigMouseClicked.connect(self._on_scene_mouse_clicked)
        self._solution_click_connected = True

    @staticmethod
    def _vertex_heading_degrees(points, index: int) -> float:
        """Heading at a vertex (outgoing segment, or incoming at endpoint)."""
        x = float(points[index][0])
        y = float(points[index][1])

        if index < len(points) - 1:
            nx = float(points[index + 1][0])
            ny = float(points[index + 1][1])
            dx = nx - x
            dy = ny - y
        else:
            px = float(points[index - 1][0])
            py = float(points[index - 1][1])
            dx = x - px
            dy = y - py

        if dx == 0.0 and dy == 0.0:
            return 0.0

        return float(np.degrees(np.arctan2(dy, dx)))

    @staticmethod
    def _vertex_distances(points) -> list[float]:
        """Cumulative distance at each polyline vertex."""
        distances = [0.0]
        total = 0.0

        for i in range(1, len(points)):
            px = float(points[i - 1][0])
            py = float(points[i - 1][1])
            x = float(points[i][0])
            y = float(points[i][1])
            total += float(np.hypot(x - px, y - py))
            distances.append(total)

        return distances

    @staticmethod
    def _sort_solution_by_distance(solution: Solution):
        solution.s_points.sort(key=lambda sp: float(sp.distance))

    def _nearest_vertex_index(self, x: float, y: float) -> int | None:
        if self.path_line is None:
            return None

        points = self.path_line.polyline.get_points()
        if not points:
            return None

        distances_sq = [
            (float(p[0]) - x) ** 2 + (float(p[1]) - y) ** 2
            for p in points
        ]
        return int(np.argmin(distances_sq))

    def _find_spoint_at_vertex(self, solution: Solution, x: float, y: float) -> int | None:
        for idx, s_point in enumerate(solution.s_points):
            if (
                abs(float(s_point.x) - x) <= self._vertex_match_tolerance
                and abs(float(s_point.y) - y) <= self._vertex_match_tolerance
            ):
                return idx
        return None

    def _clear_pending_span_selection(self):
        self._pending_span_start_distance = None
        if self._pending_span_marker is not None:
            self.removeItem(self._pending_span_marker)
            self._pending_span_marker = None

    def _set_pending_span_marker(self, x: float, y: float):
        if self._pending_span_marker is None:
            self._pending_span_marker = pg.ScatterPlotItem(pxMode=False)
            self.addItem(self._pending_span_marker)

        self._pending_span_marker.setData(
            x=[x],
            y=[y],
            size=0.045,
            brush=pg.mkBrush(255, 255, 255, 200),
            pen=pg.mkPen(color=(0, 0, 0), width=1),
        )

    def _span_polyline_points(self, start_distance: float, end_distance: float):
        if self.path_line is None:
            return None

        points = self.path_line.polyline.get_points()
        if len(points) < 2:
            return None

        start = float(min(start_distance, end_distance))
        end = float(max(start_distance, end_distance))

        if abs(end - start) <= self._vertex_match_tolerance:
            return None

        vertex_distances = self._vertex_distances(points)
        if len(vertex_distances) == 0:
            return None

        total_distance = float(vertex_distances[-1])
        start = max(0.0, min(start, total_distance))
        end = max(0.0, min(end, total_distance))
        if end <= start:
            return None

        span_points = [self.path_line.polyline.point_at_distance(start)]
        for idx, vertex_distance in enumerate(vertex_distances):
            distance_value = float(vertex_distance)
            if start < distance_value < end:
                span_points.append(points[idx])

        span_points.append(self.path_line.polyline.point_at_distance(end))
        return span_points

    def _draw_solution_span(self, span: SolutionSpan):
        span_points = self._span_polyline_points(
            start_distance=float(span.start_distance),
            end_distance=float(span.end_distance),
        )
        if span_points is None or len(span_points) < 2:
            return

        xs = [float(p[0]) for p in span_points]
        ys = [float(p[1]) for p in span_points]

        span_item = pg.PlotCurveItem(
            xs,
            ys,
            pen=pg.mkPen(color=(0, 200, 255, 190), width=4),
        )
        self.addItem(span_item)
        self.solution_visual_items.append(span_item)

        endpoint_item = pg.ScatterPlotItem(pxMode=False)
        endpoint_item.setData(
            x=[xs[0], xs[-1]],
            y=[ys[0], ys[-1]],
            size=0.03,
            brush=pg.mkBrush(0, 220, 255, 220),
            pen=pg.mkPen(color=(0, 80, 100), width=1),
        )
        self.addItem(endpoint_item)
        self.solution_visual_items.append(endpoint_item)

    def _draw_solution_spans(self, solution: Solution):
        for span in solution.spans:
            self._draw_solution_span(span)

    def _find_span_index_at_distance(self, solution: Solution, distance: float) -> int | None:
        matching = []
        for idx, span in enumerate(solution.spans):
            start = float(min(span.start_distance, span.end_distance))
            end = float(max(span.start_distance, span.end_distance))
            if start <= distance <= end:
                matching.append((end - start, idx))

        if len(matching) == 0:
            return None

        matching.sort(key=lambda item: item[0])
        return int(matching[0][1])

    def _handle_span_left_click(self, click_x: float, click_y: float):
        if self.path_line is None:
            return

        points = self.path_line.polyline.get_points()
        if len(points) < 2:
            return

        vertex_index = self._nearest_vertex_index(click_x, click_y)
        if vertex_index is None:
            return

        vertex_x = float(points[vertex_index][0])
        vertex_y = float(points[vertex_index][1])
        distances = self._vertex_distances(points)
        vertex_distance = float(distances[vertex_index])

        if self.current_solution is None:
            self.current_solution = Solution()

        if self._pending_span_start_distance is None:
            self._pending_span_start_distance = vertex_distance
            self._set_pending_span_marker(vertex_x, vertex_y)
            print(f"[SOLUTION] span start selected at distance={vertex_distance:.4f}")
            return

        start_distance = float(self._pending_span_start_distance)
        self._clear_pending_span_selection()

        added = self.current_solution.add_span(start_distance=start_distance, end_distance=vertex_distance)
        if not added:
            print("[SOLUTION] span not added (duplicate or zero-length)")
            return

        start = min(start_distance, vertex_distance)
        end = max(start_distance, vertex_distance)
        self.visualize_solution(self.current_solution)
        print(f"[SOLUTION] added span start={start:.4f}, end={end:.4f}")

    def _handle_span_right_click(self, click_x: float, click_y: float):
        if self.path_line is None:
            return
        if self.current_solution is None or len(self.current_solution.spans) == 0:
            return

        _, lateral_distance, _, arc_distance = self.path_line.polyline.closest_point_on_line((click_x, click_y))
        if float(lateral_distance) > self._span_click_tolerance:
            return

        span_index = self._find_span_index_at_distance(self.current_solution, float(arc_distance))
        if span_index is None:
            return

        removed_span = self.current_solution.spans.pop(span_index)
        self._clear_pending_span_selection()
        self.visualize_solution(self.current_solution)
        print(
            f"[SOLUTION] deleted span start={float(removed_span.start_distance):.4f}, "
            f"end={float(removed_span.end_distance):.4f}"
        )

    def _on_scene_mouse_clicked(self, event):
        """Toggle SPoint at nearest vertex when map is clicked."""
        if self.path_line is None:
            return

        view_box = self.getViewBox()
        if view_box is None:
            return

        scene_pos = event.scenePos()
        if not view_box.sceneBoundingRect().contains(scene_pos):
            return

        data_pos = view_box.mapSceneToView(scene_pos)
        click_x = float(data_pos.x())
        click_y = float(data_pos.y())

        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            if self.edit_mode == 'points':
                self.toggle_spoint_at_nearest_vertex(click_x, click_y)
                event.accept()
            elif self.edit_mode == 'spans':
                self._handle_span_left_click(click_x, click_y)
                event.accept()
            return

        if event.button() == QtCore.Qt.MouseButton.RightButton and self.edit_mode == 'spans':
            self._handle_span_right_click(click_x, click_y)
            event.accept()

    def set_edit_mode(self, mode: str):
        """Set click-editing mode for map interactions."""
        if mode not in ('points', 'spans'):
            print(f"Ignoring unknown track-map edit mode: {mode}")
            return

        self.edit_mode = mode
        if mode != 'spans':
            self._clear_pending_span_selection()

    def toggle_spoint_at_nearest_vertex(self, click_x: float, click_y: float):
        """Create or delete an SPoint at the nearest path vertex."""
        if self.path_line is None:
            return

        points = self.path_line.polyline.get_points()
        if len(points) < 2:
            return

        vertex_index = self._nearest_vertex_index(click_x, click_y)
        if vertex_index is None:
            return

        vx = float(points[vertex_index][0])
        vy = float(points[vertex_index][1])
        distances = self._vertex_distances(points)
        vertex_distance = float(distances[vertex_index])
        vertex_angle = self._vertex_heading_degrees(points, vertex_index)

        if self.current_solution is None:
            self.current_solution = Solution()

        existing_index = self._find_spoint_at_vertex(self.current_solution, vx, vy)
        if existing_index is not None:
            del self.current_solution.s_points[existing_index]
            action = "deleted"
        else:
            default_sweep = (
                float(self.current_solution.s_points[0].sweep)
                if len(self.current_solution.s_points) > 0
                else 10.0
            )
            self.current_solution.s_points.append(
                SPoint(
                    x=vx,
                    y=vy,
                    distance=vertex_distance,
                    angle=vertex_angle,
                    sweep=default_sweep,
                )
            )
            action = "added"

        self._sort_solution_by_distance(self.current_solution)
        self.visualize_solution(self.current_solution)
        print(f"[SOLUTION] {action} SPoint at vertex index={vertex_index}, distance={vertex_distance:.4f}")

    def visualize_solution(self, solution: Solution, line_length: float = 0.1):
        """
        Draw SPoints as one yellow angle ray and two green sweep boundary rays.

        Args:
            solution: Solution containing SPoints to visualize.
            line_length: Length of each ray in plot units.
        """
        self._ensure_solution_click_handler()

        self.clear_solution_visualization()
        self.current_solution = solution

        if self.current_solution is None:
            self._clear_pending_span_selection()
            return

        self._sort_solution_by_distance(self.current_solution)
        self.current_solution.spans.sort(
            key=lambda span: (float(span.start_distance), float(span.end_distance))
        )
        self._draw_solution_spans(self.current_solution)

        if len(self.current_solution.s_points) == 0:
            return

        for s_point in self.current_solution.s_points:
            x = float(s_point.x)
            y = float(s_point.y)
            center_angle = np.radians(float(s_point.angle))
            half_sweep = np.radians(float(s_point.sweep) / 2.0)

            # Center heading line (yellow)
            x_center = x + line_length * np.cos(center_angle)
            y_center = y + line_length * np.sin(center_angle)
            center_item = pg.PlotCurveItem(
                [x, x_center],
                [y, y_center],
                pen=pg.mkPen(color=(255, 255, 0), width=2)
            )
            self.addItem(center_item)
            self.solution_visual_items.append(center_item)

            # Sweep boundary lines (green)
            left_angle = center_angle + half_sweep
            right_angle = center_angle - half_sweep

            x_left = x + line_length * np.cos(left_angle)
            y_left = y + line_length * np.sin(left_angle)
            left_item = pg.PlotCurveItem(
                [x, x_left],
                [y, y_left],
                pen=pg.mkPen(color=(0, 255, 0), width=2)
            )
            self.addItem(left_item)
            self.solution_visual_items.append(left_item)

            x_right = x + line_length * np.cos(right_angle)
            y_right = y + line_length * np.sin(right_angle)
            right_item = pg.PlotCurveItem(
                [x, x_right],
                [y, y_right],
                pen=pg.mkPen(color=(0, 255, 0), width=2)
            )
            self.addItem(right_item)
            self.solution_visual_items.append(right_item)
    
    def update_robot_position(self, distance_along_path : float, heading_degrees : float = None):
        """
        Update and display the robot position marker along the path with optional heading arrow.
        
        Args:
            distance_along_path: Distance from the start of the path in meters.
            heading_degrees: Heading angle in degrees (0 = positive x direction). Optional.
        """
        x, y = self.path_line.polyline.point_at_distance(distance_along_path)
        
        # Create or update robot position marker
        if not hasattr(self, 'robot_marker'):
            self.robot_marker = pg.ScatterPlotItem(pxMode=False)
            self.addItem(self.robot_marker)
        
        self.robot_marker.setData(x=[x], y=[y], size=0.05, brush=pg.mkBrush('red'), pen=pg.mkPen('black'))
        
        # Create or update heading arrow if heading is provided
        if heading_degrees is not None:
            # Convert heading degrees to radians (0° = +x direction)
            heading_rad = np.radians(heading_degrees)
            
            # Calculate arrow end point (arrow length in plot coordinates)
            arrow_length = 0.1
            x_end = x + arrow_length * np.cos(heading_rad)
            y_end = y + arrow_length * np.sin(heading_rad)
            
            # Create or update heading arrow line
            if not hasattr(self, 'heading_arrow_line'):
                self.heading_arrow_line = pg.PlotCurveItem(pen=pg.mkPen('red', width=2))
                self.addItem(self.heading_arrow_line)
            
            self.heading_arrow_line.setData([x, x_end], [y, y_end])
            
            # Create or update arrow head indicator
            if not hasattr(self, 'heading_arrow_head'):
                self.heading_arrow_head = pg.ScatterPlotItem(pxMode=False)
                self.addItem(self.heading_arrow_head)
            
            self.heading_arrow_head.setData(x=[x_end], y=[y_end], size=0.03, brush=pg.mkBrush('red'), pen=pg.mkPen('red'))

        return (x, y)
    
    def update_highlight_point(self, distance_along_path : float):
        """
        Update and display a highlight point marker along the path.
        
        Args:
            distance_along_path: Distance from the start of the path in meters.
        """
        x, y = self.path_line.polyline.point_at_distance(distance_along_path)
        
        # Create or update highlight point marker
        if not hasattr(self, 'highlight_marker'):
            self.highlight_marker = pg.ScatterPlotItem(pxMode=False)
            self.addItem(self.highlight_marker)
        
        self.highlight_marker.setData(x=[x], y=[y], size=0.05, brush=pg.mkBrush('blue'), pen=pg.mkPen('black'))

        return (x, y)
