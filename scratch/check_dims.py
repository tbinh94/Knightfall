import pygame
import os

pygame.init()
pygame.display.set_mode((1,1))

bg_dir = 'assets/backgrounds'
for f in sorted(os.listdir(bg_dir)):
    if f.startswith('Layer_'):
        try:
            img = pygame.image.load(os.path.join(bg_dir, f))
            print(f"{f}: {img.get_width()}x{img.get_height()}")
        except:
            pass
pygame.quit()
