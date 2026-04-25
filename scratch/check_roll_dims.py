import pygame
import os

pygame.init()
pygame.display.set_mode((1,1))

path = 'assets/player/Roll.png'
if os.path.exists(path):
    img = pygame.image.load(path)
    print(f"Roll.png: {img.get_width()}x{img.get_height()}")
else:
    print("Roll.png not found")
pygame.quit()
