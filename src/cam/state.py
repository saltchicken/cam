"""Application state management."""
from dataclasses import dataclass, field
from typing import List, Tuple, Any

@dataclass
class AppState:
    gcode_lines: List[str] = field(default_factory=list)
    # toolpaths format: (start_pt, end_pt, is_rapid, line_idx)
    toolpaths: List[Tuple[List[float], List[float], bool, int]] = field(default_factory=list)
    mode: str = "MILL"
    
    heightmap_x: Any = None
    heightmap_y: Any = None
    heightmap_z: Any = None
    base_z_map: Any = None  # Cache of the un-cut stock

    current_line: int = 0
    last_carved_idx: int = 0  # Tracks how far we have already calculated
    
    tool_diameter: float = 5.0
    
    stock_size_x: float = 100.0
    stock_size_y: float = 100.0
    stock_size_z: float = 20.0
    stock_resolution: float = 0.25
