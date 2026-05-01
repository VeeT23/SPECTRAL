import struct
import numpy as np

# Packet format:
# I: uint32_t ticks_since_idle
# f: float velocity
# f: float relative_heading
# 40H: uint16_t ir_raw[40]
# Q: uint64_t packed_ir_processed
# fff: float line_error, float pid_output, float distance
FORMAT = "<Iff40HQfff"
SIZE = struct.calcsize(FORMAT)
NUM_SENSORS = 40


class TelemetryPacket:
    def __init__(
        self,
        ticks_since_idle,
        velocity,
        relative_heading,
        ir_raw,
        ir_processed,
        line_error,
        pid_output,
        distance
    ):
        self.ticks_since_idle = ticks_since_idle
        self.velocity = velocity          # m/s
        self.relative_heading = relative_heading          # degrees
        self.ir_raw = ir_raw              # uint16[40]
        self.ir_processed = ir_processed  # uint8[40]
        self.line_error = line_error
        self.pid_output = pid_output
        self.distance = distance          # meters

    def __repr__(self):
        return (
            f"TelemetryPacket("
            f"ticks={self.ticks_since_idle}, "
            f"vel={self.velocity:.3f}, "
            f"heading={self.relative_heading:.3f}, "
            f"line_err={self.line_error:.3f}, "
            f"pid={self.pid_output:.3f}, "
            f"dist={self.distance:.3f})"
        )


def read_packet(serial_obj) -> TelemetryPacket | None:
    data = serial_obj.read_packet(SIZE)

    if data is None:
        return None

    unpacked = struct.unpack(FORMAT, data)

    ticks_since_idle = unpacked[0]
    velocity = unpacked[1]
    relative_heading = unpacked[2]

    # 40 uint16 values
    ir_raw = np.array(unpacked[3:43], dtype=np.uint16)

    packed_ir_processed = unpacked[43]

    line_error = unpacked[44]
    pid_output = unpacked[45]

    # New fields
    distance = unpacked[46]

    # Unpack 64-bit bitfield into 40 sensor bits
    ir_processed = np.array([
        (packed_ir_processed >> i) & 1
        for i in range(NUM_SENSORS)
    ], dtype=np.uint8)

    return TelemetryPacket(
        ticks_since_idle,
        velocity,
        relative_heading,
        ir_raw,
        ir_processed,
        line_error,
        pid_output,
        distance
    )