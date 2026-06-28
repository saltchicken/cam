"""Application configuration settings."""
from dataclasses import dataclass


@dataclass
class AppConfig:
    view_scale: float = 4.0
    view_offset_x: float = 300.0
    view_offset_y: float = 600.0

    window_width: int = 1024
    window_height: int = 768
    window_title: str = "cam"
