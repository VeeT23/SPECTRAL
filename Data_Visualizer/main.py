from gui import TelemetryDashboard
from packet import read_packet
from myserial import ESP32Serial
import numpy as np
import pyqtgraph as pg
from PIL import Image

esp = ESP32Serial()
dashboard = TelemetryDashboard()

# ---------------- MAP ----------------
map_widget = dashboard.add_map("Course Map", row=0, col=1, rowspan=2, colspan=2, width=244, height=244)

img = Image.open("pathfinder_2026.png").convert("L").rotate(270, expand=True)
img = np.array(img)

map_widget.set_background(img)
# ---------------- LINE GRAPHS ----------------
line_dist = dashboard.add_line("Distance (m)", row=0, col=0)
line_steer = dashboard.add_line("Steering (deg)", row=1, col=0)
line_control = dashboard.add_line(
    "Control Metrics", 
    curve_names=["Line Error", "PID Output"], 
    pens=[pg.mkPen('r'), pg.mkPen('b')],
    row=2, col=0
)

# ---------------- HEATMAPS ----------------
heat_raw = dashboard.add_heatmap("IR Raw", levels=(0,4096), row=2, col=1)
heat_proc = dashboard.add_heatmap("IR Processed", levels=(0,1), row=2, col=2)

# ---------------- LABEL ----------------
dashboard.add_label_row()

# ---------------- DATA STORAGE ----------------
packets = {}
prev_tick = None

# ---------------- UPDATE LOOP ----------------
def update():
    global prev_tick

    packet = read_packet(esp)
    if packet is None:
        return

    # Robot reset detection
    if prev_tick is not None and packet.ticks_since_idle < prev_tick:
        packets.clear()

    prev_tick = packet.ticks_since_idle
    packets[packet.ticks_since_idle] = packet
    ticks = sorted(packets.keys())

    # ---------------- MAP ----------------
    # Example: display robot position and path
    # Replace these with real coordinates
    robot_pos = [(packets[t].approx_x * 100, packets[t].approx_y * 100 + 225) for t in ticks[-1:]]
    path = [[(packets[t].approx_x, packets[t].approx_y + 0.5) for t in ticks[-5:]]]  # example path
    map_widget.update(line_coords=path, dot_coords=robot_pos)

    # ---------------- HEATMAPS ----------------
    heat_raw.update(np.array([packets[t].ir_raw for t in ticks]))
    heat_proc.update(np.array([packets[t].ir_processed for t in ticks]))

    # ---------------- LINE GRAPHS ----------------
    line_control.update(ticks, [
        [packets[t].line_error for t in ticks],
        [packets[t].pid_output for t in ticks]
    ])
    line_steer.update(ticks, [packets[t].steering for t in ticks])
    line_dist.update(ticks, [packets[t].distance for t in ticks])

    # ---------------- LABEL ----------------
    last = packets[ticks[-1]]
    dashboard.update_label(
        f"Err: {last.line_error:.3f} | "
        f"PID: {last.pid_output:.3f} | "
        f"Steer: {last.steering:.2f}° | "
        f"Dist: {last.distance:.2f} m | "
        f"Ticks: {last.ticks_since_idle}"
    )

# ---------------- TIMER ----------------
timer = pg.QtCore.QTimer()
timer.timeout.connect(update)
timer.start(5)

dashboard.start()