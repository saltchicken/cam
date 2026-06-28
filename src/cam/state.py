"""Application state management."""
from dataclasses import dataclass
from dataclasses import field
from typing import List, Tuple


@dataclass
class AppState:
    gcode_lines: List[str] = field(default_factory=list)
    # toolpaths format: (start_pt, end_pt, is_rapid, line_idx)
    toolpaths: List[Tuple[List[float], List[float], bool, int]] = field(default_factory=list)
    
    stock_vertices: List[Tuple[float, float, float]] = field(default_factory=list)
    stock_faces: List[Tuple[int, ...]] = field(default_factory=list)

    current_line: int = 0
