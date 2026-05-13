"""
RESPONSIVE CONFIGURATION
Auto-scales game elements based on screen resolution
"""
import pygame

# ============================================
# BASE RESOLUTION (Reference resolution)
# ============================================
BASE_WIDTH = 1024
BASE_HEIGHT = 768

# ============================================
# CURRENT RESOLUTION (Auto-detect or set manually)
# ============================================
def get_screen_resolution():
    """Tự động lấy resolution màn hình hoặc sử dụng giá trị mặc định"""
    info = pygame.display.Info()
    # Sử dụng 90% màn hình để tránh fullscreen
    return int(info.current_w * 0.9), int(info.current_h * 0.9)

# Có thể override bằng cách set trực tiếp
SCREEN_W = 1280
SCREEN_H = 720
FPS = 60

# ============================================
# SCALE FACTORS (Tự động tính)
# ============================================
SCALE_X = SCREEN_W / BASE_WIDTH
SCALE_Y = SCREEN_H / BASE_HEIGHT
SCALE_UNIFORM = min(SCALE_X, SCALE_Y)  # Giữ tỷ lệ đồng nhất

# ============================================
# GROUND POSITION (Sát đáy màn hình)
# ============================================
GROUND_MARGIN_FROM_BOTTOM = 20  # Tạo một dải đất mỏng 20px ở đáy màn hình
GROUND_Y = SCREEN_H - GROUND_MARGIN_FROM_BOTTOM

# ============================================
# PLAYER SETTINGS (Scaled)
# ============================================
PLAYER_W = int(33 * SCALE_UNIFORM)
PLAYER_H = int(54 * SCALE_UNIFORM)
JUMP_V = -16 * SCALE_UNIFORM
DOUBLE_JUMP_V = -16 * SCALE_UNIFORM
GRAVITY = 0.8 * SCALE_UNIFORM
RUN_SPEED = 4.0 * SCALE_UNIFORM
WALK_SPEED = 5.5 * SCALE_UNIFORM  # Manual movement speed



# ============================================
# ENDLESS MODE (Scaled)
# ============================================
SPEED_INCREASE_RATE = 0.2 * SCALE_UNIFORM
MAX_RUN_SPEED = 15 * SCALE_UNIFORM
SAFE_ZONE_DISTANCE = int(400 * SCALE_X)

# ============================================
# WALL JUMP PHYSICS (Scaled)
# ============================================
WALL_CLIMB_TIME_LIMIT = 3.0
WALL_CLIMB_WARNING_TIME = 1.5
WALL_PUSH_BACK_SPEED = 6.0 * SCALE_UNIFORM
CONSECUTIVE_WALL_JUMP_COOLDOWN = 0.1
PLAYER_DRAG_COEFFICIENT = 0.5
MAX_WALL_SLIDE_SPEED = 2.5 * SCALE_UNIFORM
WALL_COUNTER_SCROLL_SPEED = RUN_SPEED

# ============================================
# STOMP ATTACK SETTINGS (Scaled)
# ============================================
STOMP_WINDUP_TIME = 150 # ms
STOMP_DIVE_SPEED = 30.0 * SCALE_UNIFORM
STOMP_GRAVITY_MULT = 1.5
STOMP_WINDUP_GRAVITY_MULT = 0.5
STOMP_RECOVERY_TIME = 200 # ms
STOMP_COOLDOWN = 300 # ms
STOMP_BOUNCE_V = -8.0 * SCALE_UNIFORM


# ============================================
# ROLL SETTINGS (Scaled)
# ============================================
ROLL_SPEED = 12.0 * SCALE_UNIFORM
ROLL_DURATION = 500 # ms
ROLL_COOLDOWN = 600 # ms
ROLL_INVINCIBILITY_DURATION = 500 # ms

# ============================================
# CAMERA SETTINGS (Scaled)
# ============================================
PLAYER_TARGET_X = int(300 * SCALE_X)
CAMERA_CATCH_UP_SPEED_MULTIPLIER = 1.0

# ============================================
# GAME SETTINGS
# ============================================
MAX_STEPS_PER_GENOME = 2000
DEFAULT_GENERATIONS = 40
DEFAULT_LEVEL = "dark_forest.json"

# ============================================
# TILESET SETTINGS (Scaled)
# ============================================
TILE_SIZE = int(16 * SCALE_UNIFORM)
TILE_SCALE = SCALE_UNIFORM

# Tile presets
TILE_PRESETS = {
    'grass_top': [(0, 7), (1, 7), (2, 7)],
    'solid_middle': [(0, 8), (1, 8), (2, 8)],
    'bottom_platform': [(0, 19), (1, 19), (2, 19)],
    'dark_ground': [(0, 9), (1, 9), (2, 9)],
    'stone_platform': [(3, 7), (4, 7), (5, 7)],
}

ACTIVE_TILE_PRESET = 'dark_ground'

# ============================================
# BACKGROUND PARALLAX (Responsive)
# ============================================
PARALLAX_BACKGROUND_CONFIG = [
    {
        "file": "assets/backgrounds/dungeon_bg.png",
        "speed": 1.0
    }
]


# ============================================
# ANIMATION CONFIG (Scaled)
# ============================================
ANIMATION_CONFIG = {
    'idle': {
        'file': 'assets/player/Idle.png',
        'frames': 8,
        'frame_width': 128,
        'frame_height': 64,
        'scale': 2.4 * SCALE_UNIFORM,
        'speed': 100,
        'y_offset': 0
    },
    'run': {
        'file': 'assets/player/Run.png',
        'frames': 8,
        'frame_width': 128,
        'frame_height': 64,
        'scale': 2.4 * SCALE_UNIFORM,
        'speed': 70,
        'y_offset': 0
    },
    'walk': {
        'file': 'assets/player/Run.png',
        'frames': 8,
        'frame_width': 128,
        'frame_height': 64,
        'scale': 2.4 * SCALE_UNIFORM,
        'speed': 120,
        'y_offset': 0
    },

    'jump': {
        'file': 'assets/player/Jump.png',
        'frames': 8,
        'frame_width': 128,
        'frame_height': 64,
        'scale': 2.4 * SCALE_UNIFORM,
        'speed': 80,
        'y_offset': 0
    },
    'fall': {
        'file': 'assets/player/Jump.png',
        'frames': 8,
        'frame_width': 128,
        'frame_height': 64,
        'scale': 2.4 * SCALE_UNIFORM,
        'speed': 80,
        'y_offset': 0
    },
    'climb': {
        'file': 'assets/player/Climb.png',
        'frames': 6,
        'frame_width': 128,
        'frame_height': 64,
        'scale': 2.4 * SCALE_UNIFORM,
        'speed': 100,
        'y_offset': 0
    },
    'death': {
        'file': 'assets/player/Death.png',
        'frames': 4,
        'frame_width': 128,
        'frame_height': 64,
        'scale': 2.4 * SCALE_UNIFORM,
        'speed': 250,
        'y_offset': 0
    },
    'attack1': {
        'file': 'assets/player/Attacks.png',
        'frames': 6,
        'frame_width': 128,
        'frame_height': 64,
        'scale': 2.4 * SCALE_UNIFORM,
        'speed': 50,
        'y_offset': 0,
        'start_frame': 0
    },
    'attack2': {
        'file': 'assets/player/Attacks.png',
        'frames': 7,
        'frame_width': 128,
        'frame_height': 64,
        'scale': 2.4 * SCALE_UNIFORM,
        'speed': 50,
        'y_offset': 0,
        'start_frame': 6
    },
    'attack3': {
        'file': 'assets/player/Attacks.png',
        'frames': 7,
        'frame_width': 128,
        'frame_height': 64,
        'scale': 2.4 * SCALE_UNIFORM,
        'speed': 50,
        'y_offset': 0,
        'start_frame': 13
    },

    'heal': {
        'file': 'assets/player/Health.png',
        'frames': 8,
        'frame_width': 128,
        'frame_height': 64,
        'scale': 2.4 * SCALE_UNIFORM,
        'speed': 100,
        'y_offset': 0
    },
    'defend': {
        'file': 'assets/player/Idle.png',
        'frames': 8,
        'frame_width': 128,
        'frame_height': 64,
        'scale': 2.4 * SCALE_UNIFORM,
        'speed': 100,
        'y_offset': 0
    },
    'hurt': {
        'file': 'assets/player/Hurt.png',
        'frames': 4,
        'frame_width': 128,
        'frame_height': 64,
        'scale': 2.4 * SCALE_UNIFORM,
        'speed': 100,
        'y_offset': 0
    },
    'hanging': {
        'file': 'assets/player/Hanging.png',
        'frames': 8,
        'frame_width': 128,
        'frame_height': 64,
        'scale': 2.4 * SCALE_UNIFORM,
        'speed': 120,
        'y_offset': 25 # Reduced from 85 to align hands with the ledge correctly
    },
    'crouch': {
        'file': 'assets/player/crouch_idle.png',
        'frames': 8,
        'frame_width': 128,
        'frame_height': 64,
        'scale': 2.4 * SCALE_UNIFORM,
        'speed': 100,
        'y_offset': 0
    },
    'attack_from_air': {
        'file': 'assets/player/attack_mid_air.png',
        'frames': 8,
        'frame_width': 128,
        'frame_height': 64,
        'scale': 2.4 * SCALE_UNIFORM,
        'speed': 70,
        'y_offset': 0
    },
    'jump_attack_start': {
        'file': 'assets/player/attack_from_above.png',
        'frames': 4,
        'frame_width': 128,
        'frame_height': 64,
        'scale': 2.4 * SCALE_UNIFORM,
        'speed': 50,
        'y_offset': 0
    },
    'stomp_down': {
        'file': 'assets/player/attack_from_above.png',
        'frames': 4,
        'frame_width': 128,
        'frame_height': 64,
        'scale': 2.4 * SCALE_UNIFORM,
        'speed': 50,
        'y_offset': 0
    },
    'land_heavy': {
        'file': 'assets/player/crouch_idle.png',
        'frames': 1,
        'frame_width': 128,
        'frame_height': 64,
        'scale': 2.4 * SCALE_UNIFORM,
        'speed': 200,
        'y_offset': 0
    },
    'roll': {
        'file': 'assets/player/Roll.png',
        'frames': 4,
        'frame_width': 128,
        'frame_height': 64,
        'scale': 2.4 * SCALE_UNIFORM,
        'speed': 80,
        'y_offset': 0
    },
    'crouch_attack': {
        'file': 'assets/player/crouch_attacks.png',
        'frames': 8,
        'frame_width': 128,
        'frame_height': 64,
        'scale': 2.4 * SCALE_UNIFORM,
        'speed': 60,
        'y_offset': 0
    }
}


# ============================================
# HELPER FUNCTIONS
# ============================================
def scale_pos(x, y):
    """Scale position from base resolution to current resolution"""
    return int(x * SCALE_X), int(y * SCALE_Y)

def scale_size(width, height):
    """Scale size from base resolution to current resolution"""
    return int(width * SCALE_X), int(height * SCALE_Y)

def scale_value(value):
    """Scale a single value uniformly"""
    return value * SCALE_UNIFORM

# ============================================
# DEBUG INFO
# ============================================
def print_resolution_info():
    """In thông tin resolution để debug"""
    pass

if __name__ == "__main__":
    pygame.init()
    print_resolution_info()