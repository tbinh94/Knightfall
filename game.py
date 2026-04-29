import pygame
import sys
import os

# Add src to sys.path so files in src/ can import each other without ModuleNotFoundError
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from config import SCREEN_W, SCREEN_H, FPS
from main import Game
from level_manager import LevelManager
from level_editor import LevelEditor
from assets_manager import load_assets, LOADED_THEMES
from enemy_manager import load_enemies, LOADED_ENEMIES
from decoy_manager import load_decoys, LOADED_DECOYS


def main_app():
    pygame.init()
    # print("[OK] Pygame initialized")
    
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Knightfall - Parkour AI")
    
    # 1. Preload ALL resources
    # print("Preloading assets and entities...")
    if not LOADED_THEMES: load_assets()
    if not LOADED_ENEMIES: load_enemies()
    if not LOADED_DECOYS: load_decoys()
    
    # 2. Main Game Loop with Level Selection
    while True:
        level_manager = LevelManager(screen)
        selected_level = level_manager.run()
        
        if selected_level is None:
            break
            
        if selected_level == 'EDITOR':
            editor = LevelEditor(screen)
            editor.run()
            continue
            
        # Run selected level
        level_path = os.path.join("levels", selected_level)
        game = Game(screen, level_path)
        game_result = game.run()
        
        if game_result == 'QUIT':
            break

    # print("Exiting application.")
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main_app()
