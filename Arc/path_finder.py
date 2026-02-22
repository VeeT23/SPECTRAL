import cv2
import numpy as np

def generate_path_from_skeleton(skeleton, epsilon=1.0):
    """
    Generates ordered polyline path from open-loop skeleton.
    Start = left-most white pixel.
    Returns Nx2 numpy array of (x, y) coordinates.

    epsilon: maximum distance in pixels from original to simplified path.
             Larger epsilon → fewer points on straight segments.
    """

    # ---- Extract skeleton pixel coordinates ----
    ys, xs = np.where(skeleton > 0)
    pixels = set(zip(xs, ys))

    if not pixels:
        raise ValueError("No skeleton pixels found")

    # ---- Find start (left-most pixel) ----
    start = min(pixels, key=lambda p: p[0])

    # 8-connectivity
    neighbors8 = [
        (-1, -1), (-1, 0), (-1, 1),
        ( 0, -1),           ( 0, 1),
        ( 1, -1), ( 1, 0), ( 1, 1),
    ]

    # ---- Trace ordered path ----
    path = [start]
    visited = set([start])
    current = start

    while True:
        found_next = False
        for dx, dy in neighbors8:
            nxt = (current[0] + dx, current[1] + dy)
            if nxt in pixels and nxt not in visited:
                path.append(nxt)
                visited.add(nxt)
                current = nxt
                found_next = True
                break
        if not found_next:
            break  # reached end

    ordered = np.array(path, dtype=float)

    # ---- Simplify path using RDP ----
    if len(ordered) < 3:
        return ordered

    # Convert to int for OpenCV
    ordered_int = ordered.astype(np.int32).reshape(-1, 1, 2)
    simplified = cv2.approxPolyDP(ordered_int, epsilon=epsilon, closed=False)
    simplified = simplified.reshape(-1, 2).astype(float)

    return simplified


def compute_segment_lengths(path):
    if len(path) < 2:
        return []

    lengths = []

    for i in range(len(path) - 1):
        v = path[i + 1] - path[i]
        lengths.append(np.linalg.norm(v))

    return np.array(lengths)


def compute_curvature(path):
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

    return np.array(curvatures)