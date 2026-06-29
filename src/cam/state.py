"""Application state management."""
from dataclasses import dataclass, field
from typing import List, Tuple, Any
import numpy as np


@dataclass
class AppState:
    gcode_lines: List[str] = field(default_factory=list)
    # toolpaths format: (start_pt, end_pt, is_rapid, line_idx)
    toolpaths: List[Tuple[List[float], List[float], bool, int]] = field(default_factory=list)
    
    heightmap_x: Any = None
    heightmap_y: Any = None
    heightmap_z: Any = None

    current_line: int = 0
    
    # Dynamic tool diameter retrieved from metadata or CLI fallback
    tool_diameter: float = 5.0
    
    # Explicit stock dimensions
    stock_size_x: float = 100.0
    stock_size_y: float = 100.0
    stock_size_z: float = 20.0

    # Add a resolution field (Lower = Better detail, but slower performance)
    stock_resolution: float = 0.25
