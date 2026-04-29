# 🗡️ Dark Fantasy Parkour - Knight's Journey

Game parkour với theme dark fantasy, nhân vật là hiệp sĩ phải vượt qua các quái vật và chướng ngại vật.

## 📋 Tính năng

✅ **5+ Levels** với độ khó tăng dần  
✅ **Level Editor** trực quan để tạo màn chơi riêng  
✅ **AI Training** với NEAT algorithm  
✅ **Branching Paths** - Chọn đường đi khác nhau  
✅ **Progress Tracking** - Lưu tiến độ tự động  
✅ **Monster Types** - Real (chết) và Fake (trừ điểm)  
✅ **Smooth Animations** - Chạy, nhảy, rơi  

---

Demo:
<img width="1519" height="892" alt="image" src="https://github.com/user-attachments/assets/3a39623b-5de9-4a93-99c8-63bd976697ba" />
https://github.com/user-attachments/assets/c9ba2926-7a9d-4bcc-b7d9-7f8f3aa56a10




## 🚀 Cài đặt

### Requirements:
```bash
pip install pygame neat-python
```

### File Structure:
```
parkour-game/
├── main.py                 # Game chính
├── config.py              # Cấu hình game
├── level_manager.py       # Menu chọn level
├── level_editor.py        # Trình soạn thảo level
├── config-neat.txt        # Config cho AI
├── level1.json           # Level mẫu
├── level2.json           # Level Haunted Bridge
├── level3.json           # Level Shadow Realm
├── level4.json           # Level Castle Ruins
├── level_tutorial.json   # Tutorial level
├── assets/
│   └── player/
│       ├── _Run.png
│       ├── _Jump.png
│       └── _JumpFallInbetween.png
└── progress.json         # (auto-generated) Tiến độ người chơi
```

---

## 🎮 Cách chơi

### 1. **Level Selection Menu** (Khuyến nghị):
```bash
python main.py --menu
```
- **↑/↓**: Chọn level
- **ENTER**: Chơi level đã chọn
- **E**: Mở Level Editor
- **ESC**: Thoát

### 2. **Chơi trực tiếp**:
```bash
# Chơi level mặc định
python main.py --play

# Chơi level cụ thể
python main.py --play --level level2.json
```

### 3. **Controls trong game**:
- **SPACE**: Nhảy
- **ESC**: Quay lại menu (trong game over)
- **ENTER**: Restart (sau khi chết)

---

## 🛠️ Level Editor

### Mở Level Editor:
```bash
python main.py --editor
# hoặc
python level_editor.py
```

### Controls:
| Phím | Chức năng |
|------|-----------|
| **P** | Thêm Platform thẳng (Straight Section) |
| **B** | Thêm Branch (Nhánh rẽ) |
| **Click** | Đặt obstacle tại vị trí chuột |
| **Right Click** | Xóa obstacle |
| **1** | Chuyển sang obstacle "Real" (đỏ - chết) |
| **2** | Chuyển sang obstacle "Fake" (xanh - trừ điểm) |
| **Arrow Keys** | Di chuyển camera |
| **G** | Bật/tắt grid |
| **S** | Save level |
| **L** | Load level |
| **C** | Clear tất cả |
| **ESC** | Thoát |

### Quy trình tạo level:
1. Nhấn **P** để tạo platform đầu tiên
2. **Click** để đặt obstacles
3. Nhấn **B** để tạo nhánh rẽ (2 đường)
4. Nhấn **P** để tiếp tục platform sau nhánh
5. Nhấn **S** và nhập tên file (vd: `my_level.json`)

### Tips thiết kế level:
- **Khoảng cách tối thiểu giữa obstacles**: 80-100px
- **Khoảng cách để nhảy qua**: 120-150px
- **Upper path** (nhánh trên): offset_y âm (-110 đến -170)
- **Safe zones**: Để không có obstacle trong 300-400px

---

## 🤖 AI Training

### Train AI với NEAT:
```bash
# Train 50 generations
python main.py --train --gen 50

# Train và xem AI chơi sau khi train
python main.py --train --gen 50 --render
```

### Config AI:
Chỉnh `config-neat.txt` để thay đổi:
- Population size
- Mutation rates
- Network structure

### AI Observations:
AI nhận 7 inputs:
1. Player Y position
2. Vertical velocity
3. Distance to next obstacle
4. Next obstacle type (real/fake)
5. Distance to branch
6. Branch has upper path (yes/no)
7. Upper path offset Y

### AI Actions:
0. Do nothing
1. Jump
2. Choose upper path at branch
3. Choose lower path at branch

---

## 📊 Level Information

| Level | Name | Difficulty | Length | Real Monsters | Fake Monsters |
|-------|------|------------|--------|---------------|---------------|
| Tutorial | Tutorial | ⭐ | ~2000px | 3 | 4 |
| Level 1 | The Dark Path | ⭐⭐ | ~1200px | 4 | 3 |
| Level 2 | Haunted Bridge | ⭐⭐⭐ | ~2270px | 9 | 7 |
| Level 3 | Shadow Realm | ⭐⭐⭐⭐ | ~2970px | 13 | 10 |
| Level 4 | Castle Ruins | ⭐⭐⭐⭐⭐ | ~3720px | 19 | 11 |

---

## 🎨 Customization

### Thay đổi Physics (config.py):
```python
GRAVITY = 0.9        # Tăng = rơi nhanh hơn
JUMP_V = -14         # Giảm = nhảy thấp hơn
RUN_SPEED = 2        # Tăng = game nhanh hơn
```

### Thay đổi Animation Speed:
```python
ANIMATION_CONFIG = {
    'run': {
        'speed': 75    # Giảm = animation nhanh hơn
    },
    'jump': {
        'speed': 100
    },
    'fall': {
        'speed': 120
    }
}
```

### Thay đổi Hitbox (config.py):
```python
PLAYER_W = 30        # Width của hitbox
PLAYER_H = 40        # Height của hitbox
```

---

## 📝 JSON Level Format

### Straight Section:
```json
{
  "type": "straight",
  "length": 500,
  "platform_y": 360,
  "obstacles": [
    {
      "x": 200,           // Vị trí X (relative to section start)
      "y": "ground",      // "ground" hoặc offset từ ground
      "kind": "real"      // "real" hoặc "fake"
    }
  ]
}
```

### Branch Section:
```json
{
  "type": "branch",
  "branch_x": 420,        // Absolute X position
  "paths": [
    {
      "offset_y": 0,      // Lower path (ground level)
      "length": 300,
      "obstacles": [...]
    },
    {
      "offset_y": -120,   // Upper path (120px above ground)
      "length": 300,
      "obstacles": [...]
    }
  ]
}
```

---

## 🐛 Troubleshooting

### Lỗi: Animation không hiển thị đúng
- Kiểm tra sprite files trong `assets/player/`
- Kiểm tra số frames trong `config.py` khớp với sprite sheet
- Sprite sheets phải là PNG với transparency

### Lỗi: Level file not found
```bash
# Kiểm tra file tồn tại
ls level*.json

# Tạo level mới với editor
python main.py --editor
```

### Lỗi: Hitbox không chính xác
- Điều chỉnh `PLAYER_W` và `PLAYER_H` trong `config.py`
- Uncomment debug line trong `Player.draw()` để xem hitbox

### Lỗi: Game quá khó/dễ
- Chỉnh `GRAVITY` và `JUMP_V` trong config
- Sửa level trong editor
- Thay đổi obstacle spacing

---

## 🎯 Roadmap / TODO

### Phase 1: Visual Enhancement
- [ ] Thêm sprite cho monsters thay vì rectangles
- [ ] Background layers với parallax scrolling
- [ ] Particle effects khi chết/win
- [ ] Health bar system

### Phase 2: Audio
- [ ] Background music cho mỗi level
- [ ] Sound effects (jump, death, monster)
- [ ] Audio settings menu

### Phase 3: Advanced Gameplay
- [ ] Moving platforms
- [ ] Boss fights
- [ ] Collectible items (coins, power-ups)
- [ ] Double jump ability
- [ ] Dash ability

### Phase 4: Polish
- [ ] Main menu với animations
- [ ] Leaderboard system
- [ ] Time attack mode
- [ ] Achievements system
- [ ] Story/cutscenes

---

## 🔧 Advanced Features

### Random Level Generator:
Thêm vào code để generate level tự động:
```python
from level_editor import generate_random_level
import json

# Generate level difficulty 3, 6 sections
level = generate_random_level(difficulty=3, sections=6)

with open("level_random.json", "w") as f:
    json.dump(level, f, indent=2)
```

### Custom Monster Types:
Thêm vào level JSON:
```json
{
  "x": 200,
  "y": "ground",
  "kind": "real",
  "subtype": "skeleton",    // Custom type
  "width": 40,              // Custom size
  "height": 60
}
```

---

## 💾 Save System

Progress tự động lưu vào `progress.json`:
```json
{
  "completed": [
    "level_tutorial.json",
    "level1.json"
  ],
  "high_scores": {
    "level1.json": 1500
  }
}
```

Unlock system:
- Tutorial: Luôn mở
- Level N: Mở khi hoàn thành Level N-1

---

## 🤝 Contributing

### Tạo level mới:
1. Mở Level Editor
2. Thiết kế level
3. Save với tên `level_yourname.json`
4. Test level với `python main.py --play --level level_yourname.json`

### Level Design Guidelines:
- Bắt đầu dễ, tăng dần độ khó
- Có safe zones để thở
- Branch paths phải có sự khác biệt rõ ràng
- Test với AI để đảm bảo AI có thể học được
- Real monsters không quá dày đặc

---

## 📜 License

Free to use for educational purposes.

---

## 👥 Credits

- **Game Engine**: Pygame
- **AI**: NEAT-Python
- **Theme**: Dark Fantasy Parkour
- **Character**: Knight (sprite animations)

---

## 📞 Support

Nếu gặp vấn đề:
1. Kiểm tra phần Troubleshooting
2. Đảm bảo đã cài đúng dependencies
3. Kiểm tra file structure đúng
4. Test với tutorial level trước

**Chúc bạn chơi game vui vẻ! 🗡️⚔️🛡️**
