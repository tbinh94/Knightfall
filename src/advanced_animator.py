import pygame

class AdvancedAnimator:
    """
    Class xử lý Sprite Animation chuyên dụng cho Spritesheet do AI tạo.
    Hỗ trợ Texture Atlas (Manual Rects), Pivot/Offset thủ công, Chroma Keying và Delta Time.
    """
    def __init__(self, spritesheet_path, config_data, chroma_key=None, tolerance=30):
        """
        :param spritesheet_path: Đường dẫn tới file ảnh spritesheet.
        :param config_data: Dictionary chứa thông tin các frame (Rect và Pivot).
        :param chroma_key: Tuple (R, G, B) màu nền cần xóa (Ví dụ: (54, 56, 55)).
        :param tolerance: Độ lệch màu cho phép (0-255).
        """
        self.raw_sheet = pygame.image.load(spritesheet_path).convert_alpha()
        
        # Xử lý Chroma Keying lúc runtime
        if chroma_key:
            self.spritesheet = self._apply_chroma_key(self.raw_sheet, chroma_key, tolerance)
        else:
            self.spritesheet = self.raw_sheet
            
        self.animations = {}
        self.current_state = None
        self.frame_index = 0
        self.elapsed_time = 0.0
        self.fps = 10.0
        self.is_looping = True
        
        # Khởi tạo Atlas
        self._initialize_atlas(config_data)

    def _apply_chroma_key(self, surface, color, tolerance):
        """
        Lọc dải màu nền caro thành Alpha = 0.
        """
        new_surface = surface.copy()
        px_array = pygame.PixelArray(new_surface)
        
        # Chuyển tolerance từ thang 0-255 sang tỉ lệ 0.0-1.0 của Pygame
        weight = tolerance / 255.0
        px_array.replace(color, (0, 0, 0, 0), distance=weight)
        
        px_array.close()
        return new_surface.convert_alpha()

    def _initialize_atlas(self, config_data):
        """
        Cắt frame theo tọa độ manual và lưu Pivot.
        """
        for state, frames in config_data.items():
            self.animations[state] = []
            for frame_node in frames:
                x, y, w, h = frame_node["rect"]
                pivot_x, pivot_y = frame_node.get("pivot", (0, 0))
                
                rect = pygame.Rect(x, y, w, h)
                sub_img = self.spritesheet.subsurface(rect).copy()
                
                self.animations[state].append({
                    "surface": sub_img,
                    "pivot": (pivot_x, pivot_y)
                })

    def PlayAnimation(self, state_name, fps=12, loop=True):
        """
        Chuyển trạng thái animation.
        """
        if state_name in self.animations and self.current_state != state_name:
            self.current_state = state_name
            self.frame_index = 0
            self.elapsed_time = 0.0
            self.fps = fps
            self.is_looping = loop

    def Update(self, dt):
        """
        Cập nhật frame dựa trên Delta Time (dt tính bằng giây).
        """
        if not self.current_state or not self.animations[self.current_state]:
            return

        time_per_frame = 1.0 / self.fps
        self.elapsed_time += dt

        while self.elapsed_time >= time_per_frame:
            self.elapsed_time -= time_per_frame
            self.frame_index += 1
            
            if self.frame_index >= len(self.animations[self.current_state]):
                if self.is_looping:
                    self.frame_index = 0
                else:
                    self.frame_index = len(self.animations[self.current_state]) - 1

    def GetCurrentFrame(self):
        """
        Lấy Surface và Pivot của frame hiện tại.
        """
        if not self.current_state:
            return None, (0, 0)
        active_bundle = self.animations[self.current_state][self.frame_index]
        return active_bundle["surface"], active_bundle["pivot"]

# ==========================================
# VÍ DỤ KHỞI TẠO VÀ SỬ DỤNG
# ==========================================
# 
# # Cấu hình dữ liệu manual cho AI Spritesheet
# ENEMY_CONFIG = {
#     "idle": [
#         {"rect": (10, 5, 120, 240), "pivot": (60, 240)},
#         {"rect": (145, 8, 118, 238), "pivot": (59, 238)}
#     ],
#     "run": [
#         {"rect": (280, 5, 122, 242), "pivot": (61, 242)},
#         {"rect": (420, 10, 150, 250), "pivot": (75, 250)}
#     ]
# }
# 
# class ExampleEntity(pygame.sprite.Sprite):
#     def __init__(self, x, y):
#         super().__init__()
#         self.world_pos = pygame.math.Vector2(x, y)
#         self.animator = AdvancedAnimator(
#             "assets/enemies/flying_parasite.png", 
#             ENEMY_CONFIG, 
#             chroma_key=(54, 56, 55), 
#             tolerance=45
#         )
#         self.animator.PlayAnimation("idle", fps=10)
# 
#     def update(self, dt):
#         self.animator.Update(dt)
# 
#     def draw(self, screen):
#         frame, pivot = self.animator.GetCurrentFrame()
#         if frame:
#             # Render dựa vào tâm Pivot
#             draw_x = self.world_pos.x - pivot[0]
#             draw_y = self.world_pos.y - pivot[1]
#             screen.blit(frame, (draw_x, draw_y))
