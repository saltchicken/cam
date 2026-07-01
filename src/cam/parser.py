"""
Robust state-machine-based G-Code parser and interpreter.
Handles tokenization, modal state tracking, and geometry linearization.
"""
import math
import re
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional, Iterator


@dataclass
class MachineState:
    """Tracks the modal state and position of the CNC machine."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    i: float = 0.0
    j: float = 0.0
    
    feed_rate: float = 0.0
    spindle_speed: int = 0
    
    is_absolute: bool = True
    unit_multiplier: float = 1.0  # 1.0 for mm, 25.4 for inches
    motion_mode: str = "G0"
    tool_is_on: bool = False


@dataclass
class TokenizedLine:
    """Represents a single parsed line of G-Code."""
    line_number: int
    raw_text: str
    words: Dict[str, float]
    metadata: Dict[str, str] = field(default_factory=dict)


class GCodeTokenizer:
    """Strips comments and tokenizes raw strings into G-Code words."""
    
    # Matches letter followed by optional spaces and a number (e.g., 'X -10.5', 'G01')
    WORD_PATTERN = re.compile(r'([A-Z])\s*([-+]?\d*\.?\d+)')
    META_PATTERN = re.compile(r'\(META:\s*([A-Z_]+)=([^\)]+)\)', re.IGNORECASE)

    @classmethod
    def parse_line(cls, raw_line: str, line_idx: int) -> Optional[TokenizedLine]:
        """Parses a single line into a dictionary of command words."""
        text = raw_line.strip()
        if not text:
            return None

        # 1. Extract Metadata (specific to your gcoder output)
        metadata = {}
        for match in cls.META_PATTERN.finditer(text):
            metadata[match.group(1).upper()] = match.group(2).strip()

        # 2. Strip comments
        # Remove inline parenthesis comments and everything after semicolons
        text_no_comments = re.sub(r'\(.*?\)', '', text)
        text_no_comments = text_no_comments.split(';')[0].strip().upper()

        if not text_no_comments and not metadata:
            return None

        # 3. Tokenize words
        words = {}
        for match in cls.WORD_PATTERN.finditer(text_no_comments):
            letter = match.group(1)
            value = float(match.group(2))
            words[letter] = value

        return TokenizedLine(
            line_number=line_idx,
            raw_text=raw_line,
            words=words,
            metadata=metadata
        )


class GCodeInterpreter:
    """Interprets tokenized G-Code, updates machine state, and emits toolpaths."""
    
    def __init__(self, fallback_dia: float = 5.0):
        self.state = MachineState()
        self.toolpaths = []
        self.gcode_lines = []
        
        self.parsed_dia: Optional[float] = None
        self.parsed_mode: str = "MILL"
        self.fallback_dia = fallback_dia

    def process_file(self, filepath: str) -> Tuple[List[str], List, float, str]:
        """Main entry point to process an entire file."""
        with open(filepath, 'r', encoding="utf-8") as f:
            for idx, raw_line in enumerate(f):
                token = GCodeTokenizer.parse_line(raw_line, idx)
                if token:
                    self.gcode_lines.append(f"{idx + 1}: {raw_line.strip()}")
                    self._update_state_and_emit(token)

        final_dia = self.parsed_dia if self.parsed_dia is not None else self.fallback_dia
        return self.gcode_lines, self.toolpaths, final_dia, self.parsed_mode

    def _update_state_and_emit(self, token: TokenizedLine) -> None:
        """Applies a tokenized line to the machine state and generates movements."""
        
        # Parse Metadata
        if 'TOOL_DIA' in token.metadata:
            self.parsed_dia = float(token.metadata['TOOL_DIA'])
        if 'MODE' in token.metadata:
            self.parsed_mode = token.metadata['MODE']

        words = token.words
        if not words:
            return

        # 1. Update Unit & Positioning Modes (G20/G21, G90/G91)
        if words.get('G') == 20: self.state.unit_multiplier = 25.4
        elif words.get('G') == 21: self.state.unit_multiplier = 1.0
        
        if words.get('G') == 90: self.state.is_absolute = True
        elif words.get('G') == 91: self.state.is_absolute = False

        # 2. Update Tool/Spindle State (M3/M4/M5, S)
        m_code = words.get('M')
        if m_code in (3, 4): self.state.tool_is_on = True
        elif m_code == 5: self.state.tool_is_on = False
        
        if 'S' in words:
            self.state.spindle_speed = int(words['S'])

        # 3. Determine Motion Mode
        g_code = words.get('G')
        if g_code in (0, 1, 2, 3):
            self.state.motion_mode = f"G{int(g_code)}"

        # 4. Calculate Target Coordinates
        has_motion = any(axis in words for axis in ('X', 'Y', 'Z'))
        if not has_motion:
            return

        start_pt = [self.state.x, self.state.y, self.state.z]
        
        for axis, index in (('X', 0), ('Y', 1), ('Z', 2)):
            if axis in words:
                val = words[axis] * self.state.unit_multiplier
                if self.state.is_absolute:
                    setattr(self.state, axis.lower(), val)
                else:
                    setattr(self.state, axis.lower(), start_pt[index] + val)

        end_pt = [self.state.x, self.state.y, self.state.z]
        is_rapid = self.state.motion_mode == "G0"

        # 5. Emit Toolpath Segments
        if self.state.motion_mode in ("G2", "G3"):
            self._emit_arc(start_pt, end_pt, words, token.line_number)
        else:
            self.toolpaths.append((
                start_pt, 
                end_pt, 
                is_rapid, 
                token.line_number, 
                self.state.tool_is_on, 
                self.state.spindle_speed
            ))

    def _emit_arc(self, start_pt: List[float], end_pt: List[float], 
                  words: Dict[str, float], line_num: int) -> None:
        """Linearizes an arc into small line segments for the 3D viewer."""
        i_val = words.get('I', 0.0) * self.state.unit_multiplier
        j_val = words.get('J', 0.0) * self.state.unit_multiplier

        cx = start_pt[0] + i_val
        cy = start_pt[1] + j_val
        r = math.hypot(i_val, j_val)

        if r < 0.0001:
            self.toolpaths.append((start_pt, end_pt, False, line_num, self.state.tool_is_on, self.state.spindle_speed))
            return

        angle_start = math.atan2(start_pt[1] - cy, start_pt[0] - cx)
        angle_end = math.atan2(end_pt[1] - cy, end_pt[0] - cx)

        if self.state.motion_mode == "G3":  # CCW
            if angle_end <= angle_start:
                angle_end += 2 * math.pi
        else:  # CW (G2)
            if angle_end >= angle_start:
                angle_end -= 2 * math.pi

        arc_angle = abs(angle_end - angle_start)
        # 5 degrees per segment provides smooth enough curves for UI
        segments = max(1, int(math.degrees(arc_angle) / 5.0))

        prev_pt = list(start_pt)
        for step in range(1, segments + 1):
            t = step / segments
            cur_angle = angle_start + (angle_end - angle_start) * t

            next_pt = [
                cx + r * math.cos(cur_angle),
                cy + r * math.sin(cur_angle),
                start_pt[2] + (end_pt[2] - start_pt[2]) * t
            ]
            self.toolpaths.append((prev_pt, next_pt, False, line_num, self.state.tool_is_on, self.state.spindle_speed))
            prev_pt = next_pt


def parse_gcode(file_path: str, fallback_dia: float = 5.0):
    """
    Convenience function matching the original API signature of cam/parser.py
    """
    interpreter = GCodeInterpreter(fallback_dia=fallback_dia)
    return interpreter.process_file(file_path)
