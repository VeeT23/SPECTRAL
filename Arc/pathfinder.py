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


def compute_relative_angles(path):
    """
    Computes the relative angle (in radians) between each line segment
    and its previous segment in the path.

    Parameters:
        path: Nx2 numpy array of (x, y) coordinates

    Returns:
        angles: list of relative angles in radians
                length = len(path) - 2
                angles[i] is the angle from segment i -> segment i+1
    """

    if len(path) < 3:
        return []

    angles = []

    for i in range(1, len(path) - 1):
        p0 = path[i - 1]
        p1 = path[i]
        p2 = path[i + 1]

        # vector from p0 -> p1
        v1 = p1 - p0
        # vector from p1 -> p2
        v2 = p2 - p1

        # angle between vectors using arctangent (signed)
        angle1 = np.arctan2(v1[1], v1[0])
        angle2 = np.arctan2(v2[1], v2[0])
        # relative angle from v1 to v2
        relative_angle = angle2 - angle1

        # wrap angle to [-pi, pi]
        relative_angle = (relative_angle + np.pi) % (2 * np.pi) - np.pi

        angles.append(relative_angle)

    return angles