
from PIL import Image, ImageEnhance
import os

def redesign_background():
    # Paths
    tileset_path = 'assets/tilesets/dungeon_tileset.png'
    output_path = 'assets/backgrounds/dungeon_bg.png'
    
    if not os.path.exists(tileset_path):
        print(f"Tileset {tileset_path} not found!")
        # Fallback to medieval if dungeon is missing
        tileset_path = 'assets/backgrounds/tileset.png'
        if not os.path.exists(tileset_path):
            return

    # Load assets
    tileset = Image.open(tileset_path)
    # Detect tile size based on our guess (24x24 for dungeon_tileset.png)
    if 'dungeon_tileset' in tileset_path:
        tile_size = 24
    else:
        tile_size = 48 # For the other tileset.png
        
    def get_tile(col, row):
        left = col * tile_size
        top = row * tile_size
        if left + tile_size > tileset.width or top + tile_size > tileset.height:
            return Image.new('RGBA', (tile_size, tile_size), (0,0,0,0))
        return tileset.crop((left, top, left + tile_size, top + tile_size))

    # Screen dimensions
    width = 1280
    height = 720
    
    # Create base background (Darker purple/blue)
    bg = Image.new('RGBA', (width, height), (15, 10, 25, 255))
    
    # 1. Fill with background wall tiles from the TOP ROW
    # Assuming tile (1, 0) is a good background fill
    wall_fill = get_tile(1, 0)
    enhancer = ImageEnhance.Brightness(wall_fill)
    wall_fill_dark = enhancer.enhance(0.4) # Make it dark so it's a background
    
    for y in range(0, height, tile_size):
        # Create a vertical gradient effect by darkening the tiles as they go down
        depth_factor = 1.0 - (y / height) * 0.5
        row_enhancer = ImageEnhance.Brightness(wall_fill_dark)
        row_tile = row_enhancer.enhance(depth_factor)
        
        for x in range(0, width, tile_size):
            bg.paste(row_tile, (x, y))
            
    # 2. Add Arch structures at the TOP (using row 0)
    # We'll try tiles 2, 3, 4 from the top row for the arch
    arch_left = get_tile(2, 0)
    arch_mid = get_tile(3, 0)
    arch_right = get_tile(4, 0)
    
    # Scale arches up for more presence (4x)
    scaled_tile_size = tile_size * 4
    arch_left = arch_left.resize((scaled_tile_size, scaled_tile_size), Image.NEAREST)
    arch_mid = arch_mid.resize((scaled_tile_size, scaled_tile_size), Image.NEAREST)
    arch_right = arch_right.resize((scaled_tile_size, scaled_tile_size), Image.NEAREST)
    
    # Make arches slightly brighter than background
    arch_enhancer = ImageEnhance.Brightness(arch_left)
    arch_left = arch_enhancer.enhance(1.2)
    arch_mid = ImageEnhance.Brightness(arch_mid).enhance(1.2)
    arch_right = ImageEnhance.Brightness(arch_right).enhance(1.2)
    
    arch_width = scaled_tile_size * 4 # Arch composed of L + 2xM + R
    for x in range(0, width, arch_width):
        bg.paste(arch_left, (x, 0), arch_left)
        bg.paste(arch_mid, (x + scaled_tile_size, 0), arch_mid)
        bg.paste(arch_mid, (x + 2 * scaled_tile_size, 0), arch_mid)
        bg.paste(arch_right, (x + 3 * scaled_tile_size, 0), arch_right)

    # 3. Add Columns (assuming row 0 or 1 has column parts)
    # Let's try row 1 for columns if row 0 is just arches
    col_top = get_tile(2, 1).resize((scaled_tile_size, scaled_tile_size), Image.NEAREST)
    col_mid = get_tile(2, 2).resize((scaled_tile_size, scaled_tile_size), Image.NEAREST)
    
    # Darken columns slightly as they go down
    for x in range(0, width, arch_width):
        # Joint at x=0
        bg.paste(col_top, (x - scaled_tile_size//2, scaled_tile_size//2), col_top)
        for y in range(scaled_tile_size, height, scaled_tile_size):
            c_depth = 1.0 - (y / height) * 0.4
            c_tile = ImageEnhance.Brightness(col_mid).enhance(c_depth)
            bg.paste(c_tile, (x - scaled_tile_size//2, y), c_tile)
        
        # Joint at x + arch_width
        bg.paste(col_top, (x + arch_width - scaled_tile_size//2, scaled_tile_size//2), col_top)
        for y in range(scaled_tile_size, height, scaled_tile_size):
            c_depth = 1.0 - (y / height) * 0.4
            c_tile = ImageEnhance.Brightness(col_mid).enhance(c_depth)
            bg.paste(c_tile, (x + arch_width - scaled_tile_size//2, y), c_tile)

    # Save final background
    bg.save(output_path)
    print(f"Background redesigned and saved to {output_path}")

if __name__ == "__main__":
    redesign_background()
