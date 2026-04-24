import os
from PIL import Image

def remove_white_background(img_path, threshold=240):
    try:
        img = Image.open(img_path).convert("RGBA")
        datas = img.getdata()
        newData = []
        for item in datas:
            # item is (R, G, B, A)
            if item[0] > threshold and item[1] > threshold and item[2] > threshold:
                newData.append((255, 255, 255, 0)) # Transparent
            else:
                newData.append(item)
        img.putdata(newData)
        # Crop to bounding box
        bbox = img.getbbox()
        if bbox:
            img = img.crop(bbox)
        img.save(img_path)
        print(f"Successfully processed {img_path}")
    except Exception as e:
        print(f"Error processing {img_path}: {e}")

if __name__ == "__main__":
    pillar_src = r"C:\Users\thanh\.gemini\antigravity\brain\4842f537-6d2f-4e46-9329-eb4d6371bdb8\ruined_pillar_white_1776999119097.png"
    wall_src = r"C:\Users\thanh\.gemini\antigravity\brain\4842f537-6d2f-4e46-9329-eb4d6371bdb8\weathered_wall_white_1776999156957.png"
    
    pillar_dest = "assets/decoys/pillar.png"
    wall_dest = "assets/decoys/wall.png"
    
    # Just to be safe, save it directly to the target location instead of overwriting the original
    # We will copy first then process.
    import shutil
    shutil.copy(pillar_src, pillar_dest)
    shutil.copy(wall_src, wall_dest)
    
    remove_white_background(pillar_dest)
    remove_white_background(wall_dest)
