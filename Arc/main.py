import sys
import matplotlib
import numpy as np
import pyqtgraph as pg
from PyQt6 import QtWidgets
from gui import make_menu, make_central_widgets
from path_finder import generate_path_from_skeleton, compute_segment_lengths, compute_curvature
from path_processor import process_image

class Arc:
    def __init__(self, image_path):
        self.segment_mode = "curvature"  # or "arc_length" or "solid"
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
        self.path_epsilon_slider.setValue(0)
        self.view_path_action.setChecked(False)
        self.toggle_path_visibility(False)
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

    def set_path_epsilon(self, new_value):
        new_epsilon = (new_value / 10.0 + 1.0) ** 2
        self.path = generate_path_from_skeleton(self.filtered, epsilon=new_epsilon)
        self.path_epsilon_label.setText(f'{new_epsilon:.2f}')
        self.draw_path_segments()
        self.toggle_path_visibility(True)
        self.view_path_action.setChecked(True)
        

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
    
    def draw_path_segments(self):
        if not hasattr(self, "path") or self.path is None:
            return

        

        path_y = self.stages[0].shape[0] - self.path[:, 1]
        path_x = self.path[:, 0]

        # Remove previous items
        if hasattr(self, "path_curve"):
            self.view.removeItem(self.path_curve)

        if hasattr(self, "segment_items"):
            for item in self.segment_items:
                self.view.removeItem(item)

        self.segment_items = []

        # ---- SOLID MODE (FAST PATH) ----
        if self.segment_mode == "solid":
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
        if self.segment_mode == "curvature":
            values = compute_curvature(self.path)
            # append last segment value same as previous to match segment count
            if len(values) > 0:
                values = np.append(values, values[-1])
            else:
                values = np.zeros(len(path_x) - 1)
            values = values.max() - values  # invert curvature so high curvature = high value
        else:
            lengths = compute_segment_lengths(self.path)
            if self.segment_mode == "arc_length_from_start":
                values = np.cumsum(lengths)
            elif self.segment_mode == "arc_length":
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

    def run(self):
        sys.exit(self.app.exec())


if __name__ == "__main__":
    arc = Arc("../pathfinder_2026.png")
    arc.run()