import math
import re

import dearpygui.dearpygui as dpg

# Initialize DearPyGui
dpg.create_context()
dpg.create_viewport(title='Custom G-Code Visualizer', width=1024, height=768)

# Global tracking variables for parsing
current_pos = [0.0, 0.0, 0.0]  # X, Y, Z
toolpaths = []  # Stores tuples: (start_pt, end_pt, is_rapid)


def parse_gcode(file_path):
    global current_pos
    toolpaths.clear()

    with open(file_path, 'r') as f:
        current_g = "G0"

        for line in f:
            line = line.strip().upper()
            if not line or line.startswith('(') or line.startswith(';'):
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


# --- Mathematical 3D Isometric Projection ---
def project_iso(x, y, z, scale=4.0, offset_x=300, offset_y=600):
    """Converts 3D CNC coordinates into 2D screen pixels"""
    angle = math.radians(30)
    # Calculate isometric X and Y
    screen_x = (x - y) * math.cos(angle) * scale + offset_x
    screen_y = (x + y) * math.sin(angle) * scale - (z * scale)

    # Invert Y because computer screens draw top-to-bottom
    return [screen_x, offset_y - screen_y]


# --- Generate a dummy file ---
with open("test_square.nc", "w") as test_file:
    test_file.write(
        "G0 Z5.0\nG0 X0 Y0\nG1 Z-2.0 F300\nG1 X50.0 Y0.0 F1000\nG1 X50.0 Y50.0\nG1 X0.0 Y50.0\nG1 X0.0 Y0.0\nG0 Z5.0\nG0 X0 Y0\n"
    )

# Run the parser on our test file
parse_gcode("test_square.nc")

# --- UI Setup and 3D Drawing ---
with dpg.window(label="3D Viewport",
                width=1024,
                height=768,
                no_move=True,
                no_close=True):

    # Modern DearPyGui uses 'drawlist' instead of 'drawlayer'
    with dpg.drawlist(width=1024, height=768):

        # Render the toolpaths
        for start, end, is_rapid in toolpaths:
            # Convert the 3D start and end points into flat 2D screen coordinates
            p1 = project_iso(start[0], start[1], start[2])
            p2 = project_iso(end[0], end[1], end[2])

            if is_rapid:
                # Render rapids as an orange line
                dpg.draw_line(p1, p2, color=[255, 140, 0, 200], thickness=1)
            else:
                # Render cuts as a solid cyan line
                dpg.draw_line(p1, p2, color=[0, 255, 255, 255], thickness=2)

# Finish Viewport Configuration
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
