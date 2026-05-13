import pygame
from pathlib import Path
import sys
import os

# Add the 'src' directory to sys.path to allow importing modules from it
src_path = str(Path(__file__).resolve().parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from config import SCREEN_W, SCREEN_H, FPS
from main import Game
from level_manager import LevelManager, HomeScreen
from level_editor import LevelEditor
from assets_manager import load_assets, LOADED_THEMES
from enemy_manager import load_enemies, LOADED_ENEMIES
from decoy_manager import load_decoys, LOADED_DECOYS


def main_app():
    pygame.init()

    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Knightfall")

    # Preload resources
    if not LOADED_THEMES: load_assets()
    if not LOADED_ENEMIES: load_enemies()
    if not LOADED_DECOYS: load_decoys()

    # ── Home Screen ──
    home = HomeScreen(screen)
    result = home.run()
    if result == "QUIT":
        pygame.quit()
        sys.exit()

    # ── Main Loop: Level Select → Play ──
    while True:
        level_manager = LevelManager(screen)
        selected_level = level_manager.run()

        if selected_level is None:
            break

        if selected_level == 'EDITOR':
            editor = LevelEditor(screen)
            editor.run()
            continue

        level_path = os.path.join("levels", selected_level)
        game = Game(screen, level_path)
        game_result = game.run()

        if game_result == 'QUIT':
            break

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main_app()
