import pygame
import os

pygame.init()
pygame.display.set_mode((1,1))

path = 'assets/player/crouch_attacks.png'
if os.path.exists(path):
    img = pygame.image.load(path)
    print(f"crouch_attacks.png: {img.get_width()}x{img.get_height()}")
else:
    print("crouch_attacks.png not found")
pygame.quit()
