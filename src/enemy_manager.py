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
        self.state = "idle"
        self.velocity = pygame.math.Vector2(0, 0)
        self.direction = 1  # 1: right, -1: left
        self.world_pos = pygame.math.Vector2(x, y)
        self.hp = 30
        self.max_hp = 30

        # FIX: store y_offset so update_rect can use it for correct ground alignment
        self.y_offset = y_offset
        
        self.animations = {}
        if isinstance(frames_data, dict):
            for state, frames in frames_data.items():
                speed = 0.15
                if state == "attack": speed = 0.1
                self.animations[state] = Animation(frames, speed=speed)
        else:
            self.animations["idle"] = Animation(frames_data, speed=0.15)
            self.animations["run"] = Animation(frames_data, speed=0.15)

        self.image = self.animations[self.state].get_frame()
        self.rect = self.image.get_rect()
        self.update_rect(0)

    def update_rect(self, world_x_offset):
        screen_x = self.world_pos.x - world_x_offset
        # FIX: apply y_offset so sprite feet align with world_pos.y
        self.rect.midbottom = (screen_x, self.world_pos.y + self.y_offset)

    def change_state(self, new_state):
        if new_state in self.animations and self.state != new_state:
            self.state = new_state
            self.animations[self.state].reset()

    def update(self, world_x_offset, dt, player_pos=None):
        """dt: delta time in seconds"""
        self.update_ai(player_pos, world_x_offset)
        
        if self.state in self.animations:
            anim = self.animations[self.state]
            anim.update(dt)
            frame = anim.get_frame()
            
            if self.direction == -1:
                self.image = pygame.transform.flip(frame, True, False)
            else:
                self.image = frame
        
        self.world_pos += self.velocity * dt * 60
        self.update_rect(world_x_offset)

    def update_ai(self, player_pos, world_x_offset=0):
        """Simple AI State Machine"""
        if not player_pos:
            return

        player_world_x = player_pos.centerx + world_x_offset
        player_world_y = player_pos.bottom
        
        dist_x = player_world_x - self.world_pos.x
        dist_y = player_world_y - self.world_pos.y
        distance = abs(dist_x)

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
            if "attack" in self.animations and self.animations["attack"].done:
                self.change_state("idle")
        
        elif self.state == "hit":
            pass

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

        if width > height * 1.5:
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
    candidates_cols = [2, 3, 4, 5, 6, 8]
    candidates_rows = [1, 2, 3, 4]

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
    Loại bỏ phông nền checkerboard (ô vuông xám trắng) từ ảnh AI.
    """
    width, height = surface.get_size()
    new_surf = surface.copy()
    
    edge_colors = []
    for x in [0, width-1]:
        for y in range(0, height, 10):
            edge_colors.append(surface.get_at((x, y)))
    for y in [0, height-1]:
        for x in range(0, width, 10):
            edge_colors.append(surface.get_at((x, y)))
            
    background_targets = []
    for c in edge_colors:
        if abs(c.r - c.g) < 20 and abs(c.g - c.b) < 20:
            is_new = True
            for bt in background_targets:
                if abs(c.r - bt.r) < 10:
                    is_new = False; break
            if is_new: background_targets.append(c)

    px_array = pygame.PixelArray(new_surf)
    for target in background_targets:
        px_array.replace(target, (0, 0, 0, 0), distance=0.08) 
    
    px_array.close()
    return new_surf.convert_alpha()


def crop_transparent_borders(surface):
    """
    Tự động crop phần trong suốt xung quanh sprite.
    """
    surface = remove_checkerboard(surface)
    
    rect = surface.get_bounding_rect()
    if rect.width == 0 or rect.height == 0:
        return surface
    
    cropped = surface.subsurface(rect).copy()
    return cropped


def auto_detect_ground_position(frame):
    """
    Tự động tìm vị trí "chân" của sprite.
    Trả về offset dương (số pixel từ bottom của rect đến chân thật sự).
    """
    width, height = frame.get_size()
    for y in range(height - 1, -1, -1):
        for x in range(width):
            alpha = frame.get_at((x, y)).a
            if alpha > 10:
                # Số pixel trống ở đáy rect (bên dưới chân thật)
                offset = height - y - 1
                return offset  # FIX: trả về dương để cộng vào midbottom.y
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
                all_frames.append(cropped)
            
            if not all_frames: continue
            
            # Normalize frame sizes to prevent animation jitter
            if len(all_frames) > 1:
                max_w = max(f.get_width() for f in all_frames)
                max_h = max(f.get_height() for f in all_frames)
                
                normalized_frames = []
                for frame in all_frames:
                    if frame.get_width() == max_w and frame.get_height() == max_h:
                        normalized_frames.append(frame)
                    else:
                        new_surf = pygame.Surface((max_w, max_h), pygame.SRCALPHA)
                        offset_x = (max_w - frame.get_width()) // 2
                        offset_y = (max_h - frame.get_height()) // 2
                        new_surf.blit(frame, (offset_x, offset_y))
                        normalized_frames.append(new_surf)
                
                all_frames = normalized_frames
            
            # Auto-scale
            TARGET_HEIGHT = 80
            scaled_frames = []
            
            for frame in all_frames:
                current_h = frame.get_height()
                current_w = frame.get_width()
                
                if current_h > 0 and current_h != TARGET_HEIGHT:
                    scale = TARGET_HEIGHT / current_h
                    new_w = int(current_w * scale)
                    new_h = int(current_h * scale)
                    scaled_frame = pygame.transform.smoothscale(frame, (new_w, new_h))
                    scaled_frames.append(scaled_frame)
                else:
                    scaled_frames.append(frame)
            
            all_frames = scaled_frames
            
            if not all_frames: continue
            
            # --- FIX: ORGANIZE INTO STATES BY ROW ---
            # Mỗi row trong grid = 1 animation state riêng biệt
            # (thay vì chia theo index tuyến tính như trước)
            frames_by_state = {}
            total = len(all_frames)

            if sheet_type == "grid" and "rows" in extra and extra["rows"] >= 2:
                cols = extra["cols"]
                rows = extra["rows"]
                frames_per_row = cols

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

            # FIX: auto_y_offset là dương — dùng để bù midbottom khi draw
            auto_y_offset = auto_detect_ground_position(all_frames[0])

            LOADED_ENEMIES[enemy_name] = {
                'frames_data': frames_by_state,
                'frame_width': all_frames[0].get_width(),
                'frame_height': all_frames[0].get_height(),
                'num_frames': len(all_frames),
                'animation_speed': 150,
                'auto_y_offset': auto_y_offset
            }
            print(f"     [OK] Loaded {len(all_frames)} frames → states: {list(frames_by_state.keys())}")
            
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