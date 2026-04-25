
from PIL import Image, ImageEnhance
import os

def create_background():
    # Paths
    tileset_path = 'assets/backgrounds/tileset.png'
    column_path = 'assets/backgrounds/column.png'
    output_path = 'assets/backgrounds/castle_bg_assembled.png'
    
    if not os.path.exists(tileset_path):
        print("Tileset not found!")
        return

    # Load assets
    tileset = Image.open(tileset_path)
    tile_size = 48
    
    def get_tile(col, row):
        left = col * tile_size
        top = row * tile_size
        return tileset.crop((left, top, left + tile_size, top + tile_size))

    # Screen dimensions
    width = 1280
    height = 720
    
    # Create base background (dark purple)
    bg = Image.new('RGBA', (width, height), (20, 15, 30, 255))
    
    # 1. Fill with background wall tiles (Darkened)
    wall_fill = get_tile(1, 1)
    enhancer = ImageEnhance.Brightness(wall_fill)
    wall_fill_dark = enhancer.enhance(0.4)
    
    for y in range(0, height, tile_size):
        for x in range(0, width, tile_size):
            bg.paste(wall_fill_dark, (x, y))
            
    # 2. Add some "arch" structures at the top
    arch_left = get_tile(0, 0)
    arch_mid = get_tile(1, 0)
    arch_right = get_tile(2, 0)
    
    arch_spacing = 384 # Every 8 tiles
    for x in range(0, width, arch_spacing):
        # Draw a wide arch
        bg.paste(arch_left, (x, 0), arch_left)
        for i in range(1, 7):
            bg.paste(arch_mid, (x + i * tile_size, 0), arch_mid)
        bg.paste(arch_right, (x + 7 * tile_size, 0), arch_right)

    # 3. Add columns (using column.png if exists, or tiles)
    if os.path.exists(column_path):
        col_img = Image.open(column_path)
        # Column is 114x190. Let's scale it slightly or just place it.
        col_spacing = 384
        for x in range(0, width, col_spacing):
            # Place column under the arch joints
            bg.paste(col_img, (x - 30, 0), col_img)
            bg.paste(col_img, (x + 384 - 84, 0), col_img)

    # 4. Add some decorative altar/window from backgrounds.png if possible
    panel_path = 'assets/backgrounds/backgrounds.png'
    if os.path.exists(panel_path):
        panels = Image.open(panel_path)
        # Paste panels in the middle of arches
        for x in range(96, width, arch_spacing):
            # Crop a panel (approx 100x150)
            panel = panels.crop((0, 0, 120, 180)) # Just a guess of the first panel
            bg.paste(panel, (x + 80, 200), panel)

    # Save final background
    bg.save(output_path)
    print(f"Background saved to {output_path}")

if __name__ == "__main__":
    create_background()
