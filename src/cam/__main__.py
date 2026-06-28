import argparse
import os
import sys

from cam.config import AppConfig
from cam.gui import run_gui
from cam.parser import parse_gcode
from cam.graphics import generate_stock
from cam.state import AppState


def main():
    parser = argparse.ArgumentParser(description="Visualize CNC G-Code in 3D.")
    parser.add_argument("filepath", help="Path to the .nc G-Code file to visualize")
    args = parser.parse_args()

    if not os.path.exists(args.filepath):
        print(f"Error: The file '{args.filepath}' could not be found.")
        sys.exit(1)

    # 1. Parse Data
    gcode_lines, toolpaths = parse_gcode(args.filepath)
    
    # 2. Auto-generate Built-in Stock
    stock_verts, stock_faces = generate_stock(toolpaths)

    # 3. Initialize Architecture
    config = AppConfig()
    state = AppState(
        gcode_lines=gcode_lines, 
        toolpaths=toolpaths,
        stock_vertices=stock_verts,
        stock_faces=stock_faces
    )

    # 4. Launch Frontend
    run_gui(config, state)


if __name__ == "__main__":
    main()
