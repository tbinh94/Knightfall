import pygame
import os

def check_transparency():
    pygame.init()
    pygame.display.set_mode((1,1))
    files = [
        'assets/backgrounds/background_layer_1.png',
        'assets/backgrounds/background_layer_2.png',
        'assets/backgrounds/background_layer_3.png'
    ]
    for f in files:
        if not os.path.exists(f):
            print(f"{f} does not exist")
            continue
        img = pygame.image.load(f)
        has_alpha = img.get_alpha() is not None or img.get_masks()[3] != 0
        print(f"{f}: has_alpha={has_alpha}, size={img.get_size()}, color@0,0={img.get_at((0,0))}")
        # Check some pixels for transparency
        transparent_pixels = 0
        w, h = img.get_size()
        for x in range(0, w, 100):
            for y in range(0, h, 100):
                if img.get_at((x, y))[3] < 255:
                    transparent_pixels += 1
        print(f"  Transparent samples: {transparent_pixels}")

if __name__ == "__main__":
    check_transparency()
