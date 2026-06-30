from dataclasses import dataclass, field
from typing import List, Tuple, Any
from cam.profiles import MachineProfile, MillProfile

@dataclass
class AppState:
    gcode_lines: List[str] = field(default_factory=list)
    toolpaths: List[Tuple[List[float], List[float], bool, int]] = field(default_factory=list)
    profile: MachineProfile = field(default_factory=MillProfile) # Replaced mode string with instance
    
    heightmap_x: Any = None
    heightmap_y: Any = None
    heightmap_z: Any = None
    base_z_map: Any = None 

    current_line: int = 0
    last_carved_idx: int = 0 
    
    tool_diameter: float = 5.0
    
    stock_size_x: float = 100.0
    stock_size_y: float = 100.0
    stock_size_z: float = 20.0
    stock_resolution: float = 0.25
