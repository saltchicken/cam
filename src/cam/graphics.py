"""Math and rendering utilities."""

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
