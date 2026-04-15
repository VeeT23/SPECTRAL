import json
from datetime import datetime
from pathlib import Path
from spectral.io.packet import TelemetryPacket


class TelemetryPacketDatabase:
    SESSION_FOLDER = Path("session")
    
    def __init__(self):
        self.packets = {}
        self.prev_tick = None
        self.current_file = None
        self._ensure_session_folder()
    
    @staticmethod
    def _ensure_session_folder():
        """Ensure the session folder exists."""
        Path(TelemetryPacketDatabase.SESSION_FOLDER).mkdir(exist_ok=True)
    
    def _create_new_file(self):
        """Create a new file for the current run with timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"run_{timestamp}.jsonl"
        self.current_file = self.SESSION_FOLDER / filename
        # Create empty file
        self.current_file.touch()
        return self.current_file
    
    def _packet_to_json(self, packet):
        """Convert packet to JSON-serializable dict."""
        return {
            'ticks_since_idle': packet.ticks_since_idle,
            'velocity': packet.velocity,
            'steering': packet.steering,
            'ir_raw': packet.ir_raw.tolist() if hasattr(packet.ir_raw, 'tolist') else packet.ir_raw,
            'ir_processed': packet.ir_processed.tolist() if hasattr(packet.ir_processed, 'tolist') else packet.ir_processed,
            'line_error': packet.line_error,
            'pid_output': packet.pid_output,
            'distance': packet.distance,
            'approx_x': packet.approx_x,
            'approx_y': packet.approx_y,
        }
    
    def _json_to_packet(self, json_dict):
        """Convert JSON dict back to packet."""
        import numpy as np
        packet = TelemetryPacket(
            ticks_since_idle=json_dict['ticks_since_idle'],
            velocity=json_dict['velocity'],
            steering=json_dict['steering'],
            ir_raw=np.array(json_dict['ir_raw'], dtype=np.uint16),
            ir_processed=np.array(json_dict['ir_processed'], dtype=np.uint8),
            line_error=json_dict['line_error'],
            pid_output=json_dict['pid_output'],
            distance=json_dict['distance'],
            approx_x=json_dict['approx_x'],
            approx_y=json_dict['approx_y'],
        )
        return packet
    
    def _find_insertion_point(self, packet_ticks):
        """
        Find the line number where packet should be inserted.
        Returns the line number (0-indexed) where packet should go.
        """
        if not self.current_file or not self.current_file.exists():
            return 0
        
        lines = self.current_file.read_text().strip().split('\n')
        if not lines or lines[0] == '':
            return 0
        
        # Search backwards to find insertion point
        for i in range(len(lines) - 1, -1, -1):
            try:
                json_obj = json.loads(lines[i])
                if json_obj['ticks_since_idle'] < packet_ticks:
                    return i + 1
            except (json.JSONDecodeError, KeyError):
                continue
        
        return 0
    
    def _append_packet_to_file(self, packet):
        """Append packet to the current file in sorted order."""
        if self.current_file is None:
            self._create_new_file()
        
        json_line = json.dumps(self._packet_to_json(packet))
        
        # Read current file
        if self.current_file.exists():
            content = self.current_file.read_text().strip()
            lines = content.split('\n') if content else []
        else:
            lines = []
        
        # Find insertion point
        insertion_point = self._find_insertion_point(packet.ticks_since_idle)
        
        # Insert packet at correct position
        lines.insert(insertion_point, json_line)
        
        # Write back to file
        self.current_file.write_text('\n'.join(lines) + '\n' if lines else '')
    
    def add_packet(self, packet):
        """
        Add a packet to the database.
        Returns True if this is a new run (reset occurred), False otherwise.
        """
        is_new_run = False
        
        # Check if this is a new run by comparing ticks
        if self.prev_tick is not None and packet.ticks_since_idle < self.prev_tick:
            # New run detected, create new file and reset packets
            self._create_new_file()
            self.packets = {}
            is_new_run = True
        
        self.prev_tick = packet.ticks_since_idle
        self.packets[packet.ticks_since_idle] = packet
        
        # Append to file
        self._append_packet_to_file(packet)
        
        return is_new_run
    
    def get_all_packets(self):
        """Return all packets sorted by tick."""
        ticks = sorted(self.packets.keys())
        return [self.packets[t] for t in ticks]
    
    def get_packets_dict(self):
        """Return the packets dictionary."""
        return self.packets
    
    def get_most_recent_packet(self):
        """Return the most recent packet, or None if no packets."""
        ticks = sorted(self.packets.keys())
        if len(ticks) == 0:
            return None
        return self.packets[ticks[-1]]
    
    def clear(self):
        """Clear all packets."""
        self.packets = {}
        self.prev_tick = None
    
    def load(self, filepath):
        """
        Load packets from a file.
        
        Args:
            filepath: Path to the .jsonl file to load
        """
        self.clear()
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        try:
            lines = filepath.read_text().strip().split('\n')
            for line in lines:
                if line.strip():
                    json_obj = json.loads(line)
                    packet = self._json_to_packet(json_obj)
                    self.packets[packet.ticks_since_idle] = packet
                    self.prev_tick = packet.ticks_since_idle
        except (json.JSONDecodeError, KeyError) as e:
            raise ValueError(f"Error parsing file {filepath}: {e}")
