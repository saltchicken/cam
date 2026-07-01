import argparse
import os
import sys

from cam.config import AppConfig
from cam.gui import run_gui
from cam.parser import parse_gcode
from cam.graphics import create_heightmap
from cam.state import AppState
from cam.profiles import MillProfile, LaserProfile, PenProfile


def main():
    parser = argparse.ArgumentParser(description="Visualize CNC G-Code in 3D.")
    parser.add_argument("filepath", help="Path to the .nc G-Code file to visualize")
    parser.add_argument("--tool-dia", type=float, default=5.0, help="Fallback tool diameter (mm) if missing from file metadata")
    # Add the new mode argument with choices
    parser.add_argument("--mode", type=str, choices=['mill', 'laser', 'pen'], default='mill', help="Machine visualization mode")
    args = parser.parse_args()

    if not os.path.exists(args.filepath):
        print(f"Error: The file '{args.filepath}' could not be found.")
        sys.exit(1)

    # 1. Parse Data (removed parsed_mode from the return signature)
    gcode_lines, toolpaths, parsed_dia = parse_gcode(args.filepath)
    final_dia = parsed_dia if parsed_dia is not None else args.tool_dia
    
    # 2. Select Machine Profile Strategy using the CLI argument
    normalized_mode = args.mode.upper()
    if normalized_mode == 'LASER':
        profile = LaserProfile()
    elif normalized_mode == 'PEN':
        profile = PenProfile()
    else:
        profile = MillProfile()

    # 3. Initialize Architecture
    config = AppConfig.load()
    state = AppState(
        gcode_lines=gcode_lines, 
        toolpaths=toolpaths,
        tool_diameter=final_dia,
        profile=profile
    )

    # 4. Generate Initial Stock Heightmap
    x, y, z = create_heightmap(state.stock_size_x, state.stock_size_y, resolution=state.stock_resolution)
    state.heightmap_x = x
    state.heightmap_y = y
    state.heightmap_z = z
    state.base_z_map = z.copy()

    # 5. Launch Frontend
    run_gui(config, state)


if __name__ == "__main__":
    main()
