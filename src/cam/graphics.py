"""Math and rendering utilities."""
import math


def project_iso(x, y, z, scale, offset_x, offset_y):
    """Converts 3D CNC coordinates into 2D screen pixels."""
    angle = math.radians(30)
    screen_x = (x - y) * math.cos(angle) * scale + offset_x
    screen_y = offset_y - (x + y) * math.sin(angle) * scale - (z * scale)
    return [screen_x, screen_y]
