import cv2
import numpy as np
from skimage.morphology import skeletonize
from collections import deque
from spectral.geometry.polyline import Polyline
# ---------------- Image Pipeline ----------------


neighbors8 = [
(-1, -1), (-1, 0), (-1, 1),
( 0, -1),           ( 0, 1),
( 1, -1), ( 1, 0), ( 1, 1),
]

def generate_path_from_skeleton(skeleton, position=None, epsilon=1.0):
    """
    Generates ordered polyline path from open-loop skeleton.
    Start = nearest pixel to position if provided, otherwise left-most white pixel.
    Returns a Polyline object representing the simplified path.

    position: (x, y) tuple to seed path from nearest pixel, or None for left-most.
    epsilon: maximum distance in pixels from original to simplified path.
             Larger epsilon → fewer points on straight segments.
    """

    # ---- Extract skeleton pixel coordinates ----
    ys, xs = np.where(skeleton > 0)
    pixels = set(zip(xs, ys))

    if not pixels:
        raise ValueError("No skeleton pixels found")

    # ---- Find start (nearest to position if provided, otherwise left-most pixel) ----
    if position is not None:
        start = min(pixels, key=lambda p: (p[0] - position[0])**2 + (p[1] - position[1])**2)
    else:
        start = min(pixels, key=lambda p: (p[0], p[1]))


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

    # Polyline requires at least two points.
    if len(ordered) < 2:
        raise ValueError("Path has fewer than 2 points")

    polyline = Polyline([tuple(p) for p in ordered])
    simplified = polyline.simplify(epsilon=epsilon)

    return simplified

def prune_to_longest_path(skeleton):
    """
    Keeps only the longest geodesic path (graph diameter)
    inside the skeleton component.
    """

    ys, xs = np.where(skeleton > 0)
    pixels = set(zip(xs, ys))

    if not pixels:
        return skeleton


    # ---- Build adjacency ----
    adjacency = {p: [] for p in pixels}
    for x, y in pixels:
        for dx, dy in neighbors8:
            nxt = (x + dx, y + dy)
            if nxt in pixels:
                adjacency[(x, y)].append(nxt)

    # ---- BFS function ----
    def bfs_farthest(start):
        visited = {start}
        parent = {start: None}
        queue = deque([(start, 0)])

        farthest = start
        max_dist = 0

        while queue:
            node, dist = queue.popleft()

            if dist > max_dist:
                max_dist = dist
                farthest = node

            for nxt in adjacency[node]:
                if nxt not in visited:
                    visited.add(nxt)
                    parent[nxt] = node
                    queue.append((nxt, dist + 1))

        return farthest, parent

    # ---- 1st BFS (arbitrary start) ----
    start = min(pixels, key=lambda p: (p[0], p[1]))
    A, _ = bfs_farthest(start)

    # ---- 2nd BFS (true diameter) ----
    B, parent = bfs_farthest(A)

    # ---- Reconstruct path A -> B ----
    path = []
    current = B
    while current is not None:
        path.append(current)
        current = parent[current]

    path = set(path)

    # ---- Build cleaned skeleton ----
    cleaned = np.zeros_like(skeleton)
    for x, y in path:
        cleaned[y, x] = 255

    return cleaned

def keep_largest_component(skeleton):
    # Convert to binary 0/1
    binary = skeleton > 0

    # Label connected components
    num_labels, labels = cv2.connectedComponents(binary.astype(np.uint8))

    if num_labels <= 1:
        return skeleton  # nothing to filter

    # Count pixels in each label
    counts = np.bincount(labels.flatten())

    # Ignore label 0 (background)
    counts[0] = 0

    # Find largest component
    largest_label = np.argmax(counts)

    # Keep only largest
    filtered = (labels == largest_label).astype(np.uint8) * 255

    return filtered

def process_image(path):
    original = cv2.imread(path)
    if original is None:
        raise FileNotFoundError(path)

    gray = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)

    binary = thresh == 0
    skeleton = skeletonize(binary)
    skeleton = (skeleton * 255).astype(np.uint8)

    filtered = keep_largest_component(skeleton)
    pruned = prune_to_longest_path(filtered)

    original_rgb = cv2.cvtColor(original, cv2.COLOR_BGR2RGB)
    stages = [
        ["Original", original_rgb],
        ["Grayscaled", gray],
        ["Thresh", thresh],
        ["Skeleton", skeleton],
        ["Filtered", filtered],
        ["Final", pruned],
    ]

    return stages
