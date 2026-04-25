# decoy_manager.py
import pygame
import os
import random
from PIL import Image

LOADED_DECOYS = {}

def detect_sprite_frames(image_path):
    """
    Phát hiện số frame trong sprite sheet.
    Đã lược bỏ phần đoán grid tự động gây lỗi cắt phạm hình ảnh.
    """
    try:
        img = Image.open(image_path)
        width, height = img.size
        
        # Phát hiện kiểu sprite sheet
        if width > height * 1.5:
            # Sprite sheet ngang (Horizontal)
            frame_height = height
            frame_width = height  # Giả định frame vuông
            num_frames = width // frame_width
            sheet_type = "horizontal"
            extra_data = {}
        elif height > width * 1.5:
            # Sprite sheet dọc (Vertical)
            frame_width = width
            frame_height = width  # Giả định frame vuông
            num_frames = height // frame_height
            sheet_type = "vertical"
            extra_data = {}
        else:
            # Ảnh đơn (Single frame) - Dù to cỡ nào cũng không tự ý cắt đôi nữa
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

def _crop_transparent_borders(surface):
    rect = surface.get_bounding_rect()
    if rect.width == 0 or rect.height == 0:
        return surface
    return surface.subsurface(rect).copy()

def _auto_detect_ground_position(frame):
    width, height = frame.get_size()
    for y in range(height - 1, -1, -1):
        for x in range(width):
            if frame.get_at((x, y)).a > 10:
                return -(height - y - 1)
    return 0

def load_decoys():
    decoys_dir = "assets/decoys"
    if not os.path.exists(decoys_dir):
        os.makedirs(decoys_dir)
        return
    decoy_files = [f for f in os.listdir(decoys_dir) if f.endswith('.png')]
    if not decoy_files: return
    if not pygame.display.get_surface():
        pygame.display.set_mode((1, 1))
    for filename in decoy_files:
        filepath = os.path.join(decoys_dir, filename)
        decoy_name = os.path.splitext(filename)[0]
        try:
            num_frames, frame_width, frame_height, sheet_type = _detect_sprite_frames(filepath)
            spritesheet = pygame.image.load(filepath).convert_alpha()
            cropped_frames = []
            for i in range(num_frames):
                if sheet_type == "horizontal": x_pos, y_pos = i * frame_width, 0
                elif sheet_type == "vertical": x_pos, y_pos = 0, i * frame_height
                else: x_pos, y_pos = 0, 0
                if x_pos + frame_width > spritesheet.get_width() or y_pos + frame_height > spritesheet.get_height():
                    break
                rect = pygame.Rect(x_pos, y_pos, frame_width, frame_height)
                frame = spritesheet.subsurface(rect).copy()
                cropped = _crop_transparent_borders(frame)
                cropped_frames.append(cropped)
            if not cropped_frames: continue
            auto_y_offset = _auto_detect_ground_position(cropped_frames[0])
            LOADED_DECOYS[decoy_name] = {
                'frames': cropped_frames,
                'frame_width': cropped_frames[0].get_width(),
                'frame_height': cropped_frames[0].get_height(),
                'num_frames': len(cropped_frames),
                'animation_speed': 200,
                'auto_y_offset': auto_y_offset
            }
        except Exception:
            pass

def get_random_decoy():
    if not LOADED_DECOYS: return None
    return random.choice(list(LOADED_DECOYS.keys()))

def get_decoy_data(decoy_name):
    return LOADED_DECOYS.get(decoy_name)

DECOY_CONFIGS = {
    'pillar': {'scale': 0.3, 'use_static_frame': True},
    'wall': {'scale': 0.4, 'use_static_frame': True, 'y_offset': 28},
    'warrior': {'scale': 2.4, 'use_static_frame': True},
    'column': {'scale': 1.0, 'use_static_frame': True, 'y_offset': 0}
}

def get_decoy_config(decoy_name):
    decoy_data = get_decoy_data(decoy_name)
    default_config = {
        'scale': 1.0,
        'animation_speed': decoy_data.get('animation_speed', 200) if decoy_data else 200,
        'y_offset': decoy_data.get('auto_y_offset', 0) if decoy_data else 0,
        'use_static_frame': False
    }
    manual_config = DECOY_CONFIGS.get(decoy_name, {})
    default_config.update(manual_config)
    return default_config