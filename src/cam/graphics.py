"""Math and rendering utilities."""

import numpy as np

def create_heightmap(size_x, size_y, resolution=1.0):
    """Generates 2D arrays for X, Y, and Z heightmap."""
    nx = int(np.ceil(size_x / resolution)) + 1
    ny = int(np.ceil(size_y / resolution)) + 1
    x = np.linspace(0, size_x, nx)
    y = np.linspace(0, size_y, ny)
    z = np.zeros((nx, ny), dtype=np.float32)
    return x, y, z

def carve_toolpaths(z_map, x_coords, y_coords, toolpaths, max_idx, tool_radius=2.0):
    """Updates the Z heightmap based on the toolpaths up to max_idx."""
    z_map.fill(0.0)
    if max_idx == 0:
        return

    for i in range(max_idx):
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
