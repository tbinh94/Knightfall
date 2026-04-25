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
    # Removed log
except ImportError:
    from config import *
    # Removed log

from assets_manager import LOADED_THEMES, load_assets
from enemy_manager import LOADED_ENEMIES, load_enemies, get_random_enemy, get_enemy_data, get_enemy_config, Enemy, Animation
from decoy_manager import LOADED_DECOYS, load_decoys, get_random_decoy, get_decoy_data, get_decoy_config
from shop_system import ShopSystem
from player_stats import PlayerStats

# Thiết lập giá trị mặc định
if 'PLAYER_TARGET_X' not in globals():
    PLAYER_TARGET_X = SCREEN_W // 3

# -------------------------
# Initialization Helper
# -------------------------
def initialize_pygame_and_assets():
    if not pygame.get_init():
        pygame.init()
        # Removed log
    
    # Print resolution info
    if hasattr(sys.modules.get('config'), 'print_resolution_info'):
        from config import print_resolution_info
        print_resolution_info()
    
    if not LOADED_THEMES: load_assets()
    else: pass # Removed log
    
    if not LOADED_ENEMIES: load_enemies()
    else: pass # Removed log
    
    if not LOADED_DECOYS: load_decoys()
    else: pass # Removed log

    if not LOADED_DECOYS: load_decoys()
    else: pass # Removed log

# -------------------------
# Dialogue & Quest Systems (RPG ELEMENTS)
# -------------------------
class DialogueSystem:
    def __init__(self, screen, font):
        self.screen = screen
        self.font = font
        self.active = False
        self.messages = []
        self.msg_index = 0
        self.callback = None
        
    def start_dialogue(self, messages, callback=None):
        self.messages = messages
        self.msg_index = 0
        self.active = True
        self.callback = callback
        
    def next_msg(self):
        self.msg_index += 1
        if self.msg_index >= len(self.messages):
            self.active = False
            if self.callback: self.callback()
            
    def draw(self):
        if not self.active: return
        # Draw semi-transparent box
        box_rect = pygame.Rect(50, SCREEN_H - 150, SCREEN_W - 100, 120)
        pygame.draw.rect(self.screen, (20, 20, 30, 200), box_rect)
        pygame.draw.rect(self.screen, (255, 215, 0), box_rect, 2)
        
        # Draw current message
        txt = self.font.render(self.messages[self.msg_index], True, (255, 255, 255))
        self.screen.blit(txt, (box_rect.x + 20, box_rect.y + 30))
        
        prompt = self.font.render("Press SPACE to continue...", True, (200, 200, 200))
        self.screen.blit(prompt, (box_rect.right - 250, box_rect.bottom - 40))

class QuestManager:
    def __init__(self):
        self.objectives = [
            {"id": "reach_3k", "desc": "Explore the ruins (Reach 3000m)", "target": 3000, "current": 0, "completed": False}
        ]
    
    def update(self, distance):
        for q in self.objectives:
            if not q["completed"]:
                q["current"] = distance
                if q["current"] >= q["target"]:
                    q["completed"] = True
                pass # Removed log

    def draw_hud(self, screen, font):
        y = 120
        for q in self.objectives:
            color = (100, 255, 100) if q["completed"] else (255, 255, 255)
            status = "[DONE]" if q["completed"] else f"({int(q['current'])}/{q['target']}m)"
            txt = font.render(f"Quest: {q['desc']} {status}", True, color)
            screen.blit(txt, (20, y))
            y += 30

# -------------------------
# Background Systems (MOVED TO background.py)
# -------------------------
try:
    from background import GothicBackground, ForestBackground
except ImportError:
    # Fallback if file not found during development
    class GothicBackground:
        def __init__(self, *args): pass
        def draw(self, screen, *args): screen.fill((20, 20, 30))
    class ForestBackground:
        def __init__(self, *args): pass
        def draw(self, screen, *args): screen.fill((10, 20, 10))


# -------------------------
# Game Entities (RESPONSIVE)
# -------------------------
class Obstacle:
    def __init__(self, x, y, w=30, h=50, kind="real", sprite_type=None, text=None):
        self.x = x
        self.y = y
        # Apply responsive scaling
        scale = SCALE_UNIFORM if 'SCALE_UNIFORM' in globals() else 1.0
        self.w = int(w * scale)
        self.h = int(h * scale)
        self.kind = kind
        self.sprite_type = sprite_type
        self.text = text

        
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
        if plat_y == "ground": plat_y = GROUND_Y
        length = config.get("length", 500)
        platform = Platform(cursor_x, plat_y, length)
        obstacles = []
        for ob in config.get("obstacles", []):
            ox = cursor_x + ob["x"]
            # Fix KeyError: use .get("y", "ground") to handle concise JSON
            ob_y = ob.get("y", "ground")
            oy = plat_y if ob_y == "ground" else plat_y + ob_y
            kind = ob.get("kind", "real")
            sprite_type = ob.get("type")
            text = ob.get("text")
            obstacles.append(Obstacle(ox, oy, kind=kind, sprite_type=sprite_type, text=text))

        return {"type": "straight", "platform": platform, "obstacles": obstacles, "length": length}

    @staticmethod
    def stairs_up(cursor_x, config):
        # Trust the start_y from the JSON file.
        start_y = config.get("start_y", GROUND_Y)
        if start_y == "ground": start_y = GROUND_Y
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
                sprite_type = ob_config.get("type")
                text = ob_config.get("text")
                obstacles.append(Obstacle(ox, oy, kind=kind, sprite_type=sprite_type, text=text))

        return {"type": "stairs_up", "platforms": platforms, "obstacles": obstacles, "length": total_length}

    @staticmethod
    def stairs_down(cursor_x, config):
        # Trust the start_y from the JSON file.
        start_y = config.get("start_y", GROUND_Y)
        if start_y == "ground": start_y = GROUND_Y
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
                sprite_type = ob_config.get("type")
                text = ob_config.get("text")
                obstacles.append(Obstacle(ox, oy, kind=kind, sprite_type=sprite_type, text=text))

        return {"type": "stairs_down", "platforms": platforms, "obstacles": obstacles, "length": total_length}

    @staticmethod
    def gap(cursor_x, config):
        length = config.get("length", 500)
        # Trust the base_y from the JSON file.
        base_y = config.get("base_y", GROUND_Y)
        if base_y == "ground": base_y = GROUND_Y
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
                sprite_type = ob_config.get("type")
                text = ob_config.get("text")
                obstacles.append(Obstacle(ox, oy, kind=kind, sprite_type=sprite_type, text=text))
            elif "x" in ob_config and "y" in ob_config:
                y_val = ob_config["y"]
                oy = None
                if isinstance(y_val, (int, float)): oy = base_y - y_val
                elif y_val == "midair": oy = base_y - 150
                if oy is not None:
                    ox = cursor_x + ob_config["x"]
                    kind = ob_config.get("kind", "real")
                    sprite_type = ob_config.get("type")
                    obstacles.append(Obstacle(ox, oy, kind=kind, sprite_type=sprite_type))
        return {"type": "gap", "platforms": platforms, "obstacles": obstacles, "length": length}
    
    @staticmethod
    def wall_jump(cursor_x, config):
        wall_height = config.get("height", 280) # Increased to 280 for better challenge and parkour feel
        shaft_width = config.get("shaft_width", 150)
        # Trust the entry_y from the JSON file.
        entry_y = config.get("entry_y", GROUND_Y)
        if entry_y == "ground": entry_y = GROUND_Y
        
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
        # Removed log
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
        # Removed log
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
    player_hitbox = player.hitbox.copy()
    
    # 🔥 TĂNG TẦM ĐÁNH KHI ĐANG ATTACK
    if player.is_attacking:
        if player.facing_right:
            player_hitbox.width += 50
        else:
            player_hitbox.x -= 50
            player_hitbox.width += 50
            
    # Deflate enemy hitbox to be more fair
    obstacle_rect = obstacle_sprite.image.get_rect(midbottom=obstacle_sprite.rect.midbottom)
    shrink_x = obstacle_rect.width * 0.2
    shrink_y = obstacle_rect.height * 0.1
    enemy_hitbox = obstacle_rect.inflate(-shrink_x, -shrink_y)
    
    return player_hitbox.colliderect(enemy_hitbox)

class ObstacleSprite(Enemy):
    def __init__(self, world_x, y, kind='real', sprite_type=None, lore_text=None):
        # Layering: 0 = decor (background), 1 = enemies/allies, 2 = player
        self._layer = 0 if kind == 'decor' else 1
        self.kind = kind
        self.sprite_type = sprite_type
        self.lore_text = lore_text
        self.is_used = False 
        
        # Get sprite data
        sprite_data, sprite_config = (None, None)
        if self.sprite_type:
            if self.kind == 'real':
                sprite_data = get_enemy_data(self.sprite_type)
                sprite_config = get_enemy_config(self.sprite_type)
            elif self.kind in ['fake', 'decor']:
                sprite_data = get_decoy_data(self.sprite_type)
                sprite_config = get_decoy_config(self.sprite_type)

        if sprite_data and self.kind == 'real':
            # Initialize as Enemy
            frames_data = sprite_data.get('frames_data', sprite_data.get('frames'))
            super().__init__(world_x, y, self.sprite_type, frames_data)
            
            # Apply scaling from config
            if sprite_config:
                self.scale = sprite_config.get('scale', 1.0)
                y_offset = sprite_config.get('y_offset', 0)
                self.world_pos.y += y_offset
                self.world_pos.x += 15
                
                # Apply scaling to all animation frames
                for state in self.animations:
                    anim = self.animations[state]
                    scaled_frames = []
                    for frame in anim.frames:
                        w, h = frame.get_size()
                        scaled_frames.append(pygame.transform.scale(frame, (int(w * self.scale), int(h * self.scale))))
                    anim.frames = scaled_frames
            
            self.hp = 30
            self.max_hp = 30
        else:
            # Fallback for decoys or simple obstacles
            pygame.sprite.Sprite.__init__(self)
            self.world_pos = pygame.math.Vector2(world_x, y)
            self.animations = {}
            self.state = "idle"
            
            if sprite_data and sprite_config:
                frames = sprite_data.get('frames', [])
                scale = sprite_config.get('scale', 1.0)
                y_offset = sprite_config.get('y_offset', 0)
                self.world_pos.y += y_offset
                self.world_pos.x += 15
                
                scaled_frames = []
                for frame in frames:
                    w, h = frame.get_size()
                    scaled_frames.append(pygame.transform.scale(frame, (int(w * scale), int(h * scale))))
                
                self.animations["idle"] = Animation(scaled_frames, speed=sprite_config.get('animation_speed', 150)/1000.0)
                self.image = self.animations["idle"].get_frame()
            else:
                width, height = (30, 50)
                color = (200, 40, 40) if kind == 'real' else (120, 120, 220)
                self.image = pygame.Surface([width, height])
                self.image.fill(color)
                self.animations["idle"] = Animation([self.image])
            
            self.rect = self.image.get_rect()
            self.hp = 0
            
        self.rect.midbottom = (self.world_pos.x, self.world_pos.y)

    def update(self, world_x_offset, delta_time, player_pos=None):
        if self.kind == 'real' and hasattr(self, 'enemy_type'):
            # Use Enemy update for AI and multi-state animations
            super().update(world_x_offset, delta_time, player_pos)
        else:
            # Simple update for decoys
            if "idle" in self.animations:
                self.animations["idle"].update(delta_time)
                self.image = self.animations["idle"].get_frame()
            
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
        self.is_hanging = False
        self.hanging_side = None # 'left' or 'right'
        self.hanging_y = 0
        self.is_crouching = False
        self.is_attacking = False
        self.attack_timer = 0
        self.attack_duration = 400 # ms
        self.attack_combo = 0
        
        # Dash Mechanic
        self.dash_cooldown = 0
        self.dash_timer = 0
        self.is_dashing = False
        self.can_dash = False # Unlocked after Level 1 Boss
        
        # Stomp Attack Variables

        self.is_stomping = False
        self.stomp_phase = None # 'windup', 'dive', 'recovery'
        self.stomp_timer = 0.0
        self.stomp_cooldown_timer = 0.0
        
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
            pass # Removed log
            placeholder = pygame.Surface((int(frame_w*scale), int(frame_h*scale)), pygame.SRCALPHA)
            placeholder.fill((255, 0, 255, 128))
            frames.append(placeholder)
        return {'frames': frames, 'speed': anim_speed, 'y_offset': y_offset * scale}

    def jump(self):
        """Executes jump or double jump."""
        if self.is_hanging:
            # Jump away from the wall
            self.vy = JUMP_V
            if self.hanging_side == 'right':
                self.vx = -WALL_PUSH_BACK_SPEED
            else:
                self.vx = WALL_PUSH_BACK_SPEED
            self.is_hanging = False
            self.on_ground = False
            self.double_jump_available = True
            return

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

    def dash(self):
        """Executes dash if unlocked and off cooldown."""
        if self.can_dash and self.dash_cooldown <= 0 and not self.is_dashing:
            self.is_dashing = True
            self.dash_timer = 200 # Dash duration in ms
            self.dash_cooldown = 800 # Dash cooldown in ms
            # Speed boost in the facing direction
            dash_speed = WALK_SPEED * 3
            self.vx = dash_speed if self.facing_right else -dash_speed
            self.vy = 0 # Freeze vertical movement during dash
            self.state = 'run' # Use run animation for now
            return True
        return False


    def attack(self):
        """Triggers an attack animation and state."""
        if not self.is_attacking and not self.wall_state.is_sliding:
            self.is_attacking = True
            self.current_frame = 0
            self.anim_timer = 0
            
            if not self.on_ground:
                self.state = 'attack_from_air'
                self.attack_timer = 500 # Slightly longer for air
            else:
                # Cycle through attacks or pick random
                self.attack_combo = (self.attack_combo % 3) + 1
                self.state = f'attack{self.attack_combo}'
                self.attack_timer = 400
            return True
        return False

    def stomp(self):
        """Triggers the Air Attack - Stomp if preconditions are met."""
        if not self.on_ground and not self.is_stomping and self.stomp_cooldown_timer <= 0:
            if self.vy >= -2: # Falling or at apex
                self.is_stomping = True
                self.stomp_phase = 'windup'
                self.stomp_timer = STOMP_WINDUP_TIME
                self.state = 'jump_attack_start'
                self.current_frame = 0
                self.anim_timer = 0
                self.vx = 0
                return True
        return False

    def _get_stomp_hitbox(self, world_x_offset):
        """Returns the current stomp hitbox for collision detection."""
        if self.is_stomping and self.stomp_phase == 'dive':
            # Rectangle directly under feet
            # Use screen coordinates to match obstacle sprites
            foot_x = self.hitbox.centerx
            foot_y = self.hitbox.bottom
            w = self.hitbox.width
            h = int(40 * SCALE_UNIFORM)
            return pygame.Rect(foot_x - w//2, foot_y - 10, w, h)
        return None

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

    def update(self, platforms, world_x_offset, delta_time, wall_tiles=None, current_run_speed=0):
        old_hitbox = self.hitbox.copy()
        self.wall_state.update(delta_time)
        player_on_platform = False
        
        if self.stomp_cooldown_timer > 0:
            self.stomp_cooldown_timer -= delta_time * 1000
            
        # Manual movement controls
        keys = pygame.key.get_pressed()
        # Dash Update
        if self.is_dashing:
            self.dash_timer -= delta_time * 1000
            self.vx = (WALK_SPEED * 3) if self.facing_right else -(WALK_SPEED * 3)
            self.vy = 0 # No gravity during dash
            if self.dash_timer <= 0:
                self.is_dashing = False
                self.vx = 0
        
        if self.dash_cooldown > 0:
            self.dash_cooldown -= delta_time * 1000

        if not self.is_attacking and not self.is_stomping and not self.is_dashing:
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                self.vx = -WALK_SPEED
                self.facing_right = False
            elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.vx = WALK_SPEED
                self.facing_right = True
            else:
                self.vx *= PLAYER_DRAG_COEFFICIENT
        elif not self.is_dashing:
            # Cannot move horizontally while attacking or stomping
            self.vx *= PLAYER_DRAG_COEFFICIENT

        
        if abs(self.vx) < 0.1:
            self.vx = 0
                
        # Crouch logic
        self.is_crouching = False
        if self.on_ground and (keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL]):
            self.is_crouching = True
            self.vx = 0 # Cannot move while crouching
            
        # Release hanging if moving away
        if self.is_hanging:
            if self.hanging_side == 'right' and (keys[pygame.K_LEFT] or keys[pygame.K_a]):
                self.is_hanging = False
            elif self.hanging_side == 'left' and (keys[pygame.K_RIGHT] or keys[pygame.K_d]):
                self.is_hanging = False
                
        # Horizontal movement is applied to the hitbox.
        if not self.is_hanging:
            self.hitbox.x += self.vx
        
        # X-Axis Platform collision (Wall blocking)
        for p in platforms:
            # Treat platform as a solid block
            # Narrow the collision box slightly (5px on each side) to prevent snagging on edges
            platform_screen_rect = pygame.Rect(p.x - world_x_offset + 5, p.y, p.length - 10, 600) 
            if self.hitbox.colliderect(platform_screen_rect):
                # Only block if we are truly hitting the side (40px buffer)
                if self.hitbox.bottom > platform_screen_rect.top + 40:
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
        
        # Hanging logic
        if not self.on_ground and not self.is_hanging and self.vy >= -2: # Only hang when falling or peak
            for p in platforms:
                platform_rect = pygame.Rect(p.x - world_x_offset, p.y, p.length, 20)
                # Check if player hands are near the top edge
                # Left side of platform
                if self.facing_right and abs(self.hitbox.right - platform_rect.left) < 15:
                    if abs(self.hitbox.top - platform_rect.top) < 25:
                        self.is_hanging = True
                        self.hanging_side = 'right' # Hanging on the right wall (facing it)
                        # Align player side with the edge (slight overlap) and drop body slightly
                        self.hitbox.right = platform_rect.left + 5
                        self.hitbox.top = platform_rect.top + 12
                        self.vy = 0
                        self.vx = 0
                        self.pos_y = float(self.hitbox.y)
                        break
                # Right side of platform
                elif not self.facing_right and abs(self.hitbox.left - platform_rect.right) < 15:
                    if abs(self.hitbox.top - platform_rect.top) < 25:
                        self.is_hanging = True
                        self.hanging_side = 'left'
                        # Align player side with the edge (slight overlap) and drop body slightly
                        self.hitbox.left = platform_rect.right - 5
                        self.hitbox.top = platform_rect.top + 12
                        self.vy = 0
                        self.vx = 0
                        self.pos_y = float(self.hitbox.y)
                        break

        # Vertical movement using float for stability
        if not self.on_ground and not self.is_hanging:
            grav = GRAVITY
            if self.is_stomping:
                if self.stomp_phase == 'windup':
                    grav *= STOMP_WINDUP_GRAVITY_MULT
                elif self.stomp_phase == 'dive':
                    grav *= STOMP_GRAVITY_MULT
                    self.vy = STOMP_DIVE_SPEED
            
            self.vy += grav
            
        if self.wall_state.is_sliding and not self.on_ground:
            self.vy = min(self.vy, MAX_WALL_SLIDE_SPEED)
        
        # Stomp phase transitions
        if self.is_stomping:
            self.stomp_timer -= delta_time * 1000
            if self.stomp_phase == 'windup' and self.stomp_timer <= 0:
                self.stomp_phase = 'dive'
                self.state = 'stomp_down'
                self.current_frame = 0
            elif self.stomp_phase == 'recovery' and self.stomp_timer <= 0:
                self.is_stomping = False
                self.stomp_phase = None
                self.stomp_cooldown_timer = STOMP_COOLDOWN
        
        # Update float position and sync to hitbox
        self.pos_y += self.vy
        self.hitbox.y = int(self.pos_y)
        
        # Y-Axis Platform collision (Ground landing) - Disabled while hanging to prevent "flicking" to top
        if not self.is_hanging:
            self.on_ground = False
            for p in platforms:
                # 1px buffer to prevent horizontal jitter at seams
                top_rect = pygame.Rect(p.x - world_x_offset - 1, p.y, p.length + 2, 20)
                ground_check_rect = pygame.Rect(self.hitbox.x, self.hitbox.y, self.hitbox.width, self.hitbox.height + 2)
                
                if ground_check_rect.colliderect(top_rect) and self.vy >= 0:
                    # Increase buffer to 45px to allow walking up stairs (40px height) without jumping
                    if old_hitbox.bottom <= top_rect.top + 45:
                        self.on_ground = True
                        self.double_jump_available = True
                        self.vy = 0
                        self.hitbox.bottom = top_rect.top
                        self.pos_y = float(self.hitbox.y) # Sync float to snapped position
                        self.wall_state.reset()
                        
                        # If landed while performing air attack, end the attack
                        if self.is_attacking and self.state == 'attack_from_air':
                            self.is_attacking = False
                            self.attack_timer = 0
                            self.state = 'idle'
                            
                        # Stomp Impact Logic
                        if self.is_stomping and self.stomp_phase == 'dive':
                            self.stomp_phase = 'recovery'
                            self.stomp_timer = STOMP_RECOVERY_TIME
                            self.state = 'land_heavy'
                            self.current_frame = 0
                            self.vx = 0
                            # Impact signal return
                            player_on_platform = "STOMP_IMPACT"
                        break
        else:
            self.on_ground = False
        
        # Check wall time limit
        if self.wall_state.is_sliding and not self.on_ground:
            if self.wall_state.time_elapsed > WALL_CLIMB_TIME_LIMIT:
                return "WALL_TIME_EXCEEDED"
        
        if player_on_platform == "STOMP_IMPACT":
            return "STOMP_IMPACT"
        
        # Animation state selection
        previous_state = self.state
        if self.state == 'death':
            pass # Keep death state
        elif self.is_attacking or self.is_stomping:
            # Keep the attack state set by attack() or stomp()
            pass
        elif self.is_hanging:
            self.state = 'hanging'
        elif self.wall_state.is_sliding and not self.on_ground:
            self.state = 'climb'
        elif not self.on_ground:
            self.state = 'jump' if self.vy < 0 else 'fall'
        elif self.is_crouching:
            self.state = 'crouch'
        elif abs(self.vx) > 0.1:
            self.state = 'run'
        else:
            self.state = 'idle'
        
        # Handle attack timer
        if self.is_attacking:
            self.attack_timer -= delta_time * 1000
            if self.attack_timer <= 0:
                self.is_attacking = False
                # Force state update next frame
                self.state = 'run' if abs(self.vx) > 0.1 else 'idle'
        
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
                # If finished a one-shot animation
                if self.current_frame == 0 and self.is_attacking:
                    self.is_attacking = False
        
        self.image = current_anim['frames'][self.current_frame]
        
        # Flip logic for left/right
        if self.state in ['climb', 'hanging']:
            # Face the wall
            side = self.wall_state.side if self.state == 'climb' else self.hanging_side
            if side == 'left':
                self.image = pygame.transform.flip(self.image, True, False)
        else:
            if not self.facing_right:
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
            pass # Removed log
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
            
        # Background selection based on theme
        if theme_name in ["dark_forest", "forest", "nature"]:
            self.background = ForestBackground()
        else:
            self.background = GothicBackground()

        self.active_theme_tiles = LOADED_THEMES.get(theme_name)
        if not self.active_theme_tiles:
            pass # Removed log
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
        
        self.dialogue = DialogueSystem(self.game.screen, pygame.font.SysFont(None, 32))
        self.quests = QuestManager()
        
        # Level 1 Specific State
        self.visibility_mult = 1.0
        self.boss_active = False
        self.boss_instance = None
        self.level_phase = 1 # 1: Tutorial, 2: Explore, 3: Danger, 4: Boss


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
                if first_plat_y == "ground": first_plat_y = GROUND_Y

            # Set player correctly on the first platform
            self.player.hitbox.bottom = first_plat_y
            self.player.pos_y = float(self.player.hitbox.y)
            pass # Removed log

            pass # Removed log
            # Add some ruins to the safe zone so it's not empty
            safe_obstacles = [{"x": i, "kind": "decor"} for i in range(100, SAFE_ZONE_DISTANCE, 200)]
            safe_zone_config = {"type": "straight", "platform_y": first_plat_y, 
                              "length": SAFE_ZONE_DISTANCE, "obstacles": safe_obstacles}
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
                    self.player.pos_y = float(self.player.hitbox.y)
                    self.player.on_ground = True
                    self.player.vy = 0
                    player_on_platform = True
                    break # Found the correct platform
            
            if not player_on_platform:
                first_platform_y = all_platforms[0].y
                self.player.hitbox.bottom = first_platform_y
                self.player.pos_y = float(self.player.hitbox.y)
                self.player.on_ground = True
                self.player.vy = 0

            pass # Removed log
        else:
            pass # Removed log
        
        # Sync rect to final starting position
        self.player.rect.midbottom = self.player.hitbox.midbottom

    def _create_fixed_level(self):
        pass # Removed log
        for seg in self.world_data:
            for ob_data in seg.get("obstacles", []): 
                self._create_obstacle_sprite(ob_data)
        pass # Removed log

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
        sprite_type = ob_data.sprite_type
        if not sprite_type:
            if ob_data.kind == 'real' and LOADED_ENEMIES: 
                sprite_type = get_random_enemy()
            elif ob_data.kind in ['fake', 'decor'] and LOADED_DECOYS: 
                # Differentiate between Shrines and Merchants for 'fake' kind
                if ob_data.kind == 'fake':
                    # Only spawn functional NPCs after a certain distance
                    lore_text = ob_data.get("text")
                    if ob_data.x > 400:
                        rand_val = random.random()
                        if rand_val < 0.20:
                            sprite_type = 'pillar'
                        elif rand_val < 0.40: 
                            sprite_type = 'warrior'
                        else:
                            sprite_type = 'wall'
                    else:
                        sprite_type = 'wall'
                else:
                    # For decor, pick anything EXCEPT pillar and warrior to avoid confusion
                    available = [k for k in LOADED_DECOYS.keys() if k not in ['pillar', 'warrior']]
                    if available:
                        sprite_type = random.choice(available)
                    else:
                        sprite_type = get_random_decoy()
                
        obstacle_sprite = ObstacleSprite(ob_data.x, ob_data.y, ob_data.kind, sprite_type=sprite_type, lore_text=ob_data.text)
        if ob_data.kind == 'real': 
            self.real_obstacles.add(obstacle_sprite)
        # If it's a pillar or warrior, it MUST be interactive, regardless of original kind
        elif ob_data.kind == 'fake' or sprite_type in ['pillar', 'warrior']: 
            self.fake_obstacles.add(obstacle_sprite)
        # Decorative objects don't go into interaction groups
        self.all_sprites.add(obstacle_sprite)
        
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.QUIT: 
                self.game.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE: 
                    if self.dialogue.active:
                        self.dialogue.next_msg()
                    else:
                        self.player.jump()
                if event.key == pygame.K_f or event.key == pygame.K_j:
                    if not self.player.stomp():
                        self.player.attack()
                if event.key == pygame.K_s or event.key == pygame.K_DOWN:
                    if not self.player.on_ground:
                        self.player.stomp()
                if event.key == pygame.K_ESCAPE: 
                    self.game.running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: # Left Click
                    self.player.attack()

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
        
        # Check stomp hitbox against enemies
        stomp_hitbox = self.player._get_stomp_hitbox(self.world_x_offset)
        if stomp_hitbox:
            for obs in self.real_obstacles:
                if stomp_hitbox.colliderect(obs.rect):
                    # HIT ENEMY WITH STOMP
                    self.game.player_stats.gold += 15
                    obs.kill()
                    # Bounce player
                    self.player.vy = STOMP_BOUNCE_V
                    self.player.is_stomping = False
                    self.player.stomp_phase = None
                    self.player.stomp_cooldown_timer = STOMP_COOLDOWN
                    # Could add impact effect here
                    break

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
            pass # Removed log
            self.game.flip_state("game_over")
            return
        
        for sprite in self.all_sprites:
            if sprite != self.player:
                if isinstance(sprite, ObstacleSprite):
                    sprite.update(self.world_x_offset, delta_time, player_pos=self.player.hitbox)
                else:
                    sprite.update(self.world_x_offset, delta_time)
        
        real_collisions = pygame.sprite.spritecollide(self.player, self.real_obstacles, False, collided=collide_player_hitbox)
        if real_collisions and self.player.state != 'death':
            obs = real_collisions[0]
            # IF ATTACKING OR STOMPING, DAMAGE ENEMY
            if self.player.is_attacking or (self.player.is_stomping and self.player.stomp_phase == 'dive'):
                if hasattr(obs, 'hp'):
                    obs.hp -= 20 # Player damage
                    if obs.hp <= 0:
                        obs.kill()
                        self.game.player_stats.gold += 50
                else:
                    self.game.player_stats.gold += 10
                    obs.kill()
                return
                
            pass # Removed log
            # Take direct damage instead of entering card battle
            self.game.player_stats.hp -= 10
            if self.game.player_stats.hp <= 0:
                self.player.state = 'death'
                self.player.current_frame = 0
                self.player.vx = 0 # Stop movement on death
            else:
                # Knockback or temporary invincibility could be added here
                self.player.vx = -10
                self.player.vy = -5
                self.player.on_ground = False
                obs.kill() # Remove enemy after collision
            return

        # Interaction logic (Press E)
        self.interaction_prompt = None
        keys = pygame.key.get_pressed()
        
        # Create an interaction zone around the player
        interaction_zone = self.player.hitbox.inflate(100, 50)
        
        # Check proximity to fake obstacles (allies/shrines)
        for obs in self.fake_obstacles:
            # Use rect collision for more reliable interaction with large sprites
            if interaction_zone.colliderect(obs.rect):
                if obs.sprite_type == 'pillar' and not obs.is_used:
                    self.interaction_prompt = "Press E to Heal at Shrine"
                    if keys[pygame.K_e]:
                        heal_amount = self.game.player_stats.hp * 0.2
                        self.game.player_stats.add_hp(heal_amount)
                        # Removed log
                        obs.is_used = True # Keep sprite but disable interaction
                        break
                elif obs.sprite_type == 'warrior':
                    self.interaction_prompt = "Press E to Trade with Warrior"
                    if keys[pygame.K_e]:
                        # Dialogue before shop
                        msgs = [
                            "Warrior: Halt, traveler!",
                            "Warrior: I've found some rare artifacts in these ruins.",
                            "Warrior: Do you have gold to trade?"
                        ]
                        def open_shop():
                            shop = ShopSystem(self.game.screen, self.game.player_stats)
                            res = shop.run()
                            obs.kill()
                            if res == 'QUIT': self.game.running = False
                            
                        self.dialogue.start_dialogue(msgs, open_shop)
                        break
                
                # Level 1 Specific Lore Popups
                if obs.sprite_type == 'lore_popup' and not obs.is_used:
                    lore_text = getattr(obs, 'lore_text', "Use A/D to move, Space to Jump, J to Attack")
                    self.interaction_prompt = f"Lore: {lore_text}"
                    # Auto-trigger or just show
                
                if obs.sprite_type == 'dead_knight' and not obs.is_used:
                    self.interaction_prompt = "Examine Fallen Knight (E)"
                    if keys[pygame.K_e]:
                        self.dialogue.start_dialogue(["A fallen warrior... his armor is rusted through.", "\"They came from beneath...\" is carved into the hilt of his sword."], None)
                        obs.is_used = True

                if obs.sprite_type == 'boss_trigger' and not self.boss_active:
                    self.boss_active = True
                    self.dialogue.start_dialogue(["The ground tremors...", "The Rooted Knight rises from the decay!"], None)
                    # Find the boss obstacle and turn it into the active boss
                    for boss_obs in self.real_obstacles:
                        if boss_obs.sprite_type == 'rooted_knight_boss':
                            self.boss_instance = boss_obs
                            # Boost boss stats
                            self.boss_instance.hp = 100
                            self.boss_instance.max_hp = 100
                            break



        # Update systems
        self.quests.update(self.world_x_offset)

        # Death transition to Game Over
        if self.player.state == 'death':
            death_anim = self.player.animations['death']
            if self.player.current_frame >= len(death_anim['frames']) - 1:
                # Wait a small delay then Game Over
                self.game.flip_state("game_over")
                return

        # -------------------------
        # LEVEL PHASE & VISIBILITY LOGIC
        # -------------------------
        if self.world_x_offset > 2500:
            self.level_phase = 4
        elif self.world_x_offset > 1500:
            self.level_phase = 3
            # Dim lights gradually in Phase 3
            target_vis = 0.4
            if self.visibility_mult > target_vis:
                self.visibility_mult -= delta_time * 0.1
        elif self.world_x_offset > 500:
            self.level_phase = 2

        # Handle keyboard input for Dash (LSHIFT or K)
        if keys[pygame.K_LSHIFT] or keys[pygame.K_k]:
            self.player.dash()

        if self.boss_active and self.boss_instance:
            if not self.boss_instance.alive():
                self.boss_active = False
                self.player.can_dash = True # REWARD!
                self.dialogue.start_dialogue(["The Rooted Knight has been cleansed.", "You feel a surge of energy! Skill Unlocked: DASH (LSHIFT)"], None)
            else:
                # Basic Boss AI: Move towards player if not attacking
                dist = self.boss_instance.world_pos.x - (self.world_x_offset + self.player.hitbox.x)
                if abs(dist) > 100:
                    self.boss_instance.world_pos.x -= (20 * delta_time) if dist > 0 else -(20 * delta_time)
                
                # Randomly spawn root spikes if player is near
                if abs(dist) < 400 and random.random() < 0.01:
                    spike_x = self.world_x_offset + self.player.hitbox.x + random.randint(-100, 100)
                    spike = ObstacleSprite(spike_x, GROUND_Y, kind='real', sprite_type='spiked_barricade')
                    self.real_obstacles.add(spike)
                    self.all_sprites.add(spike)

        # Update and cull segments

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
        # Apply visibility darkening
        bg_surface = pygame.Surface((SCREEN_W, SCREEN_H))
        bg_surface.fill((30, 30, 40))
        
        if self.background:
            self.background.draw(bg_surface, self.world_x_offset, self.level_length)

        # Darken the background based on phase
        if self.visibility_mult < 1.0:
            dark_overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            alpha = int(255 * (1.0 - self.visibility_mult))
            dark_overlay.fill((0, 0, 0, alpha))
            bg_surface.blit(dark_overlay, (0, 0))

        screen.blit(bg_surface, (0, 0))


        if not self.active_theme_tiles:
            self.draw_platforms_fallback(screen)
            self.all_sprites.draw(screen)
            return

        # OVERRIDE: Use Gothic Tileset for Platforms if available
        if hasattr(self.background, 'tiles') and self.background.tiles:
            # Map Gothic Tileset (4x4) to platform roles
            # Row 4 [3] is Floor, Row 3 [2] is Wall
            g_tiles = self.background.tiles
            tile_top_left = pygame.transform.scale(g_tiles[3][0], (32, 32))
            tile_top_middle = pygame.transform.scale(g_tiles[3][1], (32, 32))
            tile_top_right = pygame.transform.scale(g_tiles[3][2], (32, 32))
            tile_middle_left = pygame.transform.scale(g_tiles[2][0], (32, 32))
            tile_middle_right = pygame.transform.scale(g_tiles[2][2], (32, 32))
            tile_fill = pygame.transform.scale(g_tiles[2][1], (32, 32))
        else:
            tile_top_left = self.active_theme_tiles.get('wall_top_left')
            tile_top_middle = self.active_theme_tiles.get('wall_top_middle')
            tile_top_right = self.active_theme_tiles.get('wall_top_right')
            tile_middle_left = self.active_theme_tiles.get('wall_middle_left')
            tile_middle_right = self.active_theme_tiles.get('wall_middle_right')
            tile_fill = self.active_theme_tiles.get('wall_fill') 
        
        essential_tiles = [tile_top_left, tile_top_middle, tile_top_right, 
                          tile_middle_left, tile_middle_right]
        if not all(essential_tiles):
            self.draw_platforms_fallback(screen)
            self.all_sprites.draw(screen)
            # DRAW HUD EVEN IF TILES FAIL
            self.game.player_stats.draw_hud(screen, self.game.font)
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
                # Optimization: if p.length is within 5px of tile boundary, just use full tile
                final_w = p.length
                final_surf = pygame.Surface((final_w, num_tiles_y * tile_size), pygame.SRCALPHA)
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

        # Draw Quest HUD
        self.quests.draw_hud(self.game.screen, self.game.font)
        
        # Draw Dialogue
        self.dialogue.draw()
        
        # Draw interaction prompt
        if self.interaction_prompt and not self.dialogue.active:
            prompt_text = self.game.font.render(self.interaction_prompt, True, (255, 255, 255))
            # Draw above player
            prompt_x = self.player.rect.centerx - prompt_text.get_width() // 2
            prompt_y = self.player.rect.top - 60
            
            # Draw a nice background box for the prompt
            bg_rect = pygame.Rect(prompt_x - 10, prompt_y - 5, prompt_text.get_width() + 20, prompt_text.get_height() + 10)
            pygame.draw.rect(screen, (0, 0, 0, 180), bg_rect, border_radius=5)
            pygame.draw.rect(screen, (255, 255, 100), bg_rect, 2, border_radius=5)
            
            screen.blit(prompt_text, (prompt_x, prompt_y))

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

