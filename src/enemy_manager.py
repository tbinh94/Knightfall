import pygame
import json
import os
import random
from PIL import Image
import numpy as np


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
            self.index = (self.index + 1) % len(self.frames)
            if self.index == 0 and not self.loop:
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
    def __init__(self, x, y, enemy_type, frames_data, y_offset=0):
        super().__init__()
        self.enemy_type = enemy_type

        config = get_enemy_config(enemy_type)
        self.y_offset = config.get('y_offset', 0)

        self.state = "idle"
        self.velocity = pygame.math.Vector2(0, 0)
        self.direction = 1  # 1: right, -1: left
        self.world_pos = pygame.math.Vector2(x, y)
        self.patrol_left = x - 100
        self.patrol_right = x + 100
        self.patrol_direction = 1  # 1: right, -1: left
        self.hp = 20
        self.max_hp = 20

        # FIX: store y_offset so update_rect can use it for correct ground alignment
        self.y_offset = y_offset
        self.attack_range = config.get('attack_range', 40)
        self.stun_timer = 0.0
        
        self.animations = {}
        if isinstance(frames_data, dict):
            for state, frames in frames_data.items():
                speed = config.get('animation_speed', 150) / 1000.0
                if state == "attack": speed = 0.1
                self.animations[state] = Animation(frames, speed=speed)
        else:
            speed = config.get('animation_speed', 150) / 1000.0
            self.animations["idle"] = Animation(frames_data, speed=speed)
            self.animations["run"] = Animation(frames_data, speed=speed)

        self.image = self.animations[self.state].get_frame()
        self.rect = self.image.get_rect()
        self.update_rect(0)

    def update_rect(self, world_x_offset):
        screen_x = self.world_pos.x - world_x_offset
        self.rect.midbottom = (screen_x, self.world_pos.y)

        self.rect.y += self.y_offset

    def change_state(self, new_state):
        if self.state != new_state:
            if new_state in self.animations:
                self.state = new_state
                self.animations[self.state].reset()
            elif new_state == "hit":
                self.state = "hit"

    def update(self, world_x_offset, dt, player_pos=None):
        """dt: delta time in seconds"""
        if self.state == "hit":
            if hasattr(self, 'stun_timer'):
                self.stun_timer -= dt

        self.update_ai(player_pos, world_x_offset)
        
        if self.state in self.animations:
            anim = self.animations[self.state]
            anim.update(dt)
            frame = anim.get_frame()
            
            if self.direction == -1:
                self.image = pygame.transform.flip(frame, True, False)
            else:
                self.image = frame
            
            # FIX JITTER: keep rect size stable - only update position, not size
            # The normalized canvas guarantees all frames are the same size anyway,
            # but flip() creates new surface, so we must keep rect size locked.
            old_w, old_h = self.rect.width, self.rect.height
            if self.image.get_width() != old_w or self.image.get_height() != old_h:
                # Re-anchor rect to same midbottom when size changes
                old_midbottom = self.rect.midbottom
                self.rect = self.image.get_rect()
                self.rect.midbottom = old_midbottom
                
        # --- RED TINT EFFECT FOR HIT STATE ---
        if self.state == "hit" and hasattr(self, 'image') and self.image:
            tinted_image = self.image.copy()
            red_surf = pygame.Surface(tinted_image.get_size(), pygame.SRCALPHA)
            red_surf.fill((255, 100, 100, 255))
            tinted_image.blit(red_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            self.image = tinted_image
        
        self.world_pos += self.velocity * dt * 60
        self.update_rect(world_x_offset)

    def update_ai(self, player_pos, world_x_offset=0):
        """Simple AI State Machine with patrol and chase"""
        if not player_pos:
            return

        player_world_x = player_pos.centerx + world_x_offset
        player_world_y = player_pos.bottom
        
        dist_x = player_world_x - self.world_pos.x
        dist_y = player_world_y - self.world_pos.y
        distance = abs(dist_x)

        if self.state == "idle":
            # Patrol between left and right
            if self.patrol_direction == 1 and self.world_pos.x >= self.patrol_right:
                self.patrol_direction = -1
            elif self.patrol_direction == -1 and self.world_pos.x <= self.patrol_left:
                self.patrol_direction = 1
            
            self.velocity.x = self.patrol_direction * 2  # Patrol speed
            self.direction = self.patrol_direction
            
            if distance < 250:
                self.change_state("run")
        
        elif self.state == "run":
            if distance > 400:
                self.change_state("idle")
            elif distance < getattr(self, 'attack_range', 40) and abs(dist_y) < 60:
                # Face player before attacking
                if player_world_x > self.world_pos.x:
                    self.direction = 1
                else:
                    self.direction = -1
                self.change_state("attack")
                self.velocity.x = 0
            else:
                self.move_towards_player(player_world_x)


        
        elif self.state == "attack":
            if player_world_x > self.world_pos.x:
                self.direction = 1
            else:
                self.direction = -1
            if "attack" in self.animations and self.animations["attack"].done:
                self.change_state("idle")
        
        elif self.state == "hit":
            self.velocity.x = 0
            if hasattr(self, 'stun_timer') and self.stun_timer <= 0:
                self.change_state("idle")

    def move_towards_player(self, player_world_x):
        if player_world_x > self.world_pos.x:
            self.velocity.x = 2
            self.direction = 1
        else:
            self.velocity.x = -2
            self.direction = -1
        
        if "run" in self.animations:
            self.change_state("run")

    def deal_damage(self):
        """Check for damage at specific frame"""
        if self.state == "attack":
            if "attack" in self.animations and self.animations["attack"].index == 3:
                return True
        return False

# --- GLOBAL ENEMIES ---
LOADED_ENEMIES = {}

def detect_sprite_frames(image_path):
    """
    Tự động phát hiện số frame trong sprite sheet.
    
    FIX: Đối với ảnh grid vuông (width ≈ height), phát hiện thực tế
    số cột/hàng bằng cách phân tích alpha channel thay vì hard-code 8 cột.
    """
    try:
        img = Image.open(image_path).convert("RGBA")
        width, height = img.size
        pixels = img.load()

        if width > height * 1.5 and width // height >= 2:
            frame_height = height
            frame_width = height
            num_frames = width // frame_width
            sheet_type = "horizontal"
            extra_data = {}

        elif height > width * 1.5:
            frame_width = width
            frame_height = width
            num_frames = height // frame_height
            sheet_type = "vertical"
            extra_data = {}

        else:
            # --- FIX: Detect grid dimensions by scanning for empty columns/rows ---
            # Try common column counts and pick the best fit using vertical alpha profiles
            best_cols, best_rows = _detect_grid_layout(img, pixels, width, height)

            frame_width = width // best_cols
            frame_height = height // best_rows
            num_frames = best_cols * best_rows
            sheet_type = "grid"
            extra_data = {"cols": best_cols, "rows": best_rows}

        print(f"     - Image size: {width}x{height}px")
        print(f"     - Type: {sheet_type}")
        print(f"     - Calculated: {num_frames} frames of {frame_width}x{frame_height}px each")
        
        return num_frames, frame_width, frame_height, sheet_type, extra_data

    except Exception as e:
        print(f"  ⚠️ Could not auto-detect frames for {image_path}: {e}")
        return 1, 32, 32, "single", {}


def _detect_grid_layout(img, pixels, width, height):
    """
    FIX: Phát hiện số cột và hàng thực tế của grid sprite sheet.
    Quét các cột dọc và hàng ngang để tìm ranh giới có ít pixel nhất (gần như trống).
    """
    # Try candidate column counts
    candidates_cols = [2, 3, 4, 5, 6, 8, 10, 11, 12, 14, 16]
    candidates_rows = [1, 2, 3, 4, 5, 6, 8, 10]

    best_cols = 4
    best_rows = 2
    best_score = -1

    for num_cols in candidates_cols:
        if width % num_cols != 0:
            continue
        col_w = width // num_cols

        for num_rows in candidates_rows:
            if height % num_rows != 0:
                continue
            row_h = height // num_rows

            # Score: count how many boundary columns/rows are "empty" (low alpha)
            score = 0

            # Check vertical boundaries between columns
            for c in range(1, num_cols):
                x = c * col_w
                if 0 <= x < width:
                    col_alpha = sum(pixels[x, y][3] for y in range(0, height, max(1, height // 20)))
                    # Lower alpha at boundary = better split
                    score += (height - col_alpha / 255)

            # Check horizontal boundaries between rows
            for r in range(1, num_rows):
                y = r * row_h
                if 0 <= y < height:
                    row_alpha = sum(pixels[x, y][3] for x in range(0, width, max(1, width // 20)))
                    score += (width - row_alpha / 255)

            # Prefer layouts that produce a reasonable frame count (4-16 frames)
            total_frames = num_cols * num_rows
            if total_frames < 4 or total_frames > 32:
                continue

            if score > best_score:
                best_score = score
                best_cols = num_cols
                best_rows = num_rows

    return best_cols, best_rows


def remove_checkerboard(surface):
    """
    🔥 Loại bỏ phông nền của ảnh AI (màu ở các cạnh)
    """
    width, height = surface.get_size()
    new_surf = surface.copy()
    
    # Lấy màu ở 4 góc và các cạnh
    edge_colors = []
    for x in range(0, width, 50):
        edge_colors.append(surface.get_at((x, 0)))
        edge_colors.append(surface.get_at((x, height - 1)))
    for y in range(0, height, 50):
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
        px_array.replace(target, (0, 0, 0, 0), distance=0.1) 
    
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
        
    if not pygame.display.get_surface():
        pygame.display.set_mode((1, 1), pygame.NOFRAME | pygame.HIDDEN)
    
    enemy_folders = [f for f in os.listdir(enemies_dir) if os.path.isdir(os.path.join(enemies_dir, f))]
    for folder in enemy_folders:
        folder_path = os.path.join(enemies_dir, folder)
        enemy_name = folder
        print(f"\n  -> Loading enemy folder: '{enemy_name}'")
        
        frames_by_state = {}
        all_frames_loaded = []
        
        state_map = {
            "idle": ["idle.png", "Idle.png"],
            "run": ["walk.png", "run.png", "Walk.png", "Run.png"],
            "attack": ["attack.png", "Attack.png"]
        }
        
        for state, file_options in state_map.items():
            for filename in file_options:
                filepath = os.path.join(folder_path, filename)
                if os.path.exists(filepath):
                    spritesheet = pygame.image.load(filepath).convert_alpha()
                    spritesheet = remove_checkerboard(spritesheet)
                    
                    config = get_enemy_config(enemy_name)
                    if 'cols' in config and 'rows' in config:
                        num_cols, num_rows = config['cols'], config['rows']
                        frame_width = spritesheet.get_width() // num_cols
                        frame_height = spritesheet.get_height() // num_rows
                        num_frames = num_cols * num_rows
                        sheet_type = "grid"
                        extra = {"cols": num_cols, "rows": num_rows}
                    elif config.get('use_static_frame', False):
                        num_frames = 1
                        frame_width = spritesheet.get_width()
                        frame_height = spritesheet.get_height()
                        sheet_type = "single"
                        extra = {}
                    else:
                        num_frames, frame_width, frame_height, sheet_type, extra = detect_sprite_frames(filepath)
                    
                    state_frames = []
                    for i in range(num_frames):
                        if sheet_type == "horizontal":
                            x_pos, y_pos = i * frame_width, 0
                        elif sheet_type == "vertical":
                            x_pos, y_pos = 0, i * frame_height
                        elif sheet_type == "grid":
                            cols = extra.get("cols", 4)
                            x_pos, y_pos = (i % cols) * frame_width, (i // cols) * frame_height
                        else:
                            x_pos, y_pos = 0, 0
                        
                        if x_pos + frame_width > spritesheet.get_width() or \
                           y_pos + frame_height > spritesheet.get_height():
                            break
                        
                        rect = pygame.Rect(x_pos, y_pos, frame_width, frame_height)
                        frame = spritesheet.subsurface(rect).copy()
                        state_frames.append(frame)
                    
                    if state_frames:
                        # Per-frame tight bounding-box crop
                        cropped_frames = []
                        for f in state_frames:
                            alpha_arr = pygame.surfarray.array_alpha(f)
                            # Find bounding box of content (alpha > 10)
                            non_zero = np.where(alpha_arr > 10)
                            if len(non_zero[0]) > 0 and len(non_zero[1]) > 0:
                                min_x, max_x = np.min(non_zero[0]), np.max(non_zero[0])
                                min_y, max_y = np.min(non_zero[1]), np.max(non_zero[1])
                                
                                # Crop frame directly to character bounds
                                char_rect = pygame.Rect(min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)
                                char_surf = f.subsurface(char_rect).copy()
                                cropped_frames.append(char_surf)
                            else:
                                # Frame is essentially blank, keep it empty
                                cropped_frames.append(f)
                        state_frames = cropped_frames

                        scale_factor = get_enemy_config(enemy_name).get('scale', 0.5)
                        scaled_state_frames = []
                        for f in state_frames:
                            new_w = int(f.get_width() * scale_factor)
                            new_h = int(f.get_height() * scale_factor)
                            scaled_state_frames.append(pygame.transform.scale(f, (new_w, new_h)))
                        
                        frames_by_state[state] = scaled_state_frames
                        all_frames_loaded.extend(scaled_state_frames)
                        break
                        
        if frames_by_state:
            if "idle" not in frames_by_state and all_frames_loaded:
                frames_by_state["idle"] = all_frames_loaded
            if "run" not in frames_by_state:
                frames_by_state["run"] = frames_by_state.get("idle", all_frames_loaded)
            if "attack" not in frames_by_state:
                frames_by_state["attack"] = frames_by_state.get("run", all_frames_loaded)

            # --- FIX JITTER: Normalize all frames to same canvas size, anchored at bottom ---
            max_w = max(f.get_width() for frames in frames_by_state.values() for f in frames)
            max_h = max(f.get_height() for frames in frames_by_state.values() for f in frames)

            normalized_by_state = {}
            for st, frames in frames_by_state.items():
                norm_frames = []
                for f in frames:
                    canvas = pygame.Surface((max_w, max_h), pygame.SRCALPHA)
                    dst_x = (max_w - f.get_width()) // 2
                    dst_y = max_h - f.get_height()  # anchor to bottom
                    canvas.blit(f, (dst_x, dst_y))
                    norm_frames.append(canvas)
                normalized_by_state[st] = norm_frames
            frames_by_state = normalized_by_state
                
            LOADED_ENEMIES[enemy_name] = {
                'frames_data': frames_by_state,
                'frame_width': max_w,
                'frame_height': max_h,
                'num_frames': sum(len(v) for v in frames_by_state.values()),
                'animation_speed': 150,
                'auto_y_offset': 0
            }
            print(f"     [OK] Loaded from folder -> states: {list(frames_by_state.keys())} ({max_w}x{max_h}px canvas)")

    enemy_files = [f for f in os.listdir(enemies_dir) if f.endswith('.png')]
    if not enemy_files and not enemy_folders: return
    
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
            total = len(all_frames)

            if sheet_type == "grid" and "rows" in extra and extra["rows"] >= 2:
                cols = extra["cols"]
                rows = extra["rows"]
                frames_per_row = cols

                if rows == 2:
                    # Đối với ảnh có đúng 2 dòng: Dòng 0 là Idle/Run, Dòng 1 là Attack
                    frames_by_state["idle"] = all_frames[0:cols]
                    frames_by_state["run"] = all_frames[0:cols]
                    frames_by_state["attack"] = all_frames[cols:2*cols]
                else:
                    # Gán state theo thứ tự row
                    state_order = ["idle", "run", "attack", "hit", "death"]
                    for row_idx in range(rows):
                        if row_idx >= len(state_order):
                            break
                        start = row_idx * frames_per_row
                        end = start + frames_per_row
                        row_frames = all_frames[start:end]
                        if row_frames:
                            frames_by_state[state_order[row_idx]] = row_frames

                # Đảm bảo luôn có đủ 3 state cơ bản
                if "idle" not in frames_by_state:
                    frames_by_state["idle"] = all_frames[:frames_per_row]
                if "run" not in frames_by_state:
                    frames_by_state["run"] = frames_by_state["idle"]
                if "attack" not in frames_by_state:
                    frames_by_state["attack"] = frames_by_state.get("run", all_frames)

            elif total >= 8:
                # Fallback tuyến tính nếu không phải grid rõ ràng
                half = total // 2
                frames_by_state["idle"] = all_frames[:half]
                frames_by_state["run"] = all_frames[half:]
                frames_by_state["attack"] = all_frames[half:]
            else:
                frames_by_state["idle"] = all_frames
                frames_by_state["run"] = all_frames
                frames_by_state["attack"] = all_frames

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
            print(f"     [OK] Loaded {len(all_frames)} frames -> states: {list(frames_by_state.keys())}")
            
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


# Load ENEMY_CONFIGS from JSON
ENEMY_CONFIGS = {}
json_path = "assets/enemies.json"
if os.path.exists(json_path):
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            ENEMY_CONFIGS = json.load(f)
        print(f"[OK] Loaded {len(ENEMY_CONFIGS)} enemy configs from {json_path}")
    except Exception as e:
        print(f"⚠️ Could not load {json_path}: {e}")

# Fallback in case JSON is empty or failed
if not ENEMY_CONFIGS:
    ENEMY_CONFIGS = {
        'skeleton': {'animation_speed': 100, 'scale': 1.2},
        'dark_gargoyle': {'scale': 2.0, 'y_offset': 0},
        'spiked_barricade': {'scale': 1.8},
        'rooted_knight_boss': {'cols': 4, 'rows': 3, 'scale': 0.5, 'y_offset': 0},
        'rotten_bug':         {'cols': 4, 'rows': 2, 'scale': 0.45, 'y_offset': 0, 'animation_speed': 100},
        'flying_parasite':    {'cols': 4, 'rows': 2, 'scale': 0.45, 'y_offset': -120}, 
        'forest_ghoul':       {'cols': 4, 'rows': 2, 'scale': 0.45, 'y_offset': 0}
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