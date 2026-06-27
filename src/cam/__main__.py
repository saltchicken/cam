import argparse
import math
import os
import re
import sys

import dearpygui.dearpygui as dpg

# Global tracking variables
current_pos = [0.0, 0.0, 0.0]  # X, Y, Z
toolpaths = []  # Stores tuples: (start_pt, end_pt, is_rapid)
current_step = 0  # Tracks how many lines to draw


def parse_gcode(file_path):
    global current_pos
    toolpaths.clear()

    with open(file_path, 'r') as f:
        current_g = "G0"

        for line in f:
            line = line.strip().upper()
            line = line.split(';')[0].split('(')[0].strip()
            
            if not line:
                continue

            if "G0" in line:
                current_g = "G0"
            if "G1" in line:
                current_g = "G1"
            if "G2" in line or "G3" in line:
                current_g = "G1"

            x_match = re.search(r'X\s*([-+]?\d*\.\d+|\d+)', line)
            y_match = re.search(r'Y\s*([-+]?\d*\.\d+|\d+)', line)
            z_match = re.search(r'Z\s*([-+]?\d*\.\d+|\d+)', line)

            if not (x_match or y_match or z_match):
                continue

            start_pt = list(current_pos)
            if x_match:
                current_pos[0] = float(x_match.group(1))
            if y_match:
                current_pos[1] = float(y_match.group(1))
            if z_match:
                current_pos[2] = float(z_match.group(1))
            end_pt = list(current_pos)

            is_rapid = (current_g == "G0")
            toolpaths.append((start_pt, end_pt, is_rapid))


def project_iso(x, y, z, scale=4.0, offset_x=300, offset_y=600):
    """Converts 3D CNC coordinates into 2D screen pixels"""
    angle = math.radians(30)
    screen_x = (x - y) * math.cos(angle) * scale + offset_x
    screen_y = offset_y - (x + y) * math.sin(angle) * scale - (z * scale)
    return [screen_x, screen_y]


# --- UI Callbacks and Drawing Logic ---


def update_canvas():
    """Clears the drawlist and redraws paths up to current_step"""
    # Clear existing lines from the drawlist
    dpg.delete_item("drawlist", children_only=True)

    # Redraw everything up to the current step
    max_idx = min(current_step, len(toolpaths))
    for i in range(max_idx):
        start, end, is_rapid = toolpaths[i]
        p1 = project_iso(start[0], start[1], start[2])
        p2 = project_iso(end[0], end[1], end[2])

        if is_rapid:
            # Rapid moves
            dpg.draw_line(p1,
                          p2,
                          color=[255, 140, 0, 200],
                          thickness=1,
                          parent="drawlist")
        else:
            # Cutting moves
            dpg.draw_line(p1,
                          p2,
                          color=[0, 255, 255, 255],
                          thickness=2,
                          parent="drawlist")


def next_step():
    global current_step
    if current_step < len(toolpaths):
        current_step += 1
        dpg.set_value("step_slider", current_step)
        update_canvas()


def prev_step():
    global current_step
    if current_step > 0:
        current_step -= 1
        dpg.set_value("step_slider", current_step)
        update_canvas()


def slider_changed(sender, app_data):
    global current_step
    current_step = app_data
    update_canvas()


def main():
    global current_step

    # --- Command Line Arguments ---
    parser = argparse.ArgumentParser(description="Visualize CNC G-Code in 3D.")
    parser.add_argument("filepath",
                        help="Path to the .nc G-Code file to visualize")
    args = parser.parse_args()

    if not os.path.exists(args.filepath):
        print(f"Error: The file '{args.filepath}' could not be found.")
        sys.exit(1)

    # Parse the file provided via command line
    parse_gcode(args.filepath)

    # Set the initial step to 0 (empty canvas)
    current_step = 0

    # Initialize DearPyGui
    dpg.create_context()
    dpg.create_viewport(title="cam",
                        width=1024,
                        height=768)

    # --- UI Setup ---
    with dpg.window(label="3D Viewport",
                    width=1024,
                    height=768,
                    no_move=True,
                    no_close=True):

        # 1. Control Panel
        with dpg.group(horizontal=True):
            dpg.add_button(label="< Prev", callback=prev_step)
            dpg.add_button(label="Next >", callback=next_step)
            dpg.add_slider_int(label="Step",
                               tag="step_slider",
                               min_value=0,
                               max_value=len(toolpaths),
                               default_value=current_step,
                               callback=slider_changed,
                               width=300)

        dpg.add_separator()

        # 2. Canvas
        # We tag the drawlist so we can easily target it to clear and redraw children
        with dpg.drawlist(width=1024, height=700, tag="drawlist"):
            pass

    # Run the initial draw to set the starting state
    update_canvas()

    # Finish Viewport Configuration
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()


if __name__ == "__main__":
    main()
