"""Math and rendering utilities."""
import math

def project_iso(x, y, z, scale, offset_x, offset_y, rot_x_deg, rot_y_deg, rot_z_deg):
    """Converts 3D CNC coordinates into 2D screen pixels using matrix multiplication."""
    rx = math.radians(rot_x_deg)
    ry = math.radians(rot_y_deg)
    rz = math.radians(rot_z_deg)

    mx = [
        [1, 0, 0],
        [0, math.cos(rx), -math.sin(rx)],
        [0, math.sin(rx), math.cos(rx)]
    ]
    
    my = [
        [math.cos(ry), 0, math.sin(ry)],
        [0, 1, 0],
        [-math.sin(ry), 0, math.cos(ry)]
    ]
    
    mz = [
        [math.cos(rz), -math.sin(rz), 0],
        [math.sin(rz), math.cos(rz), 0],
        [0, 0, 1]
    ]

    def matmul(mat, vec):
        return [
            mat[0][0]*vec[0] + mat[0][1]*vec[1] + mat[0][2]*vec[2],
            mat[1][0]*vec[0] + mat[1][1]*vec[1] + mat[1][2]*vec[2],
            mat[2][0]*vec[0] + mat[2][1]*vec[1] + mat[2][2]*vec[2]
        ]

    p = [x, y, z]

    p = matmul(mz, p)
    p = matmul(mx, p)
    p = matmul(my, p)

    screen_x = p[0] * scale + offset_x
    screen_y = offset_y - p[2] * scale
    
    return [screen_x, screen_y]


def generate_stock(size_x, size_y, size_z):
    """Generates a 3D stock bounding box based on explicit dimensions."""
    
    # Assuming origin (0,0) is bottom-left and Z=0 is the top of the stock.
    min_x, min_y = 0.0, 0.0
    max_x, max_y = size_x, size_y
    min_z = -size_z
    max_z = 0.0

    # Define the 8 vertices of the rectangular prism
    vertices = [
        (min_x, min_y, min_z),  # 0: Bottom-front-left
        (max_x, min_y, min_z),  # 1: Bottom-front-right
        (max_x, max_y, min_z),  # 2: Bottom-back-right
        (min_x, max_y, min_z),  # 3: Bottom-back-left
        (min_x, min_y, max_z),  # 4: Top-front-left
        (max_x, min_y, max_z),  # 5: Top-front-right
        (max_x, max_y, max_z),  # 6: Top-back-right
        (min_x, max_y, max_z),  # 7: Top-back-left
    ]

    # Define the 6 faces (quads) connecting the vertices
    faces = [
        (0, 1, 2, 3),  # Bottom
        (4, 5, 6, 7),  # Top
        (0, 1, 5, 4),  # Front
        (1, 2, 6, 5),  # Right
        (2, 3, 7, 6),  # Back
        (3, 0, 4, 7),  # Left
    ]

    return vertices, faces
