#!/usr/bin/env python3
"""
Generate PaperSort app icon
Clean, modern design representing paper organization
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_icon(size=1024):
    """Create app icon with gradient background and paper stack symbol"""

    # Create image with transparent background
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Modern gradient background (blue to purple)
    for y in range(size):
        # Gradient from #4A90E2 (blue) to #7B68EE (purple)
        r = int(74 + (123 - 74) * (y / size))
        g = int(144 + (104 - 144) * (y / size))
        b = int(226 + (238 - 226) * (y / size))
        draw.rectangle([(0, y), (size, y+1)], fill=(r, g, b, 255))

    # Add rounded corners
    mask = Image.new('L', (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    corner_radius = size // 5
    mask_draw.rounded_rectangle([(0, 0), (size, size)], radius=corner_radius, fill=255)

    # Apply mask for rounded corners
    output = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    output.paste(img, (0, 0))
    output.putalpha(mask)

    # Draw paper stack icon
    paper_width = size // 2
    paper_height = int(size * 0.6)
    paper_x = (size - paper_width) // 2
    paper_y = (size - paper_height) // 2 - size // 20

    # Draw 3 stacked papers with white color and slight offset
    papers = [
        (paper_x + size//20, paper_y + size//20),  # Back paper
        (paper_x + size//40, paper_y + size//40),  # Middle paper
        (paper_x, paper_y)  # Front paper
    ]

    draw = ImageDraw.Draw(output)

    for i, (x, y) in enumerate(papers):
        alpha = 180 if i < 2 else 255
        # Draw paper with lines
        draw.rounded_rectangle(
            [(x, y), (x + paper_width, y + paper_height)],
            radius=size//40,
            fill=(255, 255, 255, alpha),
            outline=(200, 200, 200, alpha),
            width=size//200
        )

        # Draw horizontal lines on papers (only on front paper)
        if i == 2:
            line_spacing = paper_height // 8
            line_margin = paper_width // 6
            for line_num in range(1, 6):
                line_y = y + line_spacing * line_num + paper_height // 6
                draw.line(
                    [(x + line_margin, line_y), (x + paper_width - line_margin, line_y)],
                    fill=(100, 120, 200, 200),
                    width=size//150
                )

    # Add a small "sort" arrow/indicator
    arrow_size = size // 8
    arrow_x = paper_x + paper_width - arrow_size - size // 40
    arrow_y = paper_y - arrow_size // 2

    # Draw downward arrow with gradient
    arrow_points = [
        (arrow_x + arrow_size//2, arrow_y + arrow_size),  # Bottom point
        (arrow_x, arrow_y),  # Top left
        (arrow_x + arrow_size, arrow_y),  # Top right
    ]
    draw.polygon(arrow_points, fill=(50, 200, 50, 255))

    return output


def main():
    """Generate icon in multiple sizes"""
    sizes = [1024, 512, 256, 128]

    # Create icons directory
    icon_dir = '/Users/ruichaowang/Project_PaperSortApp/electron'
    os.makedirs(icon_dir, exist_ok=True)

    for size in sizes:
        icon = create_icon(size)
        icon_path = f'{icon_dir}/icon_{size}.png'
        icon.save(icon_path, 'PNG')
        print(f'Created {icon_path}')

    # Create main icon (1024x1024)
    icon_1024 = create_icon(1024)
    icon_1024.save(f'{icon_dir}/icon.png', 'PNG')
    print(f'Created {icon_dir}/icon.png')

    print('\nIcon generation complete!')
    print(f'Icons saved to: {icon_dir}/')


if __name__ == '__main__':
    main()
