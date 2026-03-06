import struct
import numpy as np

# Added 3 floats at the end → fff
FORMAT = "<Iff40HQfffff"
SIZE = struct.calcsize(FORMAT)
NUM_SENSORS = 40


class TelemetryPacket:
    def __init__(
        self,
        ticks_since_idle,
        velocity,
        steering,
        ir_raw,
        ir_processed,
        line_error,
        pid_output,
        distance,
        approx_x,
        approx_y
    ):
        self.ticks_since_idle = ticks_since_idle
        self.velocity = velocity          # m/s
        self.steering = steering          # degrees
        self.ir_raw = ir_raw              # uint16[40]
        self.ir_processed = ir_processed  # uint8[40]
        self.line_error = line_error
        self.pid_output = pid_output
        self.distance = distance          # meters
        self.approx_x = approx_x          # meters
        self.approx_y = approx_y          # meters

    def __repr__(self):
        return (
            f"TelemetryPacket("
            f"ticks={self.ticks_since_idle}, "
            f"vel={self.velocity:.3f}, "
            f"steer={self.steering:.3f}, "
            f"line_err={self.line_error:.3f}, "
            f"pid={self.pid_output:.3f}, "
            f"dist={self.distance:.3f}, "
            f"x={self.approx_x:.3f}, "
            f"y={self.approx_y:.3f})"
        )


def read_packet(serial_obj):
    data = serial_obj.read_packet(SIZE)

    if data is None:
        return None

    unpacked = struct.unpack(FORMAT, data)

    ticks_since_idle = unpacked[0]
    velocity = unpacked[1]
    steering = unpacked[2]

    # 40 uint16 values
    ir_raw = np.array(unpacked[3:43], dtype=np.uint16)

    packed_ir_processed = unpacked[43]

    line_error = unpacked[44]
    pid_output = unpacked[45]

    # New fields
    distance = unpacked[46]
    approx_x = unpacked[47]
    approx_y = unpacked[48]

    # Unpack 64-bit bitfield into 40 sensor bits
    ir_processed = np.array([
        (packed_ir_processed >> i) & 1
        for i in range(NUM_SENSORS)
    ], dtype=np.uint8)

    return TelemetryPacket(
        ticks_since_idle,
        velocity,
        steering,
        ir_raw,
        ir_processed,
        line_error,
        pid_output,
        distance,
        approx_x,
        approx_y
    )