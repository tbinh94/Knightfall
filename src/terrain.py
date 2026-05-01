import pygame
import os
import json
import random
from config import SCREEN_W, SCREEN_H, GROUND_Y, CONSECUTIVE_WALL_JUMP_COOLDOWN, SAFE_ZONE_DISTANCE, SCALE_UNIFORM
from enemy_manager import Enemy, Animation, get_enemy_data, get_enemy_config
from decoy_manager import get_decoy_data, get_decoy_config

class Obstacle:
    def __init__(self, x, y, w=30, h=50, kind="real", sprite_type=None, text=None):
        self.x = x
        self.y = y
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

class TerrainGenerator:
    @staticmethod
    def straight(cursor_x, config):
        plat_y = config.get("platform_y", GROUND_Y)
        if plat_y == "ground": plat_y = GROUND_Y
        length = config.get("length", 500)
        platform = Platform(cursor_x, plat_y, length)
        obstacles = []
        for ob in config.get("obstacles", []):
            ox = cursor_x + ob["x"]
            ob_y = ob.get("y", "ground")
            oy = plat_y if ob_y == "ground" else plat_y + ob_y
            kind = ob.get("kind", "real")
            sprite_type = ob.get("type")
            text = ob.get("text")
            obstacles.append(Obstacle(ox, oy, kind=kind, sprite_type=sprite_type, text=text))

        return {"type": "straight", "platform": platform, "obstacles": obstacles, "length": length}

    @staticmethod
    def stairs_up(cursor_x, config):
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
        wall_height = config.get("height", 280)
        shaft_width = config.get("shaft_width", 150)
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

class EndlessManager:
    def __init__(self, patterns_data, spawn_logic):
        self.patterns = patterns_data
        self.spawn_logic = spawn_logic
        self.last_pattern_id = None
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

def collide_player_hitbox(player, obstacle_sprite):
    player_hitbox = player.hitbox.copy()
    
    if player.is_attacking:
        if player.facing_right:
            player_hitbox.width += 50
        else:
            player_hitbox.x -= 50
            player_hitbox.width += 50
            
    obstacle_rect = obstacle_sprite.image.get_rect(midbottom=obstacle_sprite.rect.midbottom)
    shrink_x = obstacle_rect.width * 0.2
    shrink_y = obstacle_rect.height * 0.1
    enemy_hitbox = obstacle_rect.inflate(-shrink_x, -shrink_y)
    
    return player_hitbox.colliderect(enemy_hitbox)

class ObstacleSprite(Enemy):
    def __init__(self, world_x, y, kind='real', sprite_type=None, lore_text=None):
        self._layer = 0 if kind == 'decor' else 1
        self.kind = kind
        self.sprite_type = sprite_type
        self.lore_text = lore_text
        self.is_used = False 
        
        sprite_data, sprite_config = (None, None)
        if self.sprite_type:
            if self.kind == 'real':
                sprite_data = get_enemy_data(self.sprite_type)
                sprite_config = get_enemy_config(self.sprite_type)
            elif self.kind in ['fake', 'decor']:
                sprite_data = get_decoy_data(self.sprite_type)
                sprite_config = get_decoy_config(self.sprite_type)

        if sprite_data and self.kind == 'real':
            frames_data = sprite_data.get('frames_data', sprite_data.get('frames'))
            config_y_offset = sprite_config.get('y_offset', 0) if sprite_config else 0
            auto_y_offset = sprite_data.get('auto_y_offset', 0) if sprite_data else 0
            y_offset = config_y_offset + auto_y_offset
            super().__init__(world_x, y, self.sprite_type, frames_data, y_offset=y_offset)
            # Đã scale trong load_enemies(), không scale lại ở đây nữa
            self.world_pos.x += 15
            
            # Calculate HP based on distance (progression)
            base_hp = 50
            extra_hp = (world_x // 1000) * 20  # +20 HP per 1000 units
            self.hp = base_hp + extra_hp
            self.max_hp = self.hp
        else:
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
                self.image = pygame.Surface([width, height], pygame.SRCALPHA)
                self.animations["idle"] = Animation([self.image])
            
            self.rect = self.image.get_rect()
            self.hp = 0
            
        self.rect.midbottom = (self.world_pos.x, self.world_pos.y)

    def update(self, world_x_offset, delta_time, player_pos=None):
        if self.kind == 'real' and hasattr(self, 'enemy_type'):
            super().update(world_x_offset, delta_time, player_pos)
        else:
            if "idle" in self.animations:
                self.animations["idle"].update(delta_time)
                self.image = self.animations["idle"].get_frame()
            
            screen_x = self.world_pos.x - world_x_offset
            self.rect.midbottom = (screen_x, self.world_pos.y)
