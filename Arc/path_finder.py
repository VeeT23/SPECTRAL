import cv2
import numpy as np



def compute_segment_lengths(path):
    if len(path) < 2:
        return []

    lengths = []

    for i in range(len(path) - 1):
        v = path[i + 1] - path[i]
        lengths.append(np.linalg.norm(v))

    return np.array(lengths)

def get_total_lengths(polyline):
    total = 0
    lengths = compute_segment_lengths(polyline)
    for length in lengths:
        total += length
    return total

def compute_curvature(path):
    path = np.asarray(path, dtype=float)

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

def compute_segment_angles(path):
    """
    Compute the interior angle at each vertex of a polyline.

    Parameters
    ----------
    path : array-like (N,2)

    Returns
    -------
    angles : np.ndarray of length N-2
        Angle at each interior vertex in **radians**.
        Measured between vectors p1-p0 and p2-p1.
    """

    path = np.asarray(path, dtype=float)
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

def normalize(v):
    norm = np.linalg.norm(v)
    if norm == 0:
        return v
    return v / norm

def perpendicular(v):
    # 90° CCW rotation (left normal)
    return np.array([-v[1], v[0]])

def line_intersection(p1, d1, p2, d2):
    """
    Solve p1 + t*d1 = p2 + u*d2
    Returns intersection point or None if parallel.
    """
    A = np.array([d1, -d2]).T
    b = p2 - p1

    det = np.linalg.det(A)
    if abs(det) < 1e-9:
        return None  # Parallel lines

    t = np.linalg.solve(A, b)[0]
    return p1 + t * d1

def offset_single_side(polyline, offset):
    """
    Returns a single offset polyline (left if offset > 0,
    right if offset < 0)
    """
    pts = [np.array(p, dtype=float) for p in polyline]
    n = len(pts)

    if n < 2:
        raise ValueError("Polyline must contain at least 2 points.")

    # Compute offset segments
    offset_segments = []

    for i in range(n - 1):
        p0 = pts[i]
        p1 = pts[i + 1]

        direction = normalize(p1 - p0)
        normal = perpendicular(direction)

        p0_off = p0 + offset * normal
        p1_off = p1 + offset * normal

        offset_segments.append((p0_off, p1_off, direction))

    result = []

    # ---- First endpoint ----
    result.append(offset_segments[0][0])

    # ---- Interior vertices ----
    for i in range(1, n - 1):
        pA, _, dA = offset_segments[i - 1]
        pB, _, dB = offset_segments[i]

        intersection = line_intersection(pA, dA, pB, dB)

        if intersection is None:
            # Parallel fallback
            intersection = pB

        result.append(intersection)

    # ---- Last endpoint ----
    result.append(offset_segments[-1][1])

    return [tuple(p) for p in result]

def offset_polyline(polyline, offset):
    """
    Given a polyline and offset distance,
    returns two polylines offset in opposite directions.

    API preserved as requested.

    Parameters
    ----------
    polyline : list[(x, y)]
    offset : float

    Returns
    -------
    left_polyline, right_polyline
    """

    left = offset_single_side(polyline, offset)
    right = offset_single_side(polyline, -offset)

    return left, right

def segments_intersect(p1, p2, p3, p4):
    """
    Returns intersection point if segments intersect, else None.
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

def remove_local_pinches(polyline, neighbor_window=5):
    """
    Post-process polyline to remove sharp turn pinches
    without changing number of points.
    """

    pts = [np.array(p, dtype=float) for p in polyline]
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

def compute_total_segment_angles(polyline):
    angles = compute_segment_angles(polyline)
    total = 0
    for curve in angles:
        total += abs(curve)
    return total

def interpolate_between_polylines(left_polyline, right_polyline, offsets):
    """
    Construct a new polyline between two boundary polylines
    using per-vertex offsets in range [-1, 1].

    Parameters
    ----------
    left_polyline : array-like (N,2)
    right_polyline : array-like (N,2)
    offsets : array-like (N,) values in [-1.0, 1.0]

    Returns
    -------
    np.ndarray (N,2)
    """

    left = np.asarray(left_polyline, dtype=float)
    right = np.asarray(right_polyline, dtype=float)
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
    return left + t * (right - left)

def vertex_distances(polyline1, polyline2):
    """
    Compute per-vertex Euclidean distances between two polylines.

    Parameters
    ----------
    polyline1 : array-like (N,2)
    polyline2 : array-like (N,2)

    Returns
    -------
    distances : np.ndarray shape (N,)
    """

    p1 = np.asarray(polyline1, dtype=float)
    p2 = np.asarray(polyline2, dtype=float)

    if p1.shape != p2.shape:
        raise ValueError("Polylines must have the same shape.")

    if p1.ndim != 2 or p1.shape[1] != 2:
        raise ValueError("Polylines must be shape (N, 2).")

    # Vectorized difference
    diff = p2 - p1

    # Euclidean norm per row
    distances = np.linalg.norm(diff, axis=1)

    return distances

def offset_polyline_variable(polyline, offsets, fix_pinches=True):
    """
    Apply per-vertex offsets to a polyline.

    Parameters
    ----------
    polyline : list[(x, y)] or Nx2 array
    offsets : list[float]
        Same length as polyline.
        Positive = left side, Negative = right side.
    fix_pinches : bool
        If True, removes local self-intersections.

    Returns
    -------
    list[(x, y)]  # variable-offset polyline
    """

    pts = [np.array(p, dtype=float) for p in polyline]
    offsets = np.asarray(offsets, dtype=float)

    n = len(pts)

    if n < 2:
        raise ValueError("Polyline must contain at least 2 points.")

    if len(offsets) != n:
        raise ValueError("Offsets must match number of polyline points.")

    # ---- Compute offset segments (each segment uses average offset) ----
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

    # ---- First endpoint ----
    result.append(offset_segments[0][0])

    # ---- Interior vertices ----
    for i in range(1, n - 1):
        pA, _, dA = offset_segments[i - 1]
        pB, _, dB = offset_segments[i]

        intersection = line_intersection(pA, dA, pB, dB)

        if intersection is None:
            # Fallback for near-parallel segments
            intersection = pB

        result.append(intersection)

    # ---- Last endpoint ----
    result.append(offset_segments[-1][1])

    if fix_pinches:
        result = remove_local_pinches(result)

    return result