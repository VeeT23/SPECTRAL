from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import builtins
import json
import math
import struct

from spectral.geometry.polyline import Polyline


@dataclass(frozen=True)
class SPoint:
	x: float
	y: float
	distance: float
	angle: float
	sweep: float


@dataclass(frozen=True)
class SolutionSpan:
	start_distance: float
	end_distance: float
	speed: float = 0.0


class Solution:
	"""Container for track solution points with JSON persistence."""

	SOLUTIONS_DIR = Path("solutions")
	_VERSION = 2
	_EXPORT_POINT_MAGIC = b"SLN1"
	_EXPORT_SPAN_MAGIC = b"SLS1"
	_EXPORT_HEADER_STRUCT = struct.Struct("<4sII")  # magic, version, point_count
	_EXPORT_POINT_STRUCT = struct.Struct("<5f")     # x, y, distance, angle, sweep
	_EXPORT_SPAN_STRUCT = struct.Struct("<3f")      # start_distance, end_distance, speed

	def __init__(self, s_points: list[SPoint] | None = None, spans: list[SolutionSpan] | None = None):
		self.s_points: list[SPoint] = list(s_points) if s_points is not None else []
		self.spans: list[SolutionSpan] = list(spans) if spans is not None else []
		self._sort_spans()

	def __len__(self) -> int:
		return len(self.s_points)

	def add_point(self, x: float, y: float, distance: float, angle: float, sweep: float) -> None:
		self.s_points.append(SPoint(x=x, y=y, distance=distance, angle=angle, sweep=sweep))

	def _sort_spans(self):
		self.spans.sort(key=lambda span: (float(span.start_distance), float(span.end_distance)))

	def add_span(self, start_distance: float, end_distance: float, speed: float = 0.0) -> bool:
		start = float(start_distance)
		end = float(end_distance)
		span_speed = float(speed)

		if math.isclose(start, end, abs_tol=1e-9):
			return False

		if start > end:
			start, end = end, start

		for span in self.spans:
			if (
				math.isclose(float(span.start_distance), start, abs_tol=1e-6)
				and math.isclose(float(span.end_distance), end, abs_tol=1e-6)
			):
				return False

		self.spans.append(SolutionSpan(start_distance=start, end_distance=end, speed=span_speed))
		self._sort_spans()
		return True

	@staticmethod
	def _angle_diff_degrees(a: float, b: float) -> float:
		"""Smallest signed difference between two angles in degrees."""
		diff = (a - b + 180.0) % 360.0 - 180.0
		return diff

	@staticmethod
	def _vertex_heading_degrees(points: list[tuple[float, ...]], index: int) -> float:
		"""Compute heading at a vertex using outgoing segment (or incoming at end)."""
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

		return math.degrees(math.atan2(dy, dx))

	@classmethod
	def from_polyline(cls, polyline: Polyline, threshold: float, range: float) -> Solution:
		"""
		Generate a Solution by traversing polyline vertices.

		Algorithm:
		1. Start from the origin vertex (index 0) as the first SPoint.
		2. Walk vertices while tracking cumulative distance.
		3. Use the last SPoint as the angle reference origin.
		4. If angle drift exceeds `threshold` degrees, place a new SPoint
		   at that vertex with `sweep=range`.
		"""
		points = polyline.get_points()
		if len(points) < 2:
			raise ValueError("Polyline must have at least 2 points")
		if threshold < 0:
			raise ValueError("threshold must be non-negative")

		solution = cls()

		# Start with origin as first SPoint.
		x0, y0 = float(points[0][0]), float(points[0][1])
		initial_angle = cls._vertex_heading_degrees(points, 0)
		solution.add_point(x=x0, y=y0, distance=0.0, angle=initial_angle, sweep=float(range))

		anchor_x = x0
		anchor_y = y0
		reference_angle = initial_angle
		cumulative_distance = 0.0

		for i in builtins.range(1, len(points)):
			px, py = float(points[i - 1][0]), float(points[i - 1][1])
			x, y = float(points[i][0]), float(points[i][1])

			segment_length = math.hypot(x - px, y - py)
			cumulative_distance += segment_length

			current_heading = cls._vertex_heading_degrees(points, i)
			angle_delta = abs(cls._angle_diff_degrees(current_heading, reference_angle))

			if angle_delta > threshold:
				placed_angle = current_heading

				solution.add_point(
					x=x,
					y=y,
					distance=cumulative_distance,
					angle=placed_angle,
					sweep=float(range),
				)
				anchor_x = x
				anchor_y = y
				reference_angle = placed_angle

		angles = [round(s_point.angle, 2) for s_point in solution.s_points]
		print(f"[SOLUTION] threshold={threshold:.2f} deg, sweep_range={float(range):.2f} deg")
		print(f"[SOLUTION] Generated {len(solution.s_points)} SPoints")
		print(f"[SOLUTION] SPoint angles (deg): {angles}")

		return solution

	@classmethod
	def _ensure_json_suffix(cls, name: str) -> str:
		return name if name.lower().endswith(".json") else f"{name}.json"

	@classmethod
	def _resolve_solution_path(cls, name_or_path: str, directory: Path | None = None) -> Path:
		candidate = Path(name_or_path)

		if candidate.suffix:
			return candidate

		base_dir = directory if directory is not None else cls.SOLUTIONS_DIR
		return base_dir / cls._ensure_json_suffix(name_or_path)

	def to_dict(self) -> dict:
		"""Convert this Solution to a JSON-serializable dictionary."""
		return {
			"version": self._VERSION,
			"s_points": [
				{
					"x": float(point.x),
					"y": float(point.y),
					"distance": float(point.distance),
					"angle": float(point.angle),
					"sweep": float(point.sweep),
				}
				for point in self.s_points
			],
			"spans": [
				{
					"start_distance": float(span.start_distance),
					"end_distance": float(span.end_distance),
					"speed": float(span.speed),
				}
				for span in self.spans
			],
		}

	@classmethod
	def from_dict(cls, payload: dict) -> Solution:
		"""Create a Solution from a dictionary payload."""
		if "s_points" not in payload:
			raise ValueError("Invalid solution JSON: missing 's_points'")

		points = []
		for p in payload["s_points"]:
			points.append(
				SPoint(
					x=float(p["x"]),
					y=float(p["y"]),
					distance=float(p["distance"]),
					angle=float(p["angle"]),
					sweep=float(p["sweep"]),
				)
			)

		spans = []
		for span in payload.get("spans", []):
			spans.append(
				SolutionSpan(
					start_distance=float(span["start_distance"]),
					end_distance=float(span["end_distance"]),
					speed=float(span.get("speed", 0.0)),
				)
			)

		return cls(points, spans=spans)

	def save(self, name_or_path: str, directory: Path | None = None) -> Path:
		"""Save this solution as JSON data in a .json file."""
		path = self._resolve_solution_path(name_or_path, directory)
		path.parent.mkdir(parents=True, exist_ok=True)

		with path.open("w", encoding="utf-8") as f:
			json.dump(self.to_dict(), f, indent=2)

		return path

	@classmethod
	def load(cls, name_or_path: str, directory: Path | None = None) -> Solution:
		"""Load a solution from a .json file."""
		path = cls._resolve_solution_path(name_or_path, directory)

		with path.open("r", encoding="utf-8") as f:
			payload = json.load(f)

		return cls.from_dict(payload)

	def to_export_bytes(self) -> bytes:
		"""Convert solution to compact binary payload for microcontroller export."""
		data = bytearray()
		data.extend(self._EXPORT_HEADER_STRUCT.pack(self._EXPORT_POINT_MAGIC, self._VERSION, len(self.s_points)))

		for point in self.s_points:
			data.extend(
				self._EXPORT_POINT_STRUCT.pack(
					float(point.x),
					float(point.y),
					float(point.distance),
					float(point.angle),
					float(point.sweep),
				)
			)

		return bytes(data)

	def to_span_export_bytes(self) -> bytes:
		"""Convert solution spans to compact binary payload for microcontroller export."""
		data = bytearray()
		data.extend(self._EXPORT_HEADER_STRUCT.pack(self._EXPORT_SPAN_MAGIC, self._VERSION, len(self.spans)))

		for span in self.spans:
			data.extend(
				self._EXPORT_SPAN_STRUCT.pack(
					float(span.start_distance),
					float(span.end_distance),
					float(span.speed),
				)
			)

		return bytes(data)

	@staticmethod
	def _format_cpp_byte_array(raw: bytes, array_name: str, bytes_per_line: int) -> list[str]:
		hex_bytes = [f"0x{b:02X}" for b in raw]
		lines = []
		for i in builtins.range(0, len(hex_bytes), bytes_per_line):
			lines.append("    " + ", ".join(hex_bytes[i:i + bytes_per_line]))

		return [
			f"static const uint8_t {array_name}[] = {{",
			",\n".join(lines),
			"};",
			f"static const size_t {array_name}Length = sizeof({array_name});",
		]

	def to_cpp_byte_array(
		self,
		array_name: str = "kSolutionData",
		bytes_per_line: int = 16,
		span_array_name: str = "kSolutionSpanData",
	) -> str:
		"""Return C++-style uint8_t arrays for SPoints and spans."""
		point_lines = self._format_cpp_byte_array(
			raw=self.to_export_bytes(),
			array_name=array_name,
			bytes_per_line=bytes_per_line,
		)
		span_lines = self._format_cpp_byte_array(
			raw=self.to_span_export_bytes(),
			array_name=span_array_name,
			bytes_per_line=bytes_per_line,
		)

		return "\n".join(point_lines + [""] + span_lines)


def generate_solution_from_polyline(polyline: Polyline, threshold: float, range: float) -> Solution:
	"""Convenience wrapper for Solution.from_polyline()."""
	return Solution.from_polyline(polyline=polyline, threshold=threshold, range=range)
