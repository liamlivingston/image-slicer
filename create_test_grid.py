#!/usr/bin/env python3
import os
from PIL import Image, ImageDraw

def generate_grid_all(cell_size=100, border=15, rows=3, cols=3):
    """
    Generates a grid where borders exist around all cells (including the outer edges).
    Total width = cols * cell_size + (cols + 1) * border
    """
    width = cols * cell_size + (cols + 1) * border
    height = rows * cell_size + (rows + 1) * border
    
    # Create image with a gray background (the border color)
    img = Image.new("RGB", (width, height), color=(80, 80, 80))
    draw = ImageDraw.Draw(img)
    
    # 9 distinct colors for cells
    colors = [
        (240, 98, 146),  # Pink
        (121, 85, 72),   # Brown
        (77, 208, 225),  # Cyan
        (220, 231, 117), # Lime
        (186, 104, 200), # Purple
        (255, 183, 77),  # Orange
        (129, 199, 132), # Green
        (100, 181, 246), # Blue
        (255, 241, 118)  # Yellow
    ]
    
    for r in range(rows):
        for c in range(cols):
            l = border + c * (cell_size + border)
            t = border + r * (cell_size + border)
            r_coord = l + cell_size
            b_coord = t + cell_size
            
            # Fill cell color (coordinates are inclusive for PIL rectangle draw)
            color = colors[(r * cols + c) % len(colors)]
            draw.rectangle([l, t, r_coord - 1, b_coord - 1], fill=color)
            
            # Draw grid cell coordinates text as label
            text = f"Cell {r+1},{c+1}"
            draw.text((l + 10, t + 10), text, fill=(0, 0, 0))
            
    filename = "test_grid_all.png"
    img.save(filename)
    print(f"Saved {filename} ({width}x{height})")

def generate_grid_between(cell_size=100, border=15, rows=3, cols=3):
    """
    Generates a grid where borders exist only between cells (no outer borders).
    Total width = cols * cell_size + (cols - 1) * border
    """
    width = cols * cell_size + (cols - 1) * border
    height = rows * cell_size + (rows - 1) * border
    
    # Create image with a gray background (the border color)
    img = Image.new("RGB", (width, height), color=(80, 80, 80))
    draw = ImageDraw.Draw(img)
    
    # 9 distinct colors for cells
    colors = [
        (240, 98, 146),  # Pink
        (121, 85, 72),   # Brown
        (77, 208, 225),  # Cyan
        (220, 231, 117), # Lime
        (186, 104, 200), # Purple
        (255, 183, 77),  # Orange
        (129, 199, 132), # Green
        (100, 181, 246), # Blue
        (255, 241, 118)  # Yellow
    ]
    
    for r in range(rows):
        for c in range(cols):
            l = c * (cell_size + border)
            t = r * (cell_size + border)
            r_coord = l + cell_size
            b_coord = t + cell_size
            
            # Fill cell color
            color = colors[(r * cols + c) % len(colors)]
            draw.rectangle([l, t, r_coord - 1, b_coord - 1], fill=color)
            
            # Draw grid cell coordinates text as label
            text = f"Cell {r+1},{c+1}"
            draw.text((l + 10, t + 10), text, fill=(0, 0, 0))
            
    filename = "test_grid_between.png"
    img.save(filename)
    print(f"Saved {filename} ({width}x{height})")

if __name__ == "__main__":
    generate_grid_all()
    generate_grid_between()
