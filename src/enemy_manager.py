import pygame
import json
import os
import random
from PIL import Image

# --- ANIMATION SYSTEM ---
class Animation:
    def __init__(self, frames, speed=0.1, loop=True):
        """
        frames: list of pygame Surfaces
        speed: time between frames in seconds
        loop: whether to loop the animation
        """
        self.frames = frames
        self.speed = speed
        self.loop = loop
        self.index = 0
        self.timer = 0
        self.done = False

    def update(self, dt):
        """dt: delta time in seconds"""
        if self.done and not self.loop:
            return

        self.timer += dt
        if self.timer >= self.speed:
            self.timer = 0
            self.index += 1

            if self.index >= len(self.frames):
                if self.loop:
                    self.index = 0
                else:
                    self.index = len(self.frames) - 1
                    self.done = True

    def get_frame(self):
        if not self.frames:
            return None
        return self.frames[self.index]

    def reset(self):
        self.index = 0
        self.timer = 0
        self.done = False

# --- ENEMY BASE CLASS ---
class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, enemy_type, frames_data):
        super().__init__()
        self.enemy_type = enemy_type
        self.state = "idle"
        self.velocity = pygame.math.Vector2(0, 0)
        self.direction = 1  # 1: right, -1: left
        self.world_pos = pygame.math.Vector2(x, y)
        self.hp = 30
        self.max_hp = 30
        
        # Load animations from frames_data
        # frames_data can be a dict: {"idle": [f1, f2], "run": [...]}
        # or a flat list (legacy)
        self.animations = {}
        if isinstance(frames_data, dict):
            for state, frames in frames_data.items():
                speed = 0.15 # Default
                if state == "attack": speed = 0.1
                self.animations[state] = Animation(frames, speed=speed)
        else:
            # Fallback for single animation sheets
            self.animations["idle"] = Animation(frames_data, speed=0.15)
            self.animations["run"] = Animation(frames_data, speed=0.15)

        self.image = self.animations[self.state].get_frame()
        self.rect = self.image.get_rect()
        self.update_rect(0) # Initial sync

    def update_rect(self, world_x_offset):
        screen_x = self.world_pos.x - world_x_offset
        self.rect.midbottom = (screen_x, self.world_pos.y)

    def change_state(self, new_state):
        if new_state in self.animations and self.state != new_state:
            self.state = new_state
            self.animations[self.state].reset()

    def update(self, world_x_offset, dt, player_pos=None):
        """dt: delta time in seconds"""
        # 1. Update AI State
        self.update_ai(player_pos, world_x_offset)
        
        # 2. Update Animation
        if self.state in self.animations:
            anim = self.animations[self.state]
            anim.update(dt)
            frame = anim.get_frame()
            
            # Flip sprite based on direction
            if self.direction == -1:
                self.image = pygame.transform.flip(frame, True, False)
            else:
                self.image = frame
        
        # 3. Apply Velocity
        self.world_pos += self.velocity * dt * 60 # Scale to roughly match previous movement
        
        # 4. Sync Rect
        self.update_rect(world_x_offset)

    def update_ai(self, player_pos, world_x_offset=0):
        """Simple AI State Machine"""
        if not player_pos:
            return

        # Convert player screen pos to world pos
        player_world_x = player_pos.centerx + world_x_offset
        player_world_y = player_pos.bottom # Assuming player is on ground
        
        dist_x = player_world_x - self.world_pos.x
        dist_y = player_world_y - self.world_pos.y
        distance = abs(dist_x) # Use horizontal distance for simple chase

        if self.state == "idle":
            if distance < 400:
                self.change_state("run")
        
        elif self.state == "run":
            if distance < 80:
                self.change_state("attack")
                self.velocity.x = 0
            else:
                self.move_towards_player(player_world_x)
        
        elif self.state == "attack":
            if self.animations["attack"].done:
                self.change_state("idle")
        
        elif self.state == "hit":
            # Knockback logic?
            pass

    def move_towards_player(self, player_world_x):
        if player_world_x > self.world_pos.x:
            self.velocity.x = 2
            self.direction = 1
        else:
            self.velocity.x = -2
            self.direction = -1
        
        # Check if we have a run animation
        if "run" in self.animations:
            self.change_state("run")

    def deal_damage(self):
        """Check for damage at specific frame"""
        if self.state == "attack":
            # Damage on frame 3 (if exists)
            if self.animations["attack"].index == 3:
                return True
        return False

# --- GLOBAL ENEMIES ---
LOADED_ENEMIES = {}

def detect_sprite_frames(image_path):
    """
    Tự động phát hiện số frame trong sprite sheet
    Hỗ trợ nhiều loại sprite sheet:
    - Ngang (horizontal): width > height
    - Dọc (vertical): height > width  
    - Grid: width ≈ height
    """
    try:
        img = Image.open(image_path)
        width, height = img.size
        
        # Phát hiện kiểu sprite sheet
        if width > height * 1.5:
            # Sprite sheet ngang
            frame_height = height
            frame_width = height  # Giả định frame vuông
            num_frames = width // frame_width
            sheet_type = "horizontal"
            extra_data = {}
        elif height > width * 1.5:
            # Sprite sheet dọc
            frame_width = width
            frame_height = width  # Giả định frame vuông
            num_frames = height // frame_height
            sheet_type = "vertical"
            extra_data = {}
        else:
            # AI often generates 8x2 or 8x4 grids for 1024x1024 images
            if width >= 1024:
                # 8 columns is very common for detailed AI walk cycles
                num_cols = 8
                num_rows = 2 if height < 512 else 4
                frame_width = width // num_cols
                frame_height = height // num_rows
                num_frames = num_cols * num_rows
                sheet_type = "grid"
                extra_data = {"cols": num_cols, "rows": num_rows}
            elif width > 400 and height > 400:
                num_cols = 2
                num_rows = 2
                frame_width = width // num_cols
                frame_height = height // num_rows
                num_frames = num_cols * num_rows
                sheet_type = "grid"
                extra_data = {"cols": num_cols, "rows": num_rows}
            else:
                frame_width = width
                frame_height = height
                num_frames = 1
                sheet_type = "single"
                extra_data = {}
        
        print(f"     - Image size: {width}x{height}px")
        print(f"     - Type: {sheet_type}")
        print(f"     - Calculated: {num_frames} frames of {frame_width}x{frame_height}px each")
        
        return num_frames, frame_width, frame_height, sheet_type, extra_data
    except Exception as e:
        print(f"  ⚠️ Could not auto-detect frames for {image_path}: {e}")
        return 1, 32, 32, "single", {}

def remove_checkerboard(surface):
    """
    🔥 Loại bỏ phông nền checkerboard (ô vuông xám trắng) từ ảnh AI
    """
    width, height = surface.get_size()
    new_surf = surface.copy()
    
    # Collection phase: find the background colors at the edges
    edge_colors = []
    # Sample edges more densely
    for x in [0, width-1]:
        for y in range(0, height, 10):
            edge_colors.append(surface.get_at((x, y)))
    for y in [0, height-1]:
        for x in range(0, width, 10):
            edge_colors.append(surface.get_at((x, y)))
            
    # Keep only neutral colors (checkerboard is usually grey/white)
    background_targets = []
    for c in edge_colors:
        # If it's a neutral color (R~=G~=B) and not already in targets
        if abs(c.r - c.g) < 20 and abs(c.g - c.b) < 20:
            is_new = True
            for bt in background_targets:
                if abs(c.r - bt.r) < 10:
                    is_new = False; break
            if is_new: background_targets.append(c)

    # Execution phase: Use PixelArray for speed
    px_array = pygame.PixelArray(new_surf)
    for target in background_targets:
        # Use a SMALLER distance to avoid eating the enemy
        px_array.replace(target, (0, 0, 0, 0), distance=0.08) 
    
    px_array.close()
    return new_surf.convert_alpha()

def crop_transparent_borders(surface):
    """
    🔥 Tự động crop phần trong suốt xung quanh sprite
    """
    # Trước khi crop, xóa checkerboard nếu có
    surface = remove_checkerboard(surface)
    
    rect = surface.get_bounding_rect()
    if rect.width == 0 or rect.height == 0:
        return surface
    
    cropped = surface.subsurface(rect).copy()
    return cropped

def auto_detect_ground_position(frame):
    """
    🔥 TỰ ĐỘNG TÌM VỊ TRÍ "CHÂN" CỦA SPRITE
    """
    width, height = frame.get_size()
    for y in range(height - 1, -1, -1):
        for x in range(width):
            alpha = frame.get_at((x, y)).a
            if alpha > 10:
                offset = height - y - 1
                return -offset
    return 0

def load_enemies():
    """
    AUTO LOAD ALL ENEMY SPRITES
    """
    print("Auto-discovering enemy sprites...")
    enemies_dir = "assets/enemies"
    
    if not os.path.exists(enemies_dir):
        os.makedirs(enemies_dir)
        return
    
    enemy_files = [f for f in os.listdir(enemies_dir) if f.endswith('.png')]
    if not enemy_files: return
    
    if not pygame.display.get_surface():
        pygame.display.set_mode((1, 1))
    
    for filename in enemy_files:
        filepath = os.path.join(enemies_dir, filename)
        enemy_name = os.path.splitext(filename)[0]
        print(f"\n  -> Loading enemy: '{enemy_name}'")
        
        try:
            num_frames, frame_width, frame_height, sheet_type, extra = detect_sprite_frames(filepath)
            spritesheet = pygame.image.load(filepath).convert_alpha()
            
            all_frames = []
            
            for i in range(num_frames):
                if sheet_type == "horizontal":
                    x_pos, y_pos = i * frame_width, 0
                elif sheet_type == "vertical":
                    x_pos, y_pos = 0, i * frame_height
                elif sheet_type == "grid":
                    cols = extra["cols"]
                    x_pos, y_pos = (i % cols) * frame_width, (i // cols) * frame_height
                else:
                    x_pos, y_pos = 0, 0
                
                if x_pos + frame_width > spritesheet.get_width() or \
                   y_pos + frame_height > spritesheet.get_height():
                    break
                
                rect = pygame.Rect(x_pos, y_pos, frame_width, frame_height)
                frame = spritesheet.subsurface(rect).copy()
                
                cropped = crop_transparent_borders(frame)
                
                # Auto-scale large assets
                if cropped.get_width() > 100:
                    scale = 0.18 # Balanced scale
                    new_w = int(cropped.get_width() * scale)
                    new_h = int(cropped.get_height() * scale)
                    cropped = pygame.transform.scale(cropped, (new_w, new_h))
                
                all_frames.append(cropped)
            
            if not all_frames: continue
            
            # --- ORGANIZE INTO STATES ---
            # If it's a grid (AI often 8x2 or 8x4), split rows into states
            frames_by_state = {}
            if sheet_type == "grid" and extra.get("rows", 0) >= 2:
                rows = extra["rows"]
                cols = extra["cols"]
                states = ["idle", "run", "attack", "death"]
                for r in range(min(rows, len(states))):
                    state_name = states[r]
                    start_idx = r * cols
                    end_idx = min((r + 1) * cols, len(all_frames))
                    frames_by_state[state_name] = all_frames[start_idx:end_idx]
            else:
                # Use all frames for both idle and run as fallback
                frames_by_state["idle"] = all_frames
                frames_by_state["run"] = all_frames

            auto_y_offset = auto_detect_ground_position(all_frames[0])
            LOADED_ENEMIES[enemy_name] = {
                'frames_data': frames_by_state,
                'frame_width': all_frames[0].get_width(),
                'frame_height': all_frames[0].get_height(),
                'num_frames': len(all_frames),
                'animation_speed': 150,
                'auto_y_offset': auto_y_offset
            }
            print(f"     [OK] Loaded {len(all_frames)} frames in {len(frames_by_state)} states")
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"     [ERROR] Error: {e}")
    
    print(f"\n[OK] Loaded {len(LOADED_ENEMIES)} enemy types.")

def get_random_enemy():
    if not LOADED_ENEMIES: return None
    return random.choice(list(LOADED_ENEMIES.keys()))

def get_enemy_data(enemy_name):
    return LOADED_ENEMIES.get(enemy_name)

ENEMY_CONFIGS = {
    'skeleton': {'animation_speed': 100, 'scale': 1.2},
    'dark_gargoyle': {'scale': 2.0, 'y_offset': 10},
    'spiked_barricade': {'scale': 1.8}
}

def get_enemy_config(enemy_name):
    enemy_data = get_enemy_data(enemy_name)
    default_config = {
        'scale': 1.0,
        'animation_speed': enemy_data.get('animation_speed', 150) if enemy_data else 150,
        'y_offset': enemy_data.get('auto_y_offset', 0) if enemy_data else 0,
        'use_static_frame': False
    }
    manual_config = ENEMY_CONFIGS.get(enemy_name, {})
    default_config.update(manual_config)
    return default_config