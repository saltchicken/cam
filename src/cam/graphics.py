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
