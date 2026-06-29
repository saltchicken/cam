"""Math and rendering utilities."""

import numpy as np

def create_heightmap(size_x, size_y, resolution=1.0):
    nx = int(np.ceil(size_x / resolution)) + 1
    ny = int(np.ceil(size_y / resolution)) + 1
    x = np.linspace(0, size_x, nx)
    y = np.linspace(0, size_y, ny)
    z = np.zeros((nx, ny), dtype=np.float32)
    return x, y, z

def carve_toolpaths(z_map, x_coords, y_coords, toolpaths, start_idx, end_idx, tool_diameter=5.0):
    """Updates the Z heightmap iteratively from start_idx to end_idx."""
    if start_idx >= end_idx:
        return

    tool_radius = tool_diameter / 2.0

    for i in range(start_idx, end_idx):
        start, end, is_rapid, _ = toolpaths[i]
        if is_rapid:
            continue

        x1, y1, z1 = start
        x2, y2, z2 = end

        min_x, max_x = min(x1, x2) - tool_radius, max(x1, x2) + tool_radius
        min_y, max_y = min(y1, y2) - tool_radius, max(y1, y2) + tool_radius

        ix_min = max(0, np.searchsorted(x_coords, min_x) - 1)
        ix_max = min(len(x_coords), np.searchsorted(x_coords, max_x) + 1)
        iy_min = max(0, np.searchsorted(y_coords, min_y) - 1)
        iy_max = min(len(y_coords), np.searchsorted(y_coords, max_y) + 1)

        if ix_min >= ix_max or iy_min >= iy_max:
            continue

        X = x_coords[ix_min:ix_max]
        Y = y_coords[iy_min:iy_max]
        XX, YY = np.meshgrid(X, Y, indexing='ij')

        dx = x2 - x1
        dy = y2 - y1
        l2 = dx*dx + dy*dy

        z_sub = z_map[ix_min:ix_max, iy_min:iy_max]

        if l2 == 0:
            dist = np.sqrt((XX - x1)**2 + (YY - y1)**2)
            mask = dist <= tool_radius
            z_sub[mask] = np.minimum(z_sub[mask], z1)
        else:
            t = ((XX - x1) * dx + (YY - y1) * dy) / l2
            t = np.clip(t, 0.0, 1.0)
            px = x1 + t * dx
            py = y1 + t * dy
            pz = z1 + t * (z2 - z1)

            dist = np.sqrt((XX - px)**2 + (YY - py)**2)
            mask = dist <= tool_radius
            z_sub[mask] = np.minimum(z_sub[mask], pz[mask])

def generate_heightmap_colors(z_vals, stock_size_z):
    """Calculates vertex colors entirely in Numpy for better performance."""
    colors = np.full((len(z_vals), 4), [0.8, 0.8, 0.2, 1.0], dtype=np.float32)
    colors[z_vals < -1e-4] = [0.2, 0.8, 0.2, 1.0]
    colors[z_vals < -stock_size_z - 1e-4] = [0.8, 0.2, 0.2, 1.0]
    return colors

def get_skirt_mesh(x, y, z, z_bottom):
    """Generates vertices and faces for the walls and bottom of the stock."""
    nx = len(x)
    ny = len(y)

    vertices = []
    faces = []
    idx = 0

    # Helper to add a strip of walls
    def add_wall(x_coords, y_coords, z_coords):
        nonlocal idx
        n = len(x_coords)
        
        # Top vertices
        for i in range(n):
            vertices.append([x_coords[i], y_coords[i], z_coords[i]])
        # Bottom vertices
        for i in range(n):
            vertices.append([x_coords[i], y_coords[i], z_bottom])

        # Generate triangles
        for i in range(n - 1):
            t1, t2 = idx + i, idx + i + 1
            b1, b2 = idx + n + i, idx + n + i + 1
            faces.append([t1, b1, t2])
            faces.append([t2, b1, b2])

        idx += 2 * n

    # Draw the 4 side walls tracking the edge Z coordinates
    add_wall(np.full(ny, x[0]), y, z[0, :])             # -X Wall
    add_wall(np.full(ny, x[-1]), y[::-1], z[-1, ::-1])  # +X Wall
    add_wall(x[::-1], np.full(nx, y[0]), z[::-1, 0])    # -Y Wall
    add_wall(x, np.full(nx, y[-1]), z[:, -1])           # +Y Wall

    # Add the single bottom face closing the box
    b_idx = idx
    vertices.extend([
        [x[0], y[0], z_bottom],
        [x[-1], y[0], z_bottom],
        [x[-1], y[-1], z_bottom],
        [x[0], y[-1], z_bottom]
    ])
    faces.extend([
        [b_idx, b_idx+2, b_idx+1],
        [b_idx, b_idx+3, b_idx+2]
    ])

    return np.array(vertices, dtype=np.float32), np.array(faces, dtype=np.uint32)
