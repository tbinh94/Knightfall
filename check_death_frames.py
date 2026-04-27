import pygame
import os
pygame.init()
pygame.display.set_mode((1,1))
folder = "assets/player/"
for file in os.listdir(folder):
    if file.endswith(".png"):
        img = pygame.image.load(os.path.join(folder, file))
        print(f"{file}: {img.get_width()}x{img.get_height()}")
