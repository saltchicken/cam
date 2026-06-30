import numpy as np
from abc import ABC, abstractmethod
from typing import Tuple, Any

class MachineProfile(ABC):
    """Abstract profile defining look and rendering behavior for a machine."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def stock_color(self) -> Tuple[float, float, float, float]:
        """Base substrate color (RGBA)."""
        pass

    @property
    @abstractmethod
    def skirt_color(self) -> Tuple[float, float, float, float]:
        """Sides/envelope bounding color (RGBA)."""
        pass

    @property
    @abstractmethod
    def cut_line_color(self) -> str:
        """Color signature for cut segments."""
        pass

    @abstractmethod
    def update_heightmap(self, state: Any, max_idx: int) -> None:
        """Executes machine-specific material simulation logic."""
        pass


class MillProfile(MachineProfile):
    @property
    def name(self) -> str:
        return "MILL"

    @property
    def stock_color(self) -> Tuple[float, float, float, float]:
        return (0.8, 0.8, 0.2, 1.0)  # Polyurethane block yellow

    @property
    def skirt_color(self) -> Tuple[float, float, float, float]:
        return (0.7, 0.7, 0.15, 1.0)

    @property
    def cut_line_color(self) -> str:
        return 'cyan'

    def update_heightmap(self, state: Any, max_idx: int) -> None:
        from cam.graphics import carve_toolpaths, generate_heightmap_colors

        # Milling changes the physical structure of the substrate
        if max_idx < state.last_carved_idx:
            state.heightmap_z[:] = state.base_z_map[:]
            carve_toolpaths(
                state.heightmap_z, state.heightmap_x, state.heightmap_y,
                state.toolpaths, 0, max_idx, state.tool_diameter
            )
        else:
            carve_toolpaths(
                state.heightmap_z, state.heightmap_x, state.heightmap_y,
                state.toolpaths, state.last_carved_idx, max_idx, state.tool_diameter
            )


class LaserProfile(MachineProfile):
    @property
    def name(self) -> str:
        return "LASER"

    @property
    def stock_color(self) -> Tuple[float, float, float, float]:
        return (0.15, 0.15, 0.15, 1.0)  # Dark honeycomb bed

    @property
    def skirt_color(self) -> Tuple[float, float, float, float]:
        return (0.2, 0.2, 0.2, 1.0)

    @property
    def cut_line_color(self) -> str:
        return '#ff3366'  # High-visibility burn track

    def update_heightmap(self, state: Any, max_idx: int) -> None:
        # Push laser substrate down slightly below Z=0.0 line trace threshold
        state.heightmap_z[:] = state.base_z_map[:] - 0.1


class PenProfile(MachineProfile):
    @property
    def name(self) -> str:
        return "PEN"

    @property
    def stock_color(self) -> Tuple[float, float, float, float]:
        return (0.95, 0.95, 0.95, 1.0)  # White drawing sheet

    @property
    def skirt_color(self) -> Tuple[float, float, float, float]:
        return (0.85, 0.85, 0.85, 1.0)

    @property
    def cut_line_color(self) -> str:
        return '#0066cc'  # Deep ink blue track

    def update_heightmap(self, state: Any, max_idx: int) -> None:
        # Push paper substrate down slightly below Z=-1.0 line trace threshold
        state.heightmap_z[:] = state.base_z_map[:] - 1.1
