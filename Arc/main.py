import sys
import matplotlib
import numpy as np
import pyqtgraph as pg
import random
from PyQt6 import QtWidgets, QtCore
from gui import make_menu, make_central_widgets
from path_finder import generate_path_from_skeleton, compute_segment_lengths, compute_curvature, offset_polyline, remove_local_pinches, compute_total_segment_angles, vertex_distances,interpolate_between_polylines
from path_processor import process_image


class Arc:
    def __init__(self, image_path):
        self.segment_mode = "None"
        self.stages = []
        self.stage_index = 0

        self.app = QtWidgets.QApplication(sys.argv)

        # Main window
        self.win = QtWidgets.QMainWindow()
        self.win.setWindowTitle("Arc")
        self.win.resize(900, 700)

        # Create central widgets
        make_central_widgets(self)

        # Create menu
        make_menu(self)

        

        # Image processing
        process_image(self, image_path)

        self.update_display()

        self.path = generate_path_from_skeleton(self.filtered, epsilon=1.0)
        self.set_path_epsilon(1)
        self.toggle_path_visibility(False)

        self.draw_path_boundaries()
        self.toggle_boundaries_visibility(self.boundary_toggle_action.isChecked())
        self.win.show()

    # ---------------- UI ----------------
    def set_stage(self, index):
        print(f"Setting stage to index: {index}")
        self.stage_index = index
        self.current_stage_label.setText(self.view_map_menu.actions()[index].text())
        self.update_display()
        self.update_menu_checked_state(index)

    def update_menu_checked_state(self, index):
        actions = self.map_group.actions()
        if 0 <= index < len(actions):
            actions[index].setChecked(True)

    def commit_path_epsilon(self):
        value = self.path_epsilon_spin.value()
        self.set_path_epsilon(value)

    def set_path_epsilon(self, new_value):
        self.path = generate_path_from_skeleton(self.filtered, epsilon=new_value)
        self.draw_path_boundaries()
        if self.segment_mode == "None":
            self.segment_mode = "Solid"
        self.draw_path_segments()
        self.toggle_path_visibility(True)
    
    def clear_path_segments(self):
        if hasattr(self, "path_curve"):
            try:
                scene = self.path_curve.scene()
            except Exception:
                scene = None
            if scene is not None and scene == self.view.scene():
                self.view.removeItem(self.path_curve)

        if hasattr(self, "segment_items"):
            for item in self.segment_items:
                try:
                    scene = item.scene()
                except Exception:
                    scene = None
                if scene is not None and scene == self.view.scene():
                    self.view.removeItem(item)

    def clear_path_boundaries(self):
        if hasattr(self, "left_boundary"):
            try:
                scene = self.left_boundary.scene()
            except Exception:
                scene = None
            if scene is not None and scene == self.view.scene():
                self.view.removeItem(self.left_boundary)

        if hasattr(self, "right_boundary"):
            try:
                scene = self.right_boundary.scene()
            except Exception:
                scene = None
            if scene is not None and scene == self.view.scene():
                self.view.removeItem(self.right_boundary)
        
        if hasattr(self, "boundary_connectors"):
            try:
                scene = self.boundary_connectors.scene()
            except Exception:
                scene = None
            if scene is not None and scene == self.view.scene():
                self.view.removeItem(self.boundary_connectors)

    def update_display(self):
        if self.stage_index == 0:
            self.img_item.setImage(np.zeros((10, 10), dtype=np.uint8))
            return
        img = self.stages[self.stage_index - 1]
        img = np.flipud(img)

        if img.ndim == 2:
            self.img_item.setImage(img.T)
        else:
            self.img_item.setImage(img.transpose(1, 0, 2))

    def set_segment_mode(self, mode):
        print(f"Setting segment mode to: {mode}")
        self.segment_mode = mode
        if mode == "None":
            self.toggle_path_visibility(False)
        else:
            self.draw_path_segments()
            self.toggle_path_visibility(True)
           
    def draw_path_segments(self):
        if not hasattr(self, "path") or self.path is None:
            return
        path_y = self.stages[0].shape[0] - self.path[:, 1]
        path_x = self.path[:, 0]

        # Remove previous items
        self.clear_path_segments()

        self.segment_items = []

        # ---- SOLID MODE (FAST PATH) ----
        if self.segment_mode == "Solid":
            self.path_curve = pg.PlotDataItem(
                path_x,
                path_y,
                pen=pg.mkPen('r', width=3),
                connect="all",
                symbol=None
            )
            self.view.addItem(self.path_curve)
            return

        # ---- GRADIENT MODES ----
        if self.segment_mode == "Curvature":
            values = compute_curvature(self.path)
            # append last segment value same as previous to match segment count
            if len(values) > 0:
                values = np.append(values, values[-1])
            else:
                values = np.zeros(len(path_x) - 1)
            values = values.max() - values  # invert curvature so high curvature = high value
        else:
            lengths = compute_segment_lengths(self.path)
            if self.segment_mode == "Length From Start":
                values = np.cumsum(lengths)
            elif self.segment_mode == "Arc Length":
                values = lengths
            else:
                values = lengths  # fallback

        # Normalize values
        vmin = values.min()
        vmax = values.max()
        if vmax - vmin < 1e-8:
            vmax = vmin + 1e-8

        cmap = matplotlib.colormaps["plasma"]

        for i in range(len(path_x) - 1):
            norm = (values[i] - vmin) / (vmax - vmin)
            norm = np.clip(norm, 0, 1)

            rgba = cmap(norm)  # returns (r,g,b,a)
            color = pg.mkColor(int(rgba[0]*255), int(rgba[1]*255), int(rgba[2]*255))

            seg = pg.PlotDataItem(
                [path_x[i], path_x[i+1]],
                [path_y[i], path_y[i+1]],
                pen=pg.mkPen(color, width=3),
                connect="all",
                symbol=None
            )
            self.view.addItem(seg)
            self.segment_items.append(seg)

    def toggle_path_visibility(self, checked):
        print(f"Toggle path visibility: {checked}")
        
        if hasattr(self, "path_curve"):
            self.path_curve.setVisible(checked)
        if hasattr(self, "segment_items"):
            for item in self.segment_items:
                item.setVisible(checked)

    def toggle_boundaries_visibility(self, checked):
        print(f"Toggle boundaries visibility: {checked}")
        
        if hasattr(self, "left_boundary"):
            self.left_boundary.setVisible(checked)
        if hasattr(self, "right_boundary"):
            self.right_boundary.setVisible(checked)
        if hasattr(self, "boundary_connectors"):
            self.boundary_connectors.setVisible(checked)

    def draw_path_boundaries(self):

        if not hasattr(self, "path") or self.path is None:
            return

        self.clear_path_boundaries()

        left, right = offset_polyline(self.path, offset=20.0)

        left = remove_local_pinches(left, neighbor_window=8)
        right = remove_local_pinches(right, neighbor_window=8)

        self.left_boundary_polyline = [
            (p[0], self.stages[0].shape[0] - p[1]) for p in left
        ]
        self.right_boundary_polyline = [
            (p[0], self.stages[0].shape[0] - p[1]) for p in right
        ]

        # ---- Boundary Lines ----
        self.left_boundary = pg.PlotDataItem(
            [p[0] for p in self.left_boundary_polyline],
            [p[1] for p in self.left_boundary_polyline],
            pen=pg.mkPen('g', width=2, style=QtCore.Qt.PenStyle.DashLine),
            connect="all"
        )

        self.right_boundary = pg.PlotDataItem(
            [p[0] for p in self.right_boundary_polyline],
            [p[1] for p in self.right_boundary_polyline],
            pen=pg.mkPen('g', width=2, style=QtCore.Qt.PenStyle.DashLine),
            connect="all"
        )

        self.view.addItem(self.left_boundary)
        self.view.addItem(self.right_boundary)

        # ---- Connector Lines Between Boundaries ----
        connector_x = []
        connector_y = []

        for i in range(len(self.left_boundary_polyline)):
            lx, ly = self.left_boundary_polyline[i]
            rx, ry = self.right_boundary_polyline[i]

            connector_x.extend([lx, rx])
            connector_y.extend([ly, ry])

        self.boundary_connectors = pg.PlotDataItem(
            connector_x,
            connector_y,
            pen=pg.mkPen('c', width=2, style=QtCore.Qt.PenStyle.DotLine),
            connect="pairs"
        )

        self.view.addItem(self.boundary_connectors)
        self.toggle_boundaries_visibility(self.boundary_toggle_action.isChecked())
        
    def tick_simulation_loop(self):

        if not hasattr(self, "race_line_polyline"):
            # Initialize race line as midpoint via interpolation between boundaries
            self.boundary_mid_polyline = interpolate_between_polylines(
                self.left_boundary_polyline,
                self.right_boundary_polyline,
                np.zeros(len(self.left_boundary_polyline))
            )
            self.race_line_polyline = np.array(self.boundary_mid_polyline.copy())
            self.race_line_offsets = np.zeros(len(self.race_line_polyline))
            self.track_widths = vertex_distances(
                self.left_boundary_polyline,
                self.right_boundary_polyline
            )

        # Work with a numpy array for numeric stability
        offsets = np.asarray(self.race_line_offsets, dtype=float).copy()

        # Small mutation: avoid mutating endpoints to prevent end-cap distortions
        if len(offsets) > 2:
            idx = random.randint(1, len(offsets) - 2)
        else:
            idx = random.randint(0, len(offsets) - 1)

        offsets[idx] += (random.random() - 0.5) * 0.2
        offsets[idx] = np.clip(offsets[idx], -1.0, 1.0)

        candidate_race_line = interpolate_between_polylines(
            self.left_boundary_polyline,
            self.right_boundary_polyline,
            offsets
        )

        candidate_race_line = np.asarray(candidate_race_line, dtype=float)

        total_curvature = compute_total_segment_angles(self.race_line_polyline)
        candidate_curvature = compute_total_segment_angles(candidate_race_line)

        if candidate_curvature > total_curvature:
            self.race_line_polyline = candidate_race_line
            self.race_line_offsets = np.asarray(offsets, dtype=float)
            self.draw_race_line()

    def toggle_simulation(self):
        if not hasattr(self, "sim_timer"):
            self.sim_timer = QtCore.QTimer(self.win)
            self.sim_timer.timeout.connect(self.tick_simulation_loop)
            self.sim_timer.setInterval(0) 

        if self.sim_timer.isActive():
            self.sim_timer.stop()
            try:
                self.toggle_sim_btn.setText("Start Loop")
                self.toggle_sim_btn.setChecked(False)
            except Exception:
                pass
        else:
            self.sim_timer.start()
            try:
                self.toggle_sim_btn.setText("Stop Loop")
                self.toggle_sim_btn.setChecked(True)
            except Exception:
                pass

    def draw_race_line(self):
        
        if hasattr(self, "race_line"):
            try:
                scene = self.race_line.scene()
            except Exception:
                scene = None
            if scene is not None and scene == self.view.scene():
                self.view.removeItem(self.race_line)

       

        self.race_line = pg.PlotDataItem(
            [p[0] for p in self.race_line_polyline],
            [p[1] for p in self.race_line_polyline],
            pen=pg.mkPen('g', width=3),
            connect="all"
        )

        self.view.addItem(self.race_line)

    def run(self):
        sys.exit(self.app.exec())

if __name__ == "__main__":
    arc = Arc("../pathfinder_2026.png")
    arc.run()