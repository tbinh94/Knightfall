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

        config = get_enemy_config(enemy_type)
        self.y_offset = config.get('y_offset', 0)

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

        self.rect.y += self.y_offset

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
    🔥 Loại bỏ phông nền của ảnh AI (màu ở các cạnh)
    """
    width, height = surface.get_size()
    new_surf = surface.copy()
    
    # Lấy màu ở 4 góc và các cạnh
    edge_colors = []
    for x in range(width):
        edge_colors.append(surface.get_at((x, 0)))
        edge_colors.append(surface.get_at((x, height - 1)))
    for y in range(height):
        edge_colors.append(surface.get_at((0, y)))
        edge_colors.append(surface.get_at((width - 1, y)))
            
    # Lọc các màu trùng lặp
    background_targets = []
    for c in edge_colors:
        is_new = True
        for bt in background_targets:
            if abs(c.r - bt.r) < 15 and abs(c.g - bt.g) < 15 and abs(c.b - bt.b) < 15:
                is_new = False; break
        if is_new: background_targets.append(c)

    # Thay thế các màu nền bằng màu trong suốt
    px_array = pygame.PixelArray(new_surf)
    for target in background_targets:
        px_array.replace(target, (0, 0, 0, 0), distance=0.15) 
    
    px_array.close()
    return new_surf.convert_alpha()

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
            config = ENEMY_CONFIGS.get(enemy_name, {})
            # Ưu tiên lấy cols/rows từ config nếu có
            if 'cols' in config and 'rows' in config:
                spritesheet = pygame.image.load(filepath).convert_alpha()
                spritesheet = remove_checkerboard(spritesheet)
                
                num_cols, num_rows = config['cols'], config['rows']
                frame_width = spritesheet.get_width() // num_cols
                frame_height = spritesheet.get_height() // num_rows
                num_frames = num_cols * num_rows
                sheet_type = "grid"
                extra = {"cols": num_cols, "rows": num_rows}
            else:
                num_frames, frame_width, frame_height, sheet_type, extra = detect_sprite_frames(filepath)
                spritesheet = pygame.image.load(filepath).convert_alpha()
                spritesheet = remove_checkerboard(spritesheet)
            
            clean_frames = []
            
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
                clean_frames.append(frame)
            
            if not clean_frames: continue
            
            # --- TÍNH UNION BOUNDING BOX ĐỂ CROP ĐỒNG NHẤT (CHỐNG JITTER) ---
            min_left, min_top = clean_frames[0].get_width(), clean_frames[0].get_height()
            max_right, max_bottom = 0, 0
            valid_frames = False
            
            for frame in clean_frames:
                rect = frame.get_bounding_rect()
                if rect.width > 0 and rect.height > 0:
                    valid_frames = True
                    min_left = min(min_left, rect.left)
                    min_top = min(min_top, rect.top)
                    max_right = max(max_right, rect.right)
                    max_bottom = max(max_bottom, rect.bottom)
            
            if valid_frames:
                # Tạo một Rect bao quanh phần hiển thị của tất cả các frame
                union_rect = pygame.Rect(min_left, min_top, max_right - min_left, max_bottom - min_top)
                
                # Crop tất cả các frame theo đúng union_rect
                all_frames = []
                for frame in clean_frames:
                    all_frames.append(frame.subsurface(union_rect).copy())
            else:
                all_frames = clean_frames
            
            # --- THÊM LOGIC SCALE Ở ĐÂY (Trước đoạn ORGANIZE INTO STATES) ---
            scale_factor = get_enemy_config(enemy_name).get('scale', 0.5)
            scaled_frames = []
            for frame in all_frames:
                new_w = int(frame.get_width() * scale_factor)
                new_h = int(frame.get_height() * scale_factor)
                scaled_frames.append(pygame.transform.scale(frame, (new_w, new_h)))
            
            all_frames = scaled_frames # Cập nhật lại list frames đã scale
            
            if not all_frames: continue
            
            # --- ORGANIZE INTO STATES ---
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
                frames_by_state["idle"] = all_frames
                frames_by_state["run"] = all_frames

            # Không cần offset tự động vì đã crop đồng nhất (union rect)
            auto_y_offset = 0
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
    'spiked_barricade': {'scale': 1.8},
    
    # Định nghĩa rõ số cột (cols) và số dòng (rows) để cắt chuẩn
    'rooted_knight_boss': {'cols': 4, 'rows': 3, 'scale': 0.6, 'y_offset': 20},
    'rotten_bug':         {'cols': 5, 'rows': 2, 'scale': 0.45, 'y_offset': 30},
    'flying_parasite':    {'cols': 4, 'rows': 2, 'scale': 0.45, 'y_offset': -80}, # Quái bay nên y_offset âm
    'forest_ghoul':       {'cols': 4, 'rows': 2, 'scale': 0.5, 'y_offset': 40}
}

def get_enemy_config(enemy_name):
    enemy_data = get_enemy_data(enemy_name)
    default_config = {
        'scale': 0.5,
        'animation_speed': enemy_data.get('animation_speed', 150) if enemy_data else 150,
        'y_offset': enemy_data.get('auto_y_offset', 0) if enemy_data else 0,
        'use_static_frame': False
    }
    manual_config = ENEMY_CONFIGS.get(enemy_name, {})
    default_config.update(manual_config)
    return default_config