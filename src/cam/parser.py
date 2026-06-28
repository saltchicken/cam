"""G-Code parsing and toolpath generation."""
import math
import re


def parse_gcode(file_path):
    """Parse a G-Code file and extract toolpaths."""
    toolpaths = []
    gcode_lines = []
    current_pos = [0.0, 0.0, 0.0]
    current_g = "G0"

    with open(file_path, 'r', encoding="utf-8") as f:
        for line in f:
            raw_line = line.strip()
            line_clean = raw_line.upper().split(';')[0].split('(')[0].strip()

            if not line_clean:
                continue

            line_idx = len(gcode_lines)
            gcode_lines.append(f"{line_idx + 1}: {raw_line}")

            if "G0" in line_clean:
                current_g = "G0"
            elif "G1" in line_clean:
                current_g = "G1"
            elif "G2" in line_clean:
                current_g = "G2"
            elif "G3" in line_clean:
                current_g = "G3"

            x_match = re.search(r'X\s*([-+]?\d*\.\d+|\d+)', line_clean)
            y_match = re.search(r'Y\s*([-+]?\d*\.\d+|\d+)', line_clean)
            z_match = re.search(r'Z\s*([-+]?\d*\.\d+|\d+)', line_clean)
            i_match = re.search(r'I\s*([-+]?\d*\.\d+|\d+)', line_clean)
            j_match = re.search(r'J\s*([-+]?\d*\.\d+|\d+)', line_clean)

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

            is_rapid = current_g == "G0"

            if current_g in ("G2", "G3"):
                i_val = float(i_match.group(1)) if i_match else 0.0
                j_val = float(j_match.group(1)) if j_match else 0.0

                cx, cy = start_pt[0] + i_val, start_pt[1] + j_val
                r = math.sqrt(i_val**2 + j_val**2)

                if r > 0.0001:
                    angle_start = math.atan2(start_pt[1] - cy, start_pt[0] - cx)
                    angle_end = math.atan2(end_pt[1] - cy, end_pt[0] - cx)

                    if current_g == "G3":  # Counter-clockwise
                        if angle_end <= angle_start:
                            angle_end += 2 * math.pi
                    else:  # Clockwise
                        if angle_end >= angle_start:
                            angle_end -= 2 * math.pi

                    arc_angle = abs(angle_end - angle_start)
                    segments = max(1, int(math.degrees(arc_angle) / 5.0))

                    prev_pt = list(start_pt)
                    for step in range(1, segments + 1):
                        t = step / segments
                        cur_angle = angle_start + (angle_end - angle_start) * t

                        next_pt = [
                            cx + r * math.cos(cur_angle),
                            cy + r * math.sin(cur_angle),
                            start_pt[2] + (end_pt[2] - start_pt[2]) * t
                        ]
                        toolpaths.append((prev_pt, next_pt, False, line_idx))
                        prev_pt = next_pt
                else:
                    toolpaths.append((start_pt, end_pt, False, line_idx))
            else:
                toolpaths.append((start_pt, end_pt, is_rapid, line_idx))

    return gcode_lines, toolpaths
