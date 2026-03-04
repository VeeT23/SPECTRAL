import cv2
import numpy as np
from skimage.morphology import skeletonize
from path_finder import generate_path_from_skeleton
from collections import deque
# ---------------- Image Pipeline ----------------

def prune_to_longest_path(skeleton):
    """
    Keeps only the longest geodesic path (graph diameter)
    inside the skeleton component.
    """

    ys, xs = np.where(skeleton > 0)
    pixels = set(zip(xs, ys))

    if not pixels:
        return skeleton

    # 8-connectivity
    neighbors8 = [
        (-1, -1), (-1, 0), (-1, 1),
        ( 0, -1),           ( 0, 1),
        ( 1, -1), ( 1, 0), ( 1, 1),
    ]

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

def process_image(self, path):
    original = cv2.imread(path)
    if original is None:
        raise FileNotFoundError(path)

    rotations = {
        0: None,
        90: cv2.ROTATE_90_CLOCKWISE,
        180: cv2.ROTATE_180,
        270: cv2.ROTATE_90_COUNTERCLOCKWISE,
    }

    best_score = -1
    best_result = None
    best_rotation = 0

    # ---- Try all rotations ----
    for angle, rot_flag in rotations.items():

        if rot_flag is not None:
            rotated = cv2.rotate(original, rot_flag)
        else:
            rotated = original.copy()

        gray = cv2.cvtColor(rotated, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)

        binary = thresh == 0
        skeleton = skeletonize(binary)
        skeleton = (skeleton * 255).astype(np.uint8)

        largest = keep_largest_component(skeleton)
        filtered = prune_to_longest_path(largest)

        score = len(generate_path_from_skeleton(filtered))
        print(f"Rotation {angle}: score={score}")
        if score > best_score:
            best_score = score
            best_result = (rotated, gray, thresh, skeleton, largest, filtered)
            best_rotation = angle

    print(f"Best rotation: {best_rotation}°  (score={best_score})")

    # ---- Store best pipeline ----
    self.stages.clear()

    original_best, gray_best, thresh_best, skeleton_best, largest_best, filtered_best = best_result

    original_rgb = cv2.cvtColor(original_best, cv2.COLOR_BGR2RGB)
    self.stages.append(original_rgb)
    self.stages.append(gray_best)
    self.stages.append(thresh_best)
    self.stages.append(skeleton_best)
    self.stages.append(largest_best)
    self.filtered = filtered_best
    self.stages.append(self.filtered)

    self.stage_slider.setMaximum(len(self.stages))
    self.stage_slider.setValue(1)
