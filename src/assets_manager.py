# assets_manager.py
import pygame
import os
import json

LOADED_THEMES = {}

def load_assets():
    """
    Load all theme assets from assets/themes.json
    """
    config_path = "assets/themes.json"
    if not os.path.exists(config_path):
        return

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        themes = data.get('themes', [])
        for theme_config in themes:
            theme_name = theme_config['name']
            sheet_path = theme_config['file']
            tile_size = theme_config.get('tile_size', 16)
            mapping = theme_config.get('mapping', {})
            
            if not os.path.exists(sheet_path):
                continue
                
            sheet = pygame.image.load(sheet_path).convert_alpha()
            sheet_w, sheet_h = sheet.get_size()
            cols = sheet_w // tile_size
            rows = sheet_h // tile_size
            
            all_tiles = []
            for r in range(rows):
                for c in range(cols):
                    rect = pygame.Rect(c * tile_size, r * tile_size, tile_size, tile_size)
                    tile = sheet.subsurface(rect).copy()
                    all_tiles.append(tile)
            
            LOADED_THEMES[theme_name] = {}
            for tile_name, pos in mapping.items():
                if isinstance(pos, list) and len(pos) == 2:
                    col, row = pos
                    if col < cols and row < rows:
                        tile_index = row * cols + col
                        if tile_index < len(all_tiles):
                            LOADED_THEMES[theme_name][tile_name] = all_tiles[tile_index]
                            
    except Exception:
        pass
