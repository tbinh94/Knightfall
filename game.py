# game.py (FIXED - Proper pygame and assets initialization)
import pygame
import sys

# Thêm 'src' vào sys.path để có thể import các module từ thư mục src
sys.path.append('src') 

from src.main import Game
from src.level_manager import LevelManager
from src.level_editor import LevelEditor
from src.config import *
from src.assets_manager import load_assets
from src.enemy_manager import load_enemies  # 🔥 Import enemy loader

def main_app():
    """
    Hàm điều phối chính của ứng dụng.
    Khởi tạo Pygame MỘT LẦN, sau đó load assets, rồi chạy các trạng thái.
    """
    # ✅ 1. Khởi tạo pygame TRƯỚC
    pygame.init()
    print("✓ Pygame initialized in game.py")
    
    # ✅ 2. Tạo screen
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    
    # ✅ 3. SAU ĐÓ MỚI load assets (vì pygame đã init)
    load_assets()
    
    # ✅ 4. Bắt đầu vòng lặp chính
    print("Bắt đầu chế độ Endless Running...")
    while True:
        game = Game(screen, "endless_run.json")
        game_result = game.run() 
        
        # Nếu thoát game, thoát ứng dụng
        if not pygame.get_init() or game_result == 'QUIT':
            break

    print("Exiting application.")
    pygame.quit()
    sys.exit()

if __name__ == '__main__':
    main_app()