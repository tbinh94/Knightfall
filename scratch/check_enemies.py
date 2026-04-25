import os
from PIL import Image

enemies_dir = "assets/enemies"
for f in os.listdir(enemies_dir):
    if f.endswith('.png'):
        img = Image.open(os.path.join(enemies_dir, f))
        print(f"{f}: {img.size}")
