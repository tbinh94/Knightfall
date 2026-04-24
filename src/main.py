import pygame
import sys
import json
import random
import math
import neat
import os
from collections import deque

# Import responsive config
try:
    from config import *
    print("✓ Using responsive configuration")
except ImportError:
    from config import *
    print("⚠️ Using old config, responsive features may not work properly")

from assets_manager import LOADED_THEMES, load_assets
from enemy_manager import LOADED_ENEMIES, load_enemies, get_random_enemy, get_enemy_data, get_enemy_config
from decoy_manager import LOADED_DECOYS, load_decoys, get_random_decoy, get_decoy_data, get_decoy_config
from battle_system import BattleSystem
from shop_system import ShopSystem
from player_stats import PlayerStats, Card

# Thiết lập giá trị mặc định
if 'PLAYER_TARGET_X' not in globals():
    PLAYER_TARGET_X = SCREEN_W // 3

# -------------------------
# Initialization Helper
# -------------------------
def initialize_pygame_and_assets():
    if not pygame.get_init():
        pygame.init()
        print("✓ Pygame initialized")
    
    # Print resolution info
    if hasattr(sys.modules.get('config'), 'print_resolution_info'):
        from config import print_resolution_info
        print_resolution_info()
    
    if not LOADED_THEMES: load_assets()
    else: print("ℹ️ Assets already loaded, skipping...")
    
    if not LOADED_ENEMIES: load_enemies()
    else: print("ℹ️ Enemies already loaded, skipping...")
    
    if not LOADED_DECOYS: load_decoys()
    else: print("ℹ️ Decoys already loaded, skipping...")

# -------------------------
# Multi-Layer Background (RESPONSIVE)
# -------------------------
class MultiLayerBackground:
    """
    🎨 IMPROVED: Responsive background that fills entire screen
    """
    def __init__(self, layer_configs):
        self.layers = []
        try:
            for config in layer_configs:
                surface = pygame.image.load(config["file"]).convert_alpha()
                # Scale to full screen size
                scaled_surface = pygame.transform.scale(surface, (SCREEN_W, SCREEN_H))
                self.layers.append({
                    "image": scaled_surface,
                    "speed": config["speed"],
                    "width": scaled_surface.get_width()
                })
            print(f"✓ Loaded {len(self.layers)} background layers at {SCREEN_W}x{SCREEN_H}")
        except pygame.error as e:
            print(f"✗ Error loading background file: {e}")
        except Exception as e:
            print(f"✗ Unknown error loading background: {e}")
            
    def draw(self, screen, world_x_offset, level_length):
        """Draw background with parallax effect - fills from top to bottom"""
        for layer in self.layers:
            if level_length == -1: 
                actual_scroll = world_x_offset * layer["speed"]
            else:
                max_scroll = max(0, level_length - SCREEN_W)
                actual_scroll = min(world_x_offset * layer["speed"], max_scroll * layer["speed"])
            
            x1 = -(actual_scroll % layer["width"])
            # Draw at y=0 to fill entire screen height
            screen.blit(layer["image"], (x1, 0))
            if x1 < 0:
                screen.blit(layer["image"], (x1 + layer["width"], 0))

# -------------------------
# Game Entities (RESPONSIVE)
# -------------------------
class Obstacle:
    def __init__(self, x, y, w=30, h=50, kind="real"):
        self.x = x
        self.y = y
        # Apply responsive scaling
        scale = SCALE_UNIFORM if 'SCALE_UNIFORM' in globals() else 1.0
        self.w = int(w * scale)
        self.h = int(h * scale)
        self.kind = kind
        
    def rect(self):
        return pygame.Rect(self.x, self.y - self.h, self.w, self.h)

class Platform:
    def __init__(self, x, y, length):
        self.x = x
        self.y = y
        self.length = length

class Wall:
    def __init__(self, x, y, height):
        self.x = x
        self.y = y
        self.height = height
        scale = SCALE_UNIFORM if 'SCALE_UNIFORM' in globals() else 1.0
        self.width = int(10 * scale)

class WallTile:
    def __init__(self, x, y, width=10, tile_height=40):
        scale = SCALE_UNIFORM if 'SCALE_UNIFORM' in globals() else 1.0
        self.x = x
        self.y = y
        self.width = int(width * scale)
        self.tile_height = int(tile_height * scale)

    def rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.tile_height)

# -------------------------
# WALL STATE SYSTEM
# -------------------------
class WallState:
    def __init__(self):
        self.is_sliding = False
        self.side = None
        self.time_elapsed = 0.0
        self.can_jump = True
        self.jump_cooldown = 0.0
        self.re_attach_cooldown = 0.0

    def reset(self):
        self.is_sliding = False
        self.side = None
        self.time_elapsed = 0.0
        self.can_jump = True
        self.jump_cooldown = 0.0
        self.re_attach_cooldown = 0.0
    
    def start_slide(self, side):
        if (not self.is_sliding or self.side != side) and self.re_attach_cooldown <= 0:
            self.is_sliding = True
            self.side = side
            self.time_elapsed = 0.0
            if self.jump_cooldown <= 0:
                self.can_jump = True
    
    def stop_slide(self):
        self.is_sliding = False
        self.side = None
        self.time_elapsed = 0.0
    
    def execute_jump(self):
        if self.can_jump and self.is_sliding:
            self.can_jump = False
            self.jump_cooldown = CONSECUTIVE_WALL_JUMP_COOLDOWN
            self.re_attach_cooldown = 0.2
            return True
        return False
    
    def update(self, delta_time):
        if self.is_sliding:
            self.time_elapsed += delta_time
        
        if self.jump_cooldown > 0:
            self.jump_cooldown -= delta_time
        elif not self.can_jump:
            self.can_jump = True
            
        if self.re_attach_cooldown > 0:
            self.re_attach_cooldown -= delta_time

# -------------------------
# Terrain Type Handlers (RESPONSIVE)
# -------------------------
class TerrainGenerator:
    @staticmethod
    def straight(cursor_x, config):
        # Trust the platform_y from the JSON file. Fallback to GROUND_Y if not specified.
        plat_y = config.get("platform_y", GROUND_Y)
        length = config.get("length", 500)
        platform = Platform(cursor_x, plat_y, length)
        obstacles = []
        for ob in config.get("obstacles", []):
            ox = cursor_x + ob["x"]
            oy = plat_y if ob["y"] == "ground" else plat_y + ob["y"]
            kind = ob.get("kind", "real")
            obstacles.append(Obstacle(ox, oy, kind=kind))
        return {"type": "straight", "platform": platform, "obstacles": obstacles, "length": length}

    @staticmethod
    def stairs_up(cursor_x, config):
        # Trust the start_y from the JSON file.
        start_y = config.get("start_y", GROUND_Y)
        step_height = config.get("step_height", 40)
        step_width = config.get("step_width", 120)
        num_steps = config.get("step_count", 5)
        total_length = step_width * num_steps
        platforms = []
        obstacles = []
        for i in range(num_steps):
            step_x = cursor_x + i * step_width
            step_y = start_y - (i * step_height)
            platforms.append(Platform(step_x, step_y, step_width))
        for ob_config in config.get("obstacles", []):
            step_index = ob_config.get("step_index")
            if step_index is not None and 0 <= step_index < len(platforms):
                target_platform = platforms[step_index]
                ox = target_platform.x + ob_config.get("x_offset", step_width / 2)
                oy = target_platform.y
                kind = ob_config.get("kind", "real")
                obstacles.append(Obstacle(ox, oy, kind=kind))
        return {"type": "stairs_up", "platforms": platforms, "obstacles": obstacles, "length": total_length}

    @staticmethod
    def stairs_down(cursor_x, config):
        # Trust the start_y from the JSON file.
        start_y = config.get("start_y", GROUND_Y)
        step_height = config.get("step_height", 40)
        step_width = config.get("step_width", 100)
        num_steps = config.get("step_count", 5)
        total_length = step_width * num_steps
        platforms = []
        obstacles = []
        for i in range(num_steps):
            step_x = cursor_x + i * step_width
            step_y = start_y + (i * step_height)
            platforms.append(Platform(step_x, step_y, step_width))
        for ob_config in config.get("obstacles", []):
            step_index = ob_config.get("step_index")
            if step_index is not None and 0 <= step_index < len(platforms):
                target_platform = platforms[step_index]
                ox = target_platform.x + ob_config.get("x_offset", step_width / 2)
                oy = target_platform.y
                kind = ob_config.get("kind", "real")
                obstacles.append(Obstacle(ox, oy, kind=kind))
        return {"type": "stairs_down", "platforms": platforms, "obstacles": obstacles, "length": total_length}

    @staticmethod
    def gap(cursor_x, config):
        length = config.get("length", 500)
        # Trust the base_y from the JSON file.
        base_y = config.get("base_y", GROUND_Y)
        platforms_data = config.get("platforms", [])
        platforms = []
        for p_data in platforms_data:
            p_x = cursor_x + p_data["x"]
            p_y = base_y + p_data.get("y_offset", 0)
            p_width = p_data["width"]
            platforms.append(Platform(p_x, p_y, p_width))
        obstacles = []
        for ob_config in config.get("obstacles", []):
            platform_index = ob_config.get("platform_index")
            if platform_index is not None and 0 <= platform_index < len(platforms):
                target_platform = platforms[platform_index]
                ox = target_platform.x + ob_config.get("x", target_platform.length / 2)
                oy = target_platform.y
                kind = ob_config.get("kind", "real")
                obstacles.append(Obstacle(ox, oy, kind=kind))
            elif "x" in ob_config and "y" in ob_config:
                y_val = ob_config["y"]
                oy = None
                if isinstance(y_val, (int, float)): oy = base_y - y_val
                elif y_val == "midair": oy = base_y - 150
                if oy is not None:
                    ox = cursor_x + ob_config["x"]
                    kind = ob_config.get("kind", "real")
                    obstacles.append(Obstacle(ox, oy, kind=kind))
        return {"type": "gap", "platforms": platforms, "obstacles": obstacles, "length": length}
    
    @staticmethod
    def wall_jump(cursor_x, config):
        wall_height = config.get("height", 250)
        shaft_width = config.get("shaft_width", 150)
        # Trust the entry_y from the JSON file.
        entry_y = config.get("entry_y", GROUND_Y)
        
        entry_platform_len = 100
        exit_platform_len = 150
        wall_tile_width = 10
        wall_tile_height = 40
        
        platforms = []
        wall_tiles = []
        obstacles = []

        platforms.append(Platform(cursor_x, entry_y, entry_platform_len))

        wall_left_x = cursor_x + entry_platform_len
        wall_right_x = wall_left_x + shaft_width
        wall_top_y = entry_y - wall_height
        
        for i in range(0, wall_height, wall_tile_height):
            wall_tiles.append(WallTile(wall_left_x, entry_y - i, wall_tile_width, wall_tile_height))
        
        for i in range(0, wall_height, wall_tile_height):
            wall_tiles.append(WallTile(wall_right_x, entry_y - i, wall_tile_width, wall_tile_height))

        exit_platform_x = wall_right_x + wall_tile_width
        exit_platform_y = wall_top_y
        platforms.append(Platform(exit_platform_x, exit_platform_y, exit_platform_len))

        total_length = (exit_platform_x + exit_platform_len) - cursor_x

        return {
            "type": "wall_jump",
            "platforms": platforms,
            "wall_tiles": wall_tiles,
            "obstacles": obstacles,
            "length": total_length
        }

# -------------------------
# Endless Manager
# -------------------------
class EndlessManager:
    def __init__(self, patterns_data, spawn_logic):
        self.patterns = patterns_data
        self.spawn_logic = spawn_logic
        self.last_pattern_id = None
        print(f"✓ EndlessManager initialized with {len(self.patterns)} patterns.")
        if not self.patterns:
            raise ValueError("Endless mode requires at least one pattern.")
            
    def get_next_pattern(self):
        if self.spawn_logic.get("order") == "random":
            if self.spawn_logic.get("avoid_consecutive_same") and len(self.patterns) > 1:
                available_patterns = [p for p in self.patterns if p.get("id") != self.last_pattern_id]
                chosen_pattern = random.choice(available_patterns)
            else:
                chosen_pattern = random.choice(self.patterns)
            self.last_pattern_id = chosen_pattern.get("id")
            return chosen_pattern
        else:
            return random.choice(self.patterns)

# -------------------------
# Level Loader (JSON)
# -------------------------
def load_level(path):
    full_path = os.path.join('levels', path)
    with open(full_path, "r", encoding="utf-8") as f: 
        data = json.load(f)
    theme_name = data.get("theme", "dungeon").strip()
    is_endless = data.get("mode") == "endless"
    
    if is_endless:
        patterns = data.get("patterns", [])
        spawn_logic = data.get("spawn_logic", {})
        return {"patterns": patterns, "spawn_logic": spawn_logic, "theme": theme_name, "is_endless": True}
    else:
        world = []
        print(f"💡 Injecting a {SAFE_ZONE_DISTANCE}px safe zone at the start of the level.")
        # Determine the y of the very first platform from the JSON to create a matching safe zone
        first_plat_y = GROUND_Y
        if data.get("sections"):
            first_plat_y = data["sections"][0].get("platform_y", data["sections"][0].get("start_y", GROUND_Y))

        safe_zone_config = {"type": "straight", "platform_y": first_plat_y, "length": SAFE_ZONE_DISTANCE, "obstacles": []}
        safe_segment = TerrainGenerator.straight(0, safe_zone_config)
        world.append(safe_segment)
        cursor_x = SAFE_ZONE_DISTANCE
        
        for sec in data.get("sections", []):
            terrain_type = sec.get("type", "straight")
            terrain_func = getattr(TerrainGenerator, terrain_type, TerrainGenerator.straight)
            segment = terrain_func(cursor_x, sec)
            world.append(segment)
            cursor_x += segment["length"]
        total_length = cursor_x
        return {"world": world, "length": total_length, "theme": theme_name, "is_endless": False}

# -------------------------
# Game Sprites
# -------------------------
def collide_player_hitbox(player, obstacle_sprite):
    player_hitbox = player.hitbox
    obstacle_rect = obstacle_sprite.image.get_rect(midbottom=obstacle_sprite.rect.midbottom)
    return player_hitbox.colliderect(obstacle_rect)

class ObstacleSprite(pygame.sprite.Sprite):
    def __init__(self, world_x, y, kind='real', sprite_type=None):
        super().__init__()
        # Layering: 0 = decor (background), 1 = enemies/allies, 2 = player
        self._layer = 0 if kind == 'decor' else 1
        self.kind = kind
        self.sprite_type = sprite_type
        self.current_frame = 0
        self.anim_timer = 0.0
        self.scaled_frames = []
        self.is_animated = True
        self.world_pos = pygame.math.Vector2(world_x, y)
        
        sprite_data, sprite_config = (None, None)
        if self.sprite_type:
            if self.kind == 'real':
                sprite_data = get_enemy_data(self.sprite_type)
                sprite_config = get_enemy_config(self.sprite_type)
            elif self.kind in ['fake', 'decor']:
                sprite_data = get_decoy_data(self.sprite_type)
                sprite_config = get_decoy_config(self.sprite_type)
                
        if sprite_data and sprite_config:
            self.frames = sprite_data['frames']
            self.animation_speed = sprite_config['animation_speed']
            self.scale = sprite_config['scale']
            y_offset = sprite_config['y_offset']
            self.is_animated = not sprite_config['use_static_frame']
            self.world_pos.y += y_offset
            self.world_pos.x += 15 
            
            for frame in self.frames:
                original_w, original_h = frame.get_size()
                new_w, new_h = int(original_w * self.scale), int(original_h * self.scale)
                self.scaled_frames.append(pygame.transform.scale(frame, (new_w, new_h)))
                
            self.image = self.scaled_frames[0]
            self.rect = self.image.get_rect()
        else:
            width, height = (30, 50)
            color = (200, 40, 40) if kind == 'real' else (120, 120, 220)
            self.image = pygame.Surface([width, height])
            self.image.fill(color)
            self.rect = self.image.get_rect()
            self.world_pos.x += width / 2
            self.is_animated = False
            
    def update(self, world_x_offset, delta_time):
        if self.is_animated and self.scaled_frames:
            self.anim_timer += delta_time * 1000
            if self.anim_timer > self.animation_speed:
                self.anim_timer %= self.animation_speed
                self.current_frame = (self.current_frame + 1) % len(self.scaled_frames)
                self.image = self.scaled_frames[self.current_frame]
        screen_x = self.world_pos.x - world_x_offset
        self.rect.midbottom = (screen_x, self.world_pos.y)

class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self._layer = 2
        self.vx = 0
        self.vy = 0
        self.on_ground = True
        self.state = 'run'
        self.current_frame = 0
        self.anim_timer = 0.0
        self.animations = {}
        self.wall_state = WallState()
        self.facing_right = True # For sprite flipping
        self.double_jump_available = True
        self.jump_queued = False
        
        for anim_name, anim_cfg in ANIMATION_CONFIG.items():
            self.animations[anim_name] = self.load_spritesheet(
                anim_cfg['file'], anim_cfg['frames'], anim_cfg['frame_width'],
                anim_cfg['frame_height'], anim_cfg['scale'], anim_cfg['speed'],
                anim_cfg.get('y_offset', 0)
            )
        self.image = self.animations[self.state]['frames'][self.current_frame]
        
        self.hitbox = pygame.Rect(x, 0, PLAYER_W, PLAYER_H)
        self.hitbox.bottom = y
        self.pos_y = float(self.hitbox.y)
        self.rect = self.image.get_rect(midbottom=self.hitbox.midbottom)

    def load_spritesheet(self, path, num_frames, frame_w, frame_h, scale, anim_speed, y_offset=0):
        frames = []
        try:
            spritesheet = pygame.image.load(path).convert_alpha()
            cols = spritesheet.get_width() // frame_w
            for i in range(num_frames):
                row = i // cols
                col = i % cols
                rect = pygame.Rect(col * frame_w, row * frame_h, frame_w, frame_h)
                frame = spritesheet.subsurface(rect)
                new_w = int(frame_w * scale)
                new_h = int(frame_h * scale)
                frame = pygame.transform.scale(frame, (new_w, new_h))
                frames.append(frame)
        except pygame.error as e:
            print(f"Error loading spritesheet '{path}': {e}")
            placeholder = pygame.Surface((int(frame_w*scale), int(frame_h*scale)), pygame.SRCALPHA)
            placeholder.fill((255, 0, 255, 128))
            frames.append(placeholder)
        return {'frames': frames, 'speed': anim_speed, 'y_offset': y_offset * scale}

    def jump(self):
        """Executes jump or double jump."""
        if self.on_ground:
            self.vy = JUMP_V
            self.on_ground = False
            self.double_jump_available = True
        elif self.wall_state.is_sliding and self.wall_state.execute_jump():
            wall_side = self.wall_state.side
            self.vy = JUMP_V
            if wall_side == 'right':
                self.vx = -WALL_PUSH_BACK_SPEED
            else:
                self.vx = WALL_PUSH_BACK_SPEED
            self.wall_state.stop_slide()
            self.double_jump_available = True
        elif self.double_jump_available:
            self.vy = DOUBLE_JUMP_V
            self.double_jump_available = False

    def _check_wall_collision(self, test_rect, wall_tiles, world_x_offset):
        """Check collision with wall and return side or None"""
        for wall_tile in wall_tiles:
            wall_screen_rect = pygame.Rect(
                wall_tile.x - world_x_offset,
                wall_tile.y,
                wall_tile.width,
                wall_tile.tile_height
            )
            
            if not test_rect.colliderect(wall_screen_rect):
                continue
            
            overlap_left = test_rect.right - wall_screen_rect.left
            overlap_right = wall_screen_rect.right - test_rect.left
            
            if overlap_left < overlap_right:
                return ('right', wall_screen_rect, overlap_left)
            else:
                return ('left', wall_screen_rect, overlap_right)
        
        return (None, None, 0)

    def update(self, platforms, world_x_offset, delta_time, wall_tiles=None, current_run_speed=RUN_SPEED):
        old_hitbox = self.hitbox.copy()
        self.wall_state.update(delta_time)
        
        # Manual movement controls
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.vx = -WALK_SPEED
            self.facing_right = False
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vx = WALK_SPEED
            self.facing_right = True
        else:
            self.vx *= PLAYER_DRAG_COEFFICIENT
            if abs(self.vx) < 0.1:
                self.vx = 0
                
        # Horizontal movement is applied to the hitbox.
        self.hitbox.x += self.vx
        
        # X-Axis Platform collision (Wall blocking)
        for p in platforms:
            # Treat platform as a solid block
            platform_screen_rect = pygame.Rect(p.x - world_x_offset, p.y, p.length, 600) 
            if self.hitbox.colliderect(platform_screen_rect):
                # If player's feet are below the platform's top surface, they hit a wall
                if self.hitbox.bottom > platform_screen_rect.top + 10:
                    if self.vx > 0: # Moving right
                        self.hitbox.right = platform_screen_rect.left
                        self.vx = 0
                    elif self.vx < 0: # Moving left
                        self.hitbox.left = platform_screen_rect.right
                        self.vx = 0

        # Wall collision (Special wall tiles, only if NOT in re-attach cooldown)
        if wall_tiles and self.wall_state.re_attach_cooldown <= 0:
            side, wall_rect, overlap = self._check_wall_collision(self.hitbox, wall_tiles, world_x_offset)
            
            if side:
                if side == 'right' and self.vx >= 0:
                    self.hitbox.right = wall_rect.left
                    self.vx = 0
                    self.wall_state.start_slide('right')
                elif side == 'left' and self.vx <= 0:
                    self.hitbox.left = wall_rect.right
                    self.vx = 0
                    self.wall_state.start_slide('left')
                else:
                    self.wall_state.stop_slide()
            else:
                self.wall_state.stop_slide()
        
        # Vertical movement using float for stability
        if not self.on_ground:
            self.vy += GRAVITY
            
        if self.wall_state.is_sliding and not self.on_ground:
            self.vy = min(self.vy, MAX_WALL_SLIDE_SPEED)
        
        # Update float position and sync to hitbox
        self.pos_y += self.vy
        self.hitbox.y = int(self.pos_y)
        
        # Y-Axis Platform collision (Ground landing)
        self.on_ground = False
        for p in platforms:
            # 1px buffer to prevent horizontal jitter at seams
            top_rect = pygame.Rect(p.x - world_x_offset - 1, p.y, p.length + 2, 20)
            ground_check_rect = pygame.Rect(self.hitbox.x, self.hitbox.y, self.hitbox.width, self.hitbox.height + 2)
            
            if ground_check_rect.colliderect(top_rect) and self.vy >= 0:
                if old_hitbox.bottom <= top_rect.top + 15:
                    self.on_ground = True
                    self.double_jump_available = True
                    self.vy = 0
                    self.hitbox.bottom = top_rect.top
                    self.pos_y = float(self.hitbox.y) # Sync float to snapped position
                    self.wall_state.reset()
                    break
        
        # Check wall time limit
        if self.wall_state.is_sliding and not self.on_ground:
            if self.wall_state.time_elapsed > WALL_CLIMB_TIME_LIMIT:
                return "WALL_TIME_EXCEEDED"
        
        # Animation state selection
        previous_state = self.state
        if self.state == 'death':
            pass # Keep death state
        elif self.wall_state.is_sliding and not self.on_ground:
            self.state = 'climb'
        elif not self.on_ground:
            self.state = 'jump' if self.vy < 0 else 'fall'
        elif abs(self.vx) > 0.1:
            self.state = 'run'
        else:
            self.state = 'idle'
        
        if self.state != previous_state:
            self.current_frame = 0
        
        # Update animation frame
        anim_to_play = self.state
        current_anim = self.animations[anim_to_play]
        self.anim_timer += delta_time * 1000
        
        if self.anim_timer > current_anim['speed']:
            self.anim_timer %= current_anim['speed']
            if anim_to_play in ['jump', 'death'] and self.current_frame < len(current_anim['frames']) - 1:
                self.current_frame += 1
            elif anim_to_play not in ['jump', 'death']:
                self.current_frame = (self.current_frame + 1) % len(current_anim['frames'])
        
        self.image = current_anim['frames'][self.current_frame]
        
        # Flip logic for left/right
        if not self.facing_right:
            self.image = pygame.transform.flip(self.image, True, False)
        
        # Only flip for wall side if we are actually in climb state
        if self.state == 'climb' and self.wall_state.side == 'right':
            self.image = pygame.transform.flip(self.image, True, False)
        
        # Final visual rect positioning
        self.rect = self.image.get_rect()
        self.rect.midbottom = self.hitbox.midbottom
        # Adjust vertical offset from animation config
        self.rect.y += int(current_anim.get('y_offset', 0))
        
        return None


# -------------------------
# Game State Management
# -------------------------
class GameState:
    def __init__(self, game): 
        self.game = game
    def handle_events(self, events): pass
    def update(self, delta_time): pass
    def draw(self, screen): pass
    def enter_state(self): pass
    def exit_state(self): pass

class PlayingState(GameState):
    def __init__(self, game, level_file):
        super().__init__(game)
        self.level_file = level_file
        try: 
            level_data = load_level(self.level_file)
        except Exception as e:
            print(f"✗ Error loading {self.level_file}, falling back to default: {e}")
            level_data = load_level(DEFAULT_LEVEL)
            
        self.is_endless = level_data["is_endless"]
        theme_name = level_data["theme"]
        self.active_segments = deque()
        self.cursor_x = 0
        
        if self.is_endless:
            self.endless_manager = EndlessManager(level_data["patterns"], level_data["spawn_logic"])
            self.world_data = None
            self.level_length = -1
            self.current_run_speed = RUN_SPEED 
        else:
            self.endless_manager = None
            self.world_data = level_data["world"]
            self.level_length = level_data["length"]
            self.current_run_speed = RUN_SPEED
            
        self.background = MultiLayerBackground(PARALLAX_BACKGROUND_CONFIG)
        self.active_theme_tiles = LOADED_THEMES.get(theme_name)
        if not self.active_theme_tiles:
            print(f"⚠️ Theme '{theme_name}' not found! Falling back.")
            self.active_theme_tiles = next(iter(LOADED_THEMES.values())) if LOADED_THEMES else None
            
        self.all_sprites = pygame.sprite.LayeredUpdates()
        self.real_obstacles = pygame.sprite.Group()
        self.fake_obstacles = pygame.sprite.Group()
        
        # Initialize player (position will be set properly in enter_state)
        self.player = Player(PLAYER_TARGET_X, GROUND_Y)
        self.world_x_offset = 0
        self.visible_platforms = [] 
        self.visible_walls = []
        self.visible_wall_tiles = []
        self.platform_surfaces = {} # Cache for pre-rendered platforms

    def enter_state(self):
        self.all_sprites.empty()
        self.real_obstacles.empty()
        self.fake_obstacles.empty()
        
        # Set player's initial state
        self.player.hitbox.x = PLAYER_TARGET_X
        self.player.hitbox.bottom = GROUND_Y # Initial guess, corrected below
        self.player.vy = 0
        self.player.vx = 0
        self.player.on_ground = True
        self.player.state = 'run'
        self.player.current_frame = 0
        self.player.anim_timer = 0.0
        self.player.wall_state.reset()
        self.player.jump_queued = False # Ensure jump buffer is clear on restart
        self.all_sprites.add(self.player)
        
        # Reset health for new run/respawn
        if self.game.player_stats.hp <= 0:
            self.game.player_stats.hp = self.game.player_stats.max_hp
        
        self.world_x_offset = 0
        self.current_run_speed = RUN_SPEED
        self.platform_surfaces.clear() # Clear cache on restart/new level

        if self.is_endless:
            self.active_segments.clear()
            self.cursor_x = 0
            
            # For endless, assume first pattern y or fallback to GROUND_Y
            first_plat_y = GROUND_Y
            if self.endless_manager and self.endless_manager.patterns:
                first_plat_y = self.endless_manager.patterns[0].get("platform_y", GROUND_Y)

            # Set player correctly on the first platform
            self.player.hitbox.bottom = first_plat_y
            self.player.pos_y = float(self.player.hitbox.y)
            print(f"✓ Player placed on starting platform at y={first_plat_y}")

            print(f"💡 Creating a {SAFE_ZONE_DISTANCE}px safe zone for endless mode.")
            safe_zone_config = {"type": "straight", "platform_y": first_plat_y, 
                              "length": SAFE_ZONE_DISTANCE, "obstacles": []}
            safe_segment = TerrainGenerator.straight(self.cursor_x, safe_zone_config)
            self.active_segments.append(safe_segment)
            self.cursor_x += SAFE_ZONE_DISTANCE
            
            while self.cursor_x < self.world_x_offset + SCREEN_W * 1.5:
                self._spawn_next_segment()
        else:
            self.player.hitbox.bottom = GROUND_Y
            self.player.pos_y = float(self.player.hitbox.y)
            self._create_fixed_level()
            
        # CRITICAL: Find the correct starting platform and place the player on it.
        initial_segments = self.active_segments if self.is_endless else self.world_data
        all_platforms = []
        for seg in initial_segments:
            platforms_in_seg = seg.get("platforms", [seg.get("platform")])
            for p in platforms_in_seg:
                if p:
                    all_platforms.append(p)
        
        self.visible_platforms.clear()
        self.visible_platforms.extend(all_platforms)

        player_on_platform = False
        if all_platforms:
            for p in all_platforms:
                if p.x <= self.player.hitbox.centerx < p.x + p.length:
                    self.player.hitbox.bottom = p.y
                    self.player.on_ground = True
                    self.player.vy = 0
                    player_on_platform = True
                    print(f"✓ Player placed on starting platform at y={p.y}")
                    break
            
            if not player_on_platform:
                first_platform_y = all_platforms[0].y
                self.player.hitbox.bottom = first_platform_y
                self.player.on_ground = True
                self.player.vy = 0
                print(f"⚠️ Player not starting over any platform! Placing at first platform's height: y={first_platform_y}")
        else:
            print("⚠️ CRITICAL WARNING: No platforms loaded in the level!")
        
        # Sync rect to final starting position
        self.player.rect.midbottom = self.player.hitbox.midbottom

    def _create_fixed_level(self):
        print("\n🎮 CREATING FIXED LEVEL")
        for seg in self.world_data:
            for ob_data in seg.get("obstacles", []): 
                self._create_obstacle_sprite(ob_data)
        print("="*40 + "\n")

    def _spawn_next_segment(self):
        pattern = self.endless_manager.get_next_pattern()
        if not pattern: return
        
        terrain_type = pattern.get("type", "straight")
        terrain_func = getattr(TerrainGenerator, terrain_type, TerrainGenerator.straight)
        segment = terrain_func(self.cursor_x, pattern)
        for ob_data in segment.get("obstacles", []): 
            self._create_obstacle_sprite(ob_data)
        self.active_segments.append(segment)
        self.cursor_x += segment["length"]
        
    def _create_obstacle_sprite(self, ob_data):
        sprite_type = None
        if ob_data.kind == 'real' and LOADED_ENEMIES: 
            sprite_type = get_random_enemy()
        elif ob_data.kind in ['fake', 'decor'] and LOADED_DECOYS: 
            sprite_type = get_random_decoy()
        obstacle_sprite = ObstacleSprite(ob_data.x, ob_data.y, ob_data.kind, sprite_type=sprite_type)
        if ob_data.kind == 'real': 
            self.real_obstacles.add(obstacle_sprite)
        elif ob_data.kind == 'fake': 
            self.fake_obstacles.add(obstacle_sprite)
        # Decorative objects don't go into interaction groups
        self.all_sprites.add(obstacle_sprite)
        
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.QUIT: 
                self.game.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE: 
                    self.player.jump()
                if event.key == pygame.K_ESCAPE: 
                    self.game.running = False

    def update(self, delta_time):
        if self.player.state == 'death':
            death_anim = self.player.animations['death']
            if self.player.current_frame >= len(death_anim['frames']) - 1:
                pygame.time.delay(500) # Wait a bit
                self.game.flip_state("game_over")
            return
            
        # Auto-scrolling is disabled for RPG mode
        self.current_run_speed = 0
        
        self.visible_platforms.clear()
        self.visible_walls.clear()
        self.visible_wall_tiles.clear()
        
        segments_to_draw = self.active_segments if self.is_endless else self.world_data

        for seg in segments_to_draw:
            for tile in seg.get("wall_tiles", []):
                self.visible_wall_tiles.append(tile)
            
            platforms = seg.get("platforms", [seg.get("platform")])
            for p in platforms:
                if p is None: 
                    continue
                
                # Sync physics length to visual tile multiples to prevent invisible ledges or fake floors
                if self.active_theme_tiles and self.active_theme_tiles.get('wall_top_middle'):
                    tile_size = self.active_theme_tiles.get('wall_top_middle').get_width()
                    if tile_size > 0:
                        num_tiles_x = max(1, round(p.length / tile_size))
                        p.length = num_tiles_x * tile_size

                x_on_screen = p.x - self.world_x_offset
                if x_on_screen + p.length < -200 or x_on_screen > SCREEN_W + 200:
                    continue
                
                self.visible_platforms.append(p)
        
        wall_check = self.player.update(
            self.visible_platforms, 
            self.world_x_offset, 
            delta_time, 
            wall_tiles=self.visible_wall_tiles,
            current_run_speed=self.current_run_speed
        )
        
        # Camera lock logic
        current_screen_x = self.player.hitbox.x
        diff = current_screen_x - PLAYER_TARGET_X
        self.world_x_offset += diff
        self.player.hitbox.x = PLAYER_TARGET_X
        # Do NOT re-sync rect.midbottom here, it's already handled in player.update
        # which now accounts for offsets and camera-synced hitbox.
        # But since we just forced hitbox.x to PLAYER_TARGET_X, we should sync ONE last time
        self.player.rect.midbottom = self.player.hitbox.midbottom
        # Re-apply y_offset after final sync
        current_anim = self.player.animations[self.player.state]
        self.player.rect.y += int(current_anim.get('y_offset', 0))

        if wall_check == "WALL_TIME_EXCEEDED":
            print("Game Over: Wall time exceeded!")
            self.game.flip_state("game_over")
            return
        
        for sprite in self.all_sprites:
            if sprite != self.player:
                sprite.update(self.world_x_offset, delta_time)
        
        real_collisions = pygame.sprite.spritecollide(self.player, self.real_obstacles, False, collided=collide_player_hitbox)
        if real_collisions:
            obs = real_collisions[0]
            print("Player hit enemy! Entering Battle.")
            battle = BattleSystem(self.game.screen, "Monster", self.game.player_stats)
            res_tuple = battle.run()
            res = res_tuple[0] if isinstance(res_tuple, tuple) else res_tuple
            reward = res_tuple[1] if isinstance(res_tuple, tuple) else None
            
            if res == 'WIN':
                obs.kill()
                if reward:
                    if reward['type'] == 'hp': self.game.player_stats.add_max_hp(reward['val'])
                    elif reward['type'] == 'atk': self.game.player_stats.atk_bonus += reward['val']
                    elif reward['type'] == 'card': self.game.player_stats.add_card(reward['val'])
                    print(f"Applied reward: {reward['name']}")
            elif res == 'LOSE':
                self.player.state = 'death'
                self.player.current_frame = 0
            elif res == 'QUIT':
                self.game.flip_state("game_over")
            return

        fake_collisions = pygame.sprite.spritecollide(self.player, self.fake_obstacles, False, collided=collide_player_hitbox)
        if fake_collisions:
            obs = fake_collisions[0]
            print("Player hit ally! Entering Shop.")
            shop = ShopSystem(self.game.screen)
            res = shop.run()
            if res == 'HEALED':
                self.game.player_stats.add_hp(20)
            obs.kill()
            if res == 'QUIT':
                self.game.running = False
            return

        if self.player.hitbox.top > SCREEN_H:
            print("Player fell into the abyss! Game Over.")
            self.game.flip_state("game_over")
            return

        if self.is_endless:
            if self.cursor_x < self.world_x_offset + SCREEN_W * 1.5:
                self._spawn_next_segment()
            if self.active_segments:
                first_seg = self.active_segments[0]
                platforms = first_seg.get("platforms", [first_seg.get("platform")])
                if platforms and platforms[-1] and platforms[-1].x + platforms[-1].length < self.world_x_offset - 200:
                    self.active_segments.popleft()
            for sprite in list(self.all_sprites):
                if not isinstance(sprite, Player) and sprite.world_pos.x < self.world_x_offset - 200:
                    sprite.kill()
        else:
            if self.world_x_offset >= self.level_length - PLAYER_W:
                self.game.game_status = 'COMPLETED'
                self.game.running = False
                return
                    
    def draw(self, screen):
        screen.fill((30, 30, 40))
        if self.background:
            self.background.draw(screen, self.world_x_offset, self.level_length)

        if not self.active_theme_tiles:
            self.draw_platforms_fallback(screen)
            self.all_sprites.draw(screen)
            return

        tile_top_left = self.active_theme_tiles.get('wall_top_left')
        tile_top_middle = self.active_theme_tiles.get('wall_top_middle')
        tile_top_right = self.active_theme_tiles.get('wall_top_right')
        tile_middle_left = self.active_theme_tiles.get('wall_middle_left')
        tile_middle_right = self.active_theme_tiles.get('wall_middle_right')
        tile_fill = self.active_theme_tiles.get('wall_fill') 
        
        essential_tiles = [tile_top_left, tile_top_middle, tile_top_right, 
                          tile_middle_left, tile_middle_right]
        if not all(essential_tiles):
            print("⚠️ Theme is missing essential wall tiles. Using fallback rendering.")
            self.draw_platforms_fallback(screen)
            self.all_sprites.draw(screen)
            return

        tile_size = tile_top_middle.get_width()
        if tile_size == 0: 
            return

        # Draw platforms (OPTIMIZED with Pre-rendering)
        for p in self.visible_platforms:
            x_on_screen = p.x - self.world_x_offset
            
            # Check if we have this platform pre-rendered
            plat_key = (p.length, p.y)
            if plat_key not in self.platform_surfaces:
                # Create a new surface for this platform
                tile_size = tile_top_middle.get_width()
                num_tiles_x = max(1, round(p.length / tile_size))
                height_needed = SCREEN_H - p.y
                num_tiles_y = math.ceil(height_needed / tile_size) + 1
                
                # Create surface exactly matching physics length to avoid fake edges
                actual_w = num_tiles_x * tile_size
                plat_surf = pygame.Surface((actual_w, num_tiles_y * tile_size), pygame.SRCALPHA)
                
                # Draw the top row
                for i in range(num_tiles_x):
                    tile = tile_top_middle
                    if num_tiles_x > 1:
                        if i == 0: tile = tile_top_left
                        elif i == num_tiles_x - 1: tile = tile_top_right
                    if tile: plat_surf.blit(tile, (i * tile_size, 0))
                
                # Draw the fill
                for j in range(1, num_tiles_y):
                    if num_tiles_x > 1:
                        plat_surf.blit(tile_middle_left, (0, j * tile_size))
                        if tile_fill:
                            for i in range(1, num_tiles_x - 1):
                                plat_surf.blit(tile_fill, (i * tile_size, j * tile_size))
                        plat_surf.blit(tile_middle_right, ((num_tiles_x - 1) * tile_size, j * tile_size))
                    else:
                        plat_surf.blit(tile_middle_left, (0, j * tile_size))
                
                # Crop to exact physics length
                final_surf = pygame.Surface((p.length, num_tiles_y * tile_size), pygame.SRCALPHA)
                final_surf.blit(plat_surf, (0, 0))
                self.platform_surfaces[plat_key] = final_surf
            
            # Blit the pre-rendered platform
            screen.blit(self.platform_surfaces[plat_key], (x_on_screen, p.y))

        # Draw wall tiles
        for wall_tile in self.visible_wall_tiles:
            if wall_tile.width != 10: 
                continue

            wall_screen_x = wall_tile.x - self.world_x_offset
            wall_screen_y = wall_tile.y
            
            wall_rect = pygame.Rect(
                wall_screen_x,
                wall_screen_y,
                wall_tile.width,
                wall_tile.tile_height
            )
            
            if wall_rect.right < 0 or wall_rect.left > SCREEN_W:
                continue
            if wall_rect.bottom < 0 or wall_rect.top > SCREEN_H:
                continue
            
            tile_to_use = self.active_theme_tiles.get('wall_middle_left')
            if tile_to_use:
                scaled_tile = pygame.transform.scale(tile_to_use, 
                                                     (wall_tile.width, wall_tile.tile_height))
                screen.blit(scaled_tile, (int(wall_rect.x), int(wall_rect.y)))
            else:
                pygame.draw.rect(screen, (100, 100, 80), wall_rect)

        self.all_sprites.draw(screen)
        
        # DRAW OVERWORLD HUD
        self.game.player_stats.draw_hud(screen, self.game.font)

        # Draw wall climb timer
        if self.player.wall_state.is_sliding:
            wall_time_ratio = self.player.wall_state.time_elapsed / WALL_CLIMB_TIME_LIMIT
            bar_width, bar_height = int(200 * SCALE_X), int(20 * SCALE_Y)
            bar_x, bar_y = SCREEN_W // 2 - bar_width // 2, int(30 * SCALE_Y)
            
            pygame.draw.rect(screen, (50, 50, 50), (bar_x, bar_y, bar_width, bar_height))
            
            color = (0, 200, 0)
            if wall_time_ratio >= WALL_CLIMB_WARNING_TIME / WALL_CLIMB_TIME_LIMIT:
                color = (255, 100, 0) if wall_time_ratio < 0.8 else (255, 0, 0)
            
            current_bar_width = min(bar_width, bar_width * wall_time_ratio)
            pygame.draw.rect(screen, color, (bar_x, bar_y, current_bar_width, bar_height))
            pygame.draw.rect(screen, (200, 200, 200), (bar_x, bar_y, bar_width, bar_height), 2)
            
            font_size = int(16 * SCALE_UNIFORM)
            font = pygame.font.SysFont(None, font_size)
            text = font.render(f"Wall Time: {self.player.wall_state.time_elapsed:.1f}s", 
                             True, (200, 200, 200))
            screen.blit(text, (bar_x, bar_y - int(25 * SCALE_Y)))

    def draw_platforms_fallback(self, screen):
        segments_to_draw = self.active_segments if self.is_endless else self.world_data
        for seg in segments_to_draw:
            platforms = seg.get("platforms", [seg.get("platform")])
            for p in platforms:
                if p is None: continue
                pygame.draw.rect(screen, (80,80,80), 
                               (p.x - self.world_x_offset, p.y, p.length, 6))

class GameOverState(GameState):
    def __init__(self, game):
        super().__init__(game)
        font_size_large = int(60 * SCALE_UNIFORM)
        font_size_small = int(30 * SCALE_UNIFORM)
        self.font_large = pygame.font.SysFont(None, font_size_large)
        self.text_game_over = self.font_large.render("GAME OVER", True, (255, 60, 60))
        self.text_rect = self.text_game_over.get_rect(center=(SCREEN_W/2, SCREEN_H/2 - 40))
        self.font_small = pygame.font.SysFont(None, font_size_small)
        self.instr_text = self.font_small.render("Press ENTER to Restart | ESC for Menu", 
                                                 True, (200, 200, 200))
        self.instr_rect = self.instr_text.get_rect(center=(SCREEN_W/2, SCREEN_H/2 + 20))

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.QUIT: 
                self.game.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN: 
                    self.game.flip_state("playing")
                if event.key == pygame.K_ESCAPE: 
                    self.game.running = False

    def draw(self, screen):
        screen.fill((10, 10, 10))
        screen.blit(self.text_game_over, self.text_rect)
        screen.blit(self.instr_text, self.instr_rect)

class Game:
    def __init__(self, screen, level_file):
        initialize_pygame_and_assets()
        self.screen = screen
        pygame.display.set_caption(f"Parkour Game - {level_file}")
        self.clock = pygame.time.Clock()
        self.running = True
        self.game_status = 'QUIT'
        self.font = pygame.font.SysFont(None, 32)
        
        # PERSISTENT PLAYER STATS
        self.player_stats = PlayerStats()
        
        self.states = {
            "playing": PlayingState(self, level_file), 
            "game_over": GameOverState(self)
        }
        self.current_state_name = "playing"
        self.current_state = self.states[self.current_state_name]
        self.current_state.enter_state()

    def flip_state(self, new_state_name):
        self.current_state.exit_state()
        self.current_state_name = new_state_name
        self.current_state = self.states[self.current_state_name]
        self.current_state.enter_state()

    def run(self):
        last_time = pygame.time.get_ticks()
        while self.running:
            current_time = pygame.time.get_ticks()
            # 🔥 FIX: Use clock.tick to get delta_time for more stable physics
            delta_time = self.clock.tick(FPS) / 1000.0
            
            events = pygame.event.get()
            self.current_state.handle_events(events)
            self.current_state.update(delta_time)
            self.current_state.draw(self.screen)
            pygame.display.flip()
            
        return self.game_status

if __name__ == "__main__":
    print("This file is a module. Run 'game.py' to play.")