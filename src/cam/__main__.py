import argparse
import os
import sys

from cam.config import AppConfig
from cam.gui import run_gui
from cam.parser import parse_gcode
from cam.graphics import create_heightmap
from cam.state import AppState


def main():
    parser = argparse.ArgumentParser(description="Visualize CNC G-Code in 3D.")
    parser.add_argument("filepath", help="Path to the .nc G-Code file to visualize")
    parser.add_argument("--tool-dia", type=float, default=5.0, help="Fallback tool diameter (mm) if missing from file metadata")
    args = parser.parse_args()

    if not os.path.exists(args.filepath):
        print(f"Error: The file '{args.filepath}' could not be found.")
        sys.exit(1)

    # 1. Parse Data
    gcode_lines, toolpaths, parsed_dia, parsed_mode = parse_gcode(args.filepath)
    
    # Resolve the hybrid logic: Meta tag takes priority, CLI arg is the fallback
    final_dia = parsed_dia if parsed_dia is not None else args.tool_dia
    
    # 2. Initialize Architecture
    config = AppConfig.load()
    state = AppState(
        gcode_lines=gcode_lines, 
        toolpaths=toolpaths,
        tool_diameter=final_dia,
        mode=parsed_mode
    )

    # 3. Generate Initial Stock Heightmap
    x, y, z = create_heightmap(state.stock_size_x, state.stock_size_y, resolution=state.stock_resolution)
    state.heightmap_x = x
    state.heightmap_y = y
    state.heightmap_z = z
    state.base_z_map = z.copy() # Cache the flat board

    # 4. Launch Frontend
    run_gui(config, state)


if __name__ == "__main__":
    main()
