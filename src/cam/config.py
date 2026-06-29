"""Application configuration settings."""
import json
import os
from dataclasses import dataclass, asdict

CONFIG_FILE = "cam_config.json"

@dataclass
class AppConfig:
    view_scale: float = 4.0
    view_offset_x: float = 960.0
    view_offset_y: float = 540.0
    view_rot_x: float = 60.0
    view_rot_y: float = 0.0
    view_rot_z: float = 45.0

    # Adjusted default size for better layout handling
    window_width: int = 1280
    window_height: int = 720
    window_title: str = "cam"

    def save(self) -> None:
        """Saves current configuration to a JSON file."""
        with open(CONFIG_FILE, 'w', encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=4)

    @classmethod
    def load(cls) -> "AppConfig":
        """Loads configuration from JSON, discarding unknown keys."""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding="utf-8") as f:
                    data = json.load(f)
                    valid_keys = cls.__dataclass_fields__.keys()
                    filtered_data = {k: v for k, v in data.items() if k in valid_keys}
                    return cls(**filtered_data)
            except json.JSONDecodeError:
                print("Warning: Corrupted config file. Loading defaults.")
        return cls()
