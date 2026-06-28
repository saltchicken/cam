"""Application configuration settings."""
from dataclasses import dataclass

@dataclass
class AppConfig:
    view_scale: float = 4.0
    view_offset_x: float = 960.0
    view_offset_y: float = 540.0
    view_rot_x: float = 60.0
    view_rot_y: float = 0.0
    view_rot_z: float = 45.0

    window_width: int = 1920
    window_height: int = 1080
    window_title: str = "cam"
