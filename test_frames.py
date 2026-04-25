print("Starting test")
import sys
sys.path.append('src')
print("Imported sys")
import pygame
print("Imported pygame")
pygame.init()
print("Pygame init")
pygame.display.set_mode((1,1))
print("Set mode")
from src.enemy_manager import load_enemies, LOADED_ENEMIES
print("Imported enemy_manager")
print("Loading enemies...")
load_enemies()
print(f"Loaded {len(LOADED_ENEMIES)} enemies")
for name, data in LOADED_ENEMIES.items():
    print(f"Processing {name}")
    frames_data = data['frames_data']
    for state, frames in frames_data.items():
        sizes = [(f.get_width(), f.get_height()) for f in frames]
        unique_sizes = set(sizes)
        print(f'{name} {state}: {len(frames)} frames, sizes: {unique_sizes}')