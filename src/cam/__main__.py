"""A 3D CNC G-Code visualizer."""
import argparse
import os
import sys

from cam.config import AppConfig
from cam.gui import run_gui
from cam.parser import parse_gcode
from cam.state import AppState


def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(description="Visualize CNC G-Code in 3D.")
    parser.add_argument("filepath",
                        help="Path to the .nc G-Code file to visualize")
    args = parser.parse_args()

    if not os.path.exists(args.filepath):
        print(f"Error: The file '{args.filepath}' could not be found.")
        sys.exit(1)

    # 1. Parse Data
    gcode_lines, toolpaths = parse_gcode(args.filepath)

    # 2. Initialize Architecture
    config = AppConfig()
    state = AppState(gcode_lines=gcode_lines, toolpaths=toolpaths)

    # 3. Launch Frontend
    run_gui(config, state)


if __name__ == "__main__":
    main()
