import argparse
import os
import sys

from cam.config import AppConfig
from cam.gui import run_gui
from cam.parser import parse_gcode, parse_obj
from cam.state import AppState

def main():
    parser = argparse.ArgumentParser(description="Visualize CNC G-Code in 3D.")
    parser.add_argument("filepath", help="Path to the .nc G-Code file to visualize")
    parser.add_argument("--stock", help="Path to an optional .obj file representing the stock material", default=None)
    args = parser.parse_args()

    if not os.path.exists(args.filepath):
        print(f"Error: The file '{args.filepath}' could not be found.")
        sys.exit(1)

    # 1. Parse Data
    gcode_lines, toolpaths = parse_gcode(args.filepath)
    
    stock_verts, stock_faces = [], []
    if args.stock and os.path.exists(args.stock):
        stock_verts, stock_faces = parse_obj(args.stock)

    # 2. Initialize Architecture
    config = AppConfig()
    state = AppState(
        gcode_lines=gcode_lines, 
        toolpaths=toolpaths,
        stock_vertices=stock_verts,
        stock_faces=stock_faces
    )

    # 3. Launch Frontend
    run_gui(config, state)

if __name__ == "__main__":
    main()
