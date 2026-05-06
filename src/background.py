import pygame
import os
import random
from config import SCREEN_W, SCREEN_H

class ParallaxLayer:
    def __init__(self, image_path, speed, screen_h):
        self.original_image = pygame.image.load(image_path).convert_alpha()
        img_w, img_h = self.original_image.get_size()
        # Scale image height to be taller than screen to allow shifting up without leaving gaps at the bottom
        # Increased scale factor and shift to cover the top area
        scale_factor = (screen_h + 400) / img_h
        new_w = int(img_w * scale_factor)
        self.image = pygame.transform.scale(self.original_image, (new_w, screen_h + 400))
        self.width = self.image.get_width()
        self.speed = speed
        self.y_offset = -280  # Shift up higher to cover upper areas (Quest/HUD area)


    def draw(self, screen, x_offset):
        rel_x = int(x_offset * self.speed) % self.width
        screen.blit(self.image, (-rel_x, self.y_offset))
        if rel_x > 0:
            screen.blit(self.image, (self.width - rel_x, self.y_offset))
        if self.width - rel_x < SCREEN_W:
            extra_tiles = (SCREEN_W // self.width) + 1
            for i in range(1, extra_tiles):
                screen.blit(self.image, (self.width * i - rel_x, self.y_offset))


class ForestBackground:
    def __init__(self):
        self.layers = []
        bg_dir = "assets/backgrounds"
        layer_configs = [
            ("Layer_0011_0.png", 0.0),    # Sky
            ("Layer_0010_1.png", 0.05),   # Far trees 1
            ("Layer_0009_2.png", 0.1),    # Far trees 2
            ("Layer_0008_3.png", 0.15),   # Far trees 3
            ("Layer_0007_Lights.png", 0.15), # God rays (back)
            ("Layer_0006_4.png", 0.25),   # Mid trees 1
            ("Layer_0005_5.png", 0.4),    # Mid trees 2
            ("Layer_0004_Lights.png", 0.4),  # God rays (mid)
            ("Layer_0003_6.png", 0.6),    # Near trees 1
            ("Layer_0002_7.png", 0.8),    # Near trees 2
            ("Layer_0001_8.png", 0.95),   # Very near trees
            ("Layer_0000_9.png", 1.1)     # Foreground bushes
        ]

        for filename, speed in layer_configs:
            path = os.path.join(bg_dir, filename)
            if os.path.exists(path):
                self.layers.append(ParallaxLayer(path, speed, SCREEN_H))
        
        # Column asset loading removed as per request

    def draw(self, screen, world_x_offset, level_length=None):
        if not self.layers:
            screen.fill((10, 20, 10))
            return
            
        # Draw background layers up to Near trees 2
        for i, layer in enumerate(self.layers):
            if i < 10: # Draw up to Layer_0002_7 (Near trees 2)
                layer.draw(screen, world_x_offset)
        
        # Columns drawing removed

        # Draw remaining foreground layers
        for i, layer in enumerate(self.layers):
            if i >= 10:
                layer.draw(screen, world_x_offset)

class GothicBackground:
    def __init__(self, layer_configs=None):
        try:
            self.tileset = pygame.image.load("assets/backgrounds/tileset.png").convert_alpha()
            self.tile_size = self.tileset.get_width() // 4
            self.tiles = []
            for r in range(4):
                row_tiles = []
                for c in range(4):
                    rect = pygame.Rect(c * self.tile_size, r * self.tile_size, self.tile_size, self.tile_size)
                    row_tiles.append(self.tileset.subsurface(rect))
                self.tiles.append(row_tiles)
            self.hero_assets = []
            try:
                self.background_props = pygame.image.load("assets/backgrounds/backgrounds.png").convert_alpha()
                asset_w = self.background_props.get_width() // 3
                for i in range(3):
                    rect = pygame.Rect(i * asset_w, 0, asset_w, self.background_props.get_height())
                    self.hero_assets.append(self.background_props.subsurface(rect))
            except Exception:
                self.background_props = None
            self.bg_color = (26, 26, 46) 
            self.hero_positions = []
            random.seed(42) 
            for i in range(100): 
                asset_idx = random.randint(0, len(self.hero_assets) - 1) if self.hero_assets else 0
                x_pos = i * 600 + 150 
                y_pos = random.randint(150, 300)
                self.hero_positions.append((x_pos, y_pos, asset_idx))
        except Exception:
            self.tiles = None

    def draw(self, screen, world_x_offset, level_length=None):
        if not self.tiles:
            screen.fill((20, 20, 30))
            return
        screen.fill(self.bg_color)
        mid_parallax_offset = world_x_offset * 0.8
        for x_pos, y_pos, asset_idx in self.hero_positions:
            screen_x = x_pos - mid_parallax_offset
            if -300 < screen_x < SCREEN_W + 300:
                asset = self.hero_assets[asset_idx]
                screen.blit(asset, (screen_x, y_pos))
        num_tiles_x = (SCREEN_W // self.tile_size) + 2
        offset_x = -(world_x_offset % self.tile_size)
        start_tile_x = int(world_x_offset // self.tile_size)
        for i in range(num_tiles_x):
            tx = offset_x + i * self.tile_size
            tile_idx = (start_tile_x + i) % 4
            screen.blit(self.tiles[1][tile_idx], (tx, 20))
        # Columns drawing removed
