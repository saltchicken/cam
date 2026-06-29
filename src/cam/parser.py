"""G-Code parsing and toolpath generation."""
import math
import re

def parse_gcode(file_path):
    """Parse a G-Code file and extract toolpaths."""
    toolpaths = []
    gcode_lines = []
    current_pos = [0.0, 0.0, 0.0]
    
    current_g = "G0"
    is_absolute = True
    unit_multiplier = 1.0  # Default to mm
    
    parsed_dia = None

    with open(file_path, 'r', encoding="utf-8") as f:
        for line in f:
            raw_line = line.strip()
            
            if parsed_dia is None:
                meta_match = re.search(r'\(META:\s*TOOL_DIA=([\d.]+)\)', raw_line, re.IGNORECASE)
                if meta_match:
                    parsed_dia = float(meta_match.group(1))

            line_clean = raw_line.upper().split(';')[0].split('(')[0].strip()

            if not line_clean:
                continue

            line_idx = len(gcode_lines)
            gcode_lines.append(f"{line_idx + 1}: {raw_line}")

            words = line_clean.split()
            
            # Unit State
            if "G20" in words: unit_multiplier = 25.4
            elif "G21" in words: unit_multiplier = 1.0
            
            # Position State
            if "G90" in words: is_absolute = True
            elif "G91" in words: is_absolute = False

            # Modal Movement State
            for w in words:
                if w in ("G0", "G00"): current_g = "G0"
                elif w in ("G1", "G01"): current_g = "G1"
                elif w in ("G2", "G02"): current_g = "G2"
                elif w in ("G3", "G03"): current_g = "G3"

            x_match = re.search(r'X\s*([-+]?\d*\.\d+|\d+)', line_clean)
            y_match = re.search(r'Y\s*([-+]?\d*\.\d+|\d+)', line_clean)
            z_match = re.search(r'Z\s*([-+]?\d*\.\d+|\d+)', line_clean)
            i_match = re.search(r'I\s*([-+]?\d*\.\d+|\d+)', line_clean)
            j_match = re.search(r'J\s*([-+]?\d*\.\d+|\d+)', line_clean)

            if not (x_match or y_match or z_match):
                continue

            start_pt = list(current_pos)
            
            # Apply Coordinates
            if x_match:
                val = float(x_match.group(1)) * unit_multiplier
                current_pos[0] = val if is_absolute else current_pos[0] + val
            if y_match:
                val = float(y_match.group(1)) * unit_multiplier
                current_pos[1] = val if is_absolute else current_pos[1] + val
            if z_match:
                val = float(z_match.group(1)) * unit_multiplier
                current_pos[2] = val if is_absolute else current_pos[2] + val
                
            end_pt = list(current_pos)
            is_rapid = current_g == "G0"

            if current_g in ("G2", "G3"):
                i_val = (float(i_match.group(1)) * unit_multiplier) if i_match else 0.0
                j_val = (float(j_match.group(1)) * unit_multiplier) if j_match else 0.0

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

    return gcode_lines, toolpaths, parsed_dia
