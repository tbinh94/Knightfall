# level_manager.py - HOME SCREEN + LEVEL SELECTION UI
import pygame
import json
import os
import glob
import math
import random
from config import *


def _load_font(name, size, bold=False):
    """Try to load a nice font, fall back to SysFont."""
    try:
        return pygame.font.SysFont(name, size, bold=bold)
    except Exception:
        return pygame.font.SysFont("Arial", size, bold=bold)


# ─────────────────────────────────────────────
#  PARTICLE SYSTEM  (shared by both screens)
# ─────────────────────────────────────────────
class Particle:
    def __init__(self, w, h):
        self.x = random.uniform(0, w)
        self.y = random.uniform(0, h)
        self.vx = random.uniform(-0.3, 0.3)
        self.vy = random.uniform(-0.6, -0.1)
        self.size = random.uniform(1, 3)
        self.alpha = random.randint(80, 200)
        self.fade = random.uniform(0.3, 0.8)
        self.color = random.choice([
            (180, 120, 255), (120, 80, 200), (255, 180, 80),
            (100, 200, 255), (200, 100, 255)
        ])

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.alpha -= self.fade
        return self.alpha > 0

    def draw(self, screen):
        if self.alpha <= 0:
            return
        s = pygame.Surface((int(self.size * 2), int(self.size * 2)), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, int(self.alpha)), (int(self.size), int(self.size)), int(self.size))
        screen.blit(s, (int(self.x - self.size), int(self.y - self.size)))


def _draw_bg(surface, t):
    """Animated dark background with subtle gradient."""
    w, h = surface.get_size()
    # Base dark gradient
    for y in range(0, h, 4):
        ratio = y / h
        r = int(8 + 10 * ratio + 4 * math.sin(t * 0.5 + ratio * 3))
        g = int(5 + 8 * ratio)
        b = int(18 + 20 * ratio + 5 * math.sin(t * 0.3))
        pygame.draw.rect(surface, (max(0,r), max(0,g), max(0,b)), (0, y, w, 4))


def _draw_text_glow(surface, font, text, x, y, color, glow_color, center=True):
    """Draw text with a soft glow behind it."""
    glow = font.render(text, True, glow_color)
    main = font.render(text, True, color)
    rx, ry = (x - main.get_width() // 2, y) if center else (x, y)
    for ox, oy in [(-2,0),(2,0),(0,-2),(0,2),(-1,-1),(1,1),(-1,1),(1,-1)]:
        gs = glow.copy()
        gs.set_alpha(60)
        surface.blit(gs, (rx + ox, ry + oy))
    surface.blit(main, (rx, ry))


# ─────────────────────────────────────────────
#  HOME SCREEN
# ─────────────────────────────────────────────
class HomeScreen:
    def __init__(self, screen):
        self.screen = screen
        self.w, self.h = screen.get_size()
        self.clock = pygame.time.Clock()
        self.t = 0.0

        # Load Background
        try:
            bg_path = os.path.join("assets", "backgrounds", "home_screen.png")
            self.bg = pygame.image.load(bg_path).convert()
            self.bg = pygame.transform.scale(self.bg, (self.w, self.h))
        except:
            self.bg = pygame.Surface((self.w, self.h))
            self.bg.fill((20, 15, 25))

        # Fonts
        self.font_title   = _load_font("Georgia", int(100 * SCALE_UNIFORM), bold=True)
        self.font_tagline = _load_font("Georgia", int(24 * SCALE_UNIFORM))
        self.font_menu    = _load_font("Georgia", int(32 * SCALE_UNIFORM))
        self.font_hint    = _load_font("Arial", int(16 * SCALE_UNIFORM))
        self.font_copy    = _load_font("Arial", int(16 * SCALE_UNIFORM))

        self.particles = [Particle(self.w, self.h) for _ in range(40)]
        
        self.menu_items = ["START GAME", "SETTINGS", "CONTROLS", "CREDITS", "QUIT GAME"]
        self.selected_idx = 0
        self.menu_hovers = [0.0] * len(self.menu_items)

    def _respawn_particles(self):
        self.particles = [p for p in self.particles if p.update()]
        while len(self.particles) < 40:
            self.particles.append(Particle(self.w, self.h))

    def _draw_ornament(self, x, y, width):
        # Draw the thin line with a small diamond in the middle
        line_col = (150, 150, 150)
        pygame.draw.line(self.screen, line_col, (x - width//2, y), (x + width//2, y), 1)
        # Small diamond
        pts = [(x, y-4), (x+4, y), (x, y+4), (x-4, y)]
        pygame.draw.polygon(self.screen, (200, 200, 200), pts)
        pygame.draw.polygon(self.screen, (100, 100, 100), pts, 1)

    def run(self):
        pygame.mouse.set_visible(True)
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            self.t += dt
            
            mx, my = pygame.mouse.get_pos()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "QUIT"
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return "QUIT"
                    if event.key == pygame.K_UP:
                        self.selected_idx = (self.selected_idx - 1) % len(self.menu_items)
                    if event.key == pygame.K_DOWN:
                        self.selected_idx = (self.selected_idx + 1) % len(self.menu_items)
                    if event.key in [pygame.K_RETURN, pygame.K_SPACE, pygame.K_e]:
                        if self.menu_items[self.selected_idx] == "START GAME":
                            return "MENU"
                        if self.menu_items[self.selected_idx] == "QUIT GAME":
                            return "QUIT"
                
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        if self.menu_items[self.selected_idx] == "START GAME":
                            return "MENU"
                        if self.menu_items[self.selected_idx] == "QUIT GAME":
                            return "QUIT"

            # ── Background ──
            self.screen.blit(self.bg, (0, 0))
            
            # Subtly darken the left side for menu readability
            overlay = pygame.Surface((int(self.w * 0.5), self.h), pygame.SRCALPHA)
            for x in range(overlay.get_width()):
                alpha = int(140 * (1 - x / overlay.get_width()))
                pygame.draw.rect(overlay, (0, 0, 0, alpha), (x, 0, 1, self.h))
            self.screen.blit(overlay, (0, 0))

            # ── Particles (subtle embers) ──
            self._respawn_particles()
            for p in self.particles:
                p.draw(self.screen)

            # ── Title & Tagline ──
            start_x = int(self.w * 0.12)
            
            title_surf = self.font_title.render("KNIGHTFALL", True, (230, 220, 210))
            self.screen.blit(title_surf, (start_x, int(self.h * 0.22)))
            
            tag_text = "A DARK FANTASY PARKOUR ADVENTURE"
            tag_surf = self.font_tagline.render(tag_text, True, (160, 150, 140))
            tag_x = start_x + (title_surf.get_width() - tag_surf.get_width())//2
            self.screen.blit(tag_surf, (tag_x, int(self.h * 0.36)))

            # ── Ornament ──
            orn_y = int(self.h * 0.43)
            self._draw_ornament(start_x + title_surf.get_width()//2, orn_y, 400)

            # ── Menu ──
            menu_y_start = int(self.h * 0.52)
            item_h = int(60 * SCALE_Y)
            
            for i, item in enumerate(self.menu_items):
                item_y = menu_y_start + i * item_h
                # Check for mouse hover
                item_rect = pygame.Rect(start_x, item_y - 10, title_surf.get_width(), item_h)
                if item_rect.collidepoint(mx, my):
                    self.selected_idx = i
                
                target = 1.0 if self.selected_idx == i else 0.0
                self.menu_hovers[i] += (target - self.menu_hovers[i]) * 0.15
                h = self.menu_hovers[i]
                
                # Selection Highlight Bar (two thin lines above/below)
                if h > 0.01:
                    bar_w = int(title_surf.get_width() * 0.8 * h)
                    bx = start_x + (title_surf.get_width() - bar_w) // 2
                    for offset in [-4, 38]:
                        s = pygame.Surface((bar_w, 2), pygame.SRCALPHA)
                        s.fill((180, 100, 255, int(150 * h)))
                        self.screen.blit(s, (bx, item_y + offset))

                col = (255, 255, 255) if h > 0.5 else (180, 170, 160)
                txt_surf = self.font_menu.render(item, True, col)
                tx = start_x + (title_surf.get_width() - txt_surf.get_width()) // 2
                self.screen.blit(txt_surf, (tx, item_y))

            # ── Bottom Hint ──
            hint_y = int(self.h * 0.85)
            self._draw_ornament(start_x + title_surf.get_width()//2, hint_y, 100)
            hint_text = "Begin your descent into darkness."
            hint_surf = self.font_hint.render(hint_text, True, (100, 90, 80))
            self.screen.blit(hint_surf, (start_x + (title_surf.get_width() - hint_surf.get_width())//2, hint_y + 15))

            # ── Copyright & Controls Info ──
            copy_surf = self.font_copy.render("© 2025 Knightfall Dev Team  •  Made with Python & Pygame  •  v0.1", True, (80, 75, 70))
            self.screen.blit(copy_surf, (30, self.h - 40))
            
            # Key hints at bottom right
            hint_keys = "[E] SELECT    [ESC] BACK"
            key_surf = self.font_hint.render(hint_keys, True, (120, 115, 110))
            self.screen.blit(key_surf, (self.w - key_surf.get_width() - 40, self.h - 40))

            pygame.display.flip()



# ─────────────────────────────────────────────
#  LEVEL MANAGER (Select Level Screen)
# ─────────────────────────────────────────────
class LevelManager:
    def __init__(self, screen):
        self.screen = screen
        self.w, self.h = screen.get_size()
        self.clock = pygame.time.Clock()
        self.t = 0.0

        self.font_title  = _load_font("Georgia", int(52 * SCALE_UNIFORM), bold=True)
        self.font_item   = _load_font("Arial", int(26 * SCALE_UNIFORM), bold=True)
        self.font_meta   = _load_font("Arial", int(17 * SCALE_UNIFORM))
        self.font_status = _load_font("Arial", int(17 * SCALE_UNIFORM), bold=True)
        self.font_copy   = _load_font("Arial", int(15 * SCALE_UNIFORM))

        self.progress_file = "progress.json"
        self.completed_levels = self.load_progress()

        regular_levels, special_modes = self.discover_levels()
        editor_item = {
            "display_name": "⚒  Level Editor",
            "filename": "EDITOR",
            "is_editor": True,
            "difficulty": "",
            "description": "Create and design your own levels"
        }
        self.menu_items = regular_levels + special_modes + [editor_item]

        self.selected_index = 0
        self.hover_progress = [0.0] * len(self.menu_items)
        self.scroll_offset = 0
        self.visible_items = 6

        self.particles = [Particle(self.w, self.h) for _ in range(60)]

        # Cache pre-built card data
        self._card_w = int(min(720, self.w * 0.72))
        self._card_h = int(72 * SCALE_UNIFORM)
        self._card_gap = int(14 * SCALE_UNIFORM)

    # ── Data helpers ──────────────────────────
    def discover_levels(self):
        levels_dir = "levels"
        discovered, special = [], []
        for fp in glob.glob(os.path.join(levels_dir, "*.json")):
            try:
                with open(fp, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                meta = data.get("metadata", {})
                is_special = data.get("mode") == "endless"
                info = {
                    "display_name": meta.get("display_name", os.path.basename(fp)),
                    "filename": os.path.basename(fp),
                    "difficulty": meta.get("difficulty", "Normal"),
                    "description": meta.get("description", ""),
                    "is_editor": False,
                    "is_special_mode": is_special,
                    "order": meta.get("order", 999)
                }
                (special if is_special else discovered).append(info)
            except Exception:
                pass
        discovered.sort(key=lambda x: x["order"])
        return discovered, special

    def load_progress(self):
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r') as f:
                    return set(json.load(f))
            except Exception:
                return set()
        return set()

    def save_progress(self):
        with open(self.progress_file, 'w') as f:
            json.dump(list(self.completed_levels), f)

    def complete_level(self, filename):
        item = next((i for i in self.menu_items if i["filename"] == filename), None)
        if item and item.get("is_special_mode"):
            return
        if filename not in self.completed_levels:
            self.completed_levels.add(filename)
            self.save_progress()

    def _is_unlocked(self, index):
        item = self.menu_items[index]
        if item.get("is_editor") or item.get("is_special_mode"):
            return True
        if index == 0:
            return True
        prev = self.menu_items[index - 1]
        if prev.get("is_editor") or prev.get("is_special_mode"):
            return True
        return prev["filename"] in self.completed_levels

    # ── Drawing ───────────────────────────────
    def _diff_color(self, diff):
        return {
            "Easy":   (90, 220, 120),
            "Normal": (100, 160, 255),
            "Hard":   (255, 160, 80),
            "Expert": (255, 80, 120),
        }.get(diff, (160, 160, 160))

    def draw(self):
        _draw_bg(self.screen, self.t)

        # Particles
        self.particles = [p for p in self.particles if p.update()]
        while len(self.particles) < 60:
            self.particles.append(Particle(self.w, self.h))
        for p in self.particles:
            p.draw(self.screen)

        cx = self.w // 2

        # ── Title ──
        _draw_text_glow(self.screen, self.font_title, "SELECT LEVEL",
                        cx, int(self.h * 0.06),
                        (255, 248, 240), (160, 90, 255))

        # Divider under title
        title_h = self.font_title.size("SELECT LEVEL")[1]
        div_y = int(self.h * 0.06) + title_h + 10
        for dx in range(-200, 201, 3):
            alpha = int(140 * (1 - abs(dx) / 200))
            s = pygame.Surface((3, 2), pygame.SRCALPHA)
            s.fill((180, 120, 255, alpha))
            self.screen.blit(s, (cx + dx, div_y))

        # ── Cards ──
        top_y = div_y + 22
        cw, ch = self._card_w, self._card_h
        gap = self._card_gap

        if len(self.menu_items) > self.visible_items:
            self.scroll_offset = max(0, self.selected_index - self.visible_items + 1) \
                if self.selected_index >= self.visible_items else 0

        for i, item in enumerate(self.menu_items):
            if i < self.scroll_offset or i >= self.scroll_offset + self.visible_items:
                continue
            di = i - self.scroll_offset
            card_y = top_y + di * (ch + gap)

            is_sel = (i == self.selected_index)
            is_unlocked = self._is_unlocked(i)

            # Hover animation
            target = 1.0 if is_sel else 0.0
            self.hover_progress[i] += (target - self.hover_progress[i]) * 0.18
            hv = self.hover_progress[i]

            lift = int(-7 * hv)
            card_rect = pygame.Rect(cx - cw//2, card_y + lift, cw, ch)

            self._draw_card(card_rect, item, i, is_sel, is_unlocked, hv)

        # ── Bottom hint ──
        hint = "↑↓ Navigate   ENTER Select   ESC Back"
        hint_surf = self.font_copy.render(hint, True, (110, 95, 140))
        self.screen.blit(hint_surf, hint_surf.get_rect(center=(cx, self.h - 24)))

        pygame.display.flip()

    def _draw_card(self, rect, item, index, is_sel, is_unlocked, hv):
        x, y, w, h = rect

        # Card background surface
        card_surf = pygame.Surface((w, h), pygame.SRCALPHA)

        if not is_unlocked:
            bg1, bg2 = (40, 35, 55), (35, 30, 48)
        elif is_sel:
            bg1 = (70, 45, 130)
            bg2 = (95, 60, 170)
        else:
            bg1 = (38, 28, 62)
            bg2 = (50, 38, 80)

        # Gradient fill
        for row in range(h):
            ratio = row / h
            r = int(bg1[0] * (1-ratio) + bg2[0] * ratio)
            g = int(bg1[1] * (1-ratio) + bg2[1] * ratio)
            b = int(bg1[2] * (1-ratio) + bg2[2] * ratio)
            pygame.draw.line(card_surf, (r, g, b), (0, row), (w, row))

        # Glow border
        border_col = (200, 140, 255) if is_sel else (90, 70, 130)
        border_w = 2 + int(hv)
        pygame.draw.rect(card_surf, border_col, (0, 0, w, h), border_w, border_radius=8)

        # Inner shimmer on selected
        if hv > 0.1:
            shimmer = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.rect(shimmer, (180, 120, 255, int(20 * hv)), (0, 0, w, h), border_radius=8)
            card_surf.blit(shimmer, (0, 0))

        self.screen.blit(card_surf, (x, y))

        # ── Text content ──
        pad = 22
        text_col = (255, 255, 255) if is_unlocked else (100, 90, 120)

        name_surf = self.font_item.render(item["display_name"], True, text_col)
        self.screen.blit(name_surf, (x + pad, y + 12))

        if item.get("difficulty"):
            diff_col = self._diff_color(item["difficulty"]) if is_unlocked else (80, 75, 100)
            stars = {"Easy": "★", "Normal": "★★", "Hard": "★★★", "Expert": "★★★★"}.get(item["difficulty"], "")
            diff_surf = self.font_meta.render(f"{stars}  {item['difficulty']}", True, diff_col)
            self.screen.blit(diff_surf, (x + pad, y + h - diff_surf.get_height() - 10))

        # Completed badge
        if not item.get("is_editor") and not item.get("is_special_mode") \
                and item["filename"] in self.completed_levels:
            badge = self.font_status.render("✓ DONE", True, (80, 240, 120))
            self.screen.blit(badge, badge.get_rect(midright=(x + w - pad, y + h//2)))

        # Lock
        if not is_unlocked:
            lock = self.font_item.render("🔒 LOCKED", True, (180, 120, 80))
            self.screen.blit(lock, lock.get_rect(center=(x + w//2, y + h//2)))

        # Selection arrow
        if is_sel:
            ax = x - 20
            ay = y + h // 2
            pulse = int(4 * math.sin(self.t * 4))
            pygame.draw.polygon(self.screen, (220, 160, 255), [
                (ax + pulse, ay),
                (ax - 10 + pulse, ay - 7),
                (ax - 10 + pulse, ay + 7)
            ])

    # ── Input ─────────────────────────────────
    def handle_input(self):
        mx, my = pygame.mouse.get_pos()
        cx = self.w // 2
        title_size = self.font_title.size("SELECT LEVEL")
        top_y = int(self.h * 0.06) + title_size[1] + 10 + 22
        cw, ch = self._card_w, self._card_h
        gap = self._card_gap

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            
            # Mouse interaction: hover and click
            if event.type == pygame.MOUSEMOTION:
                for i in range(len(self.menu_items)):
                    if i < self.scroll_offset or i >= self.scroll_offset + self.visible_items:
                        continue
                    di = i - self.scroll_offset
                    card_y = top_y + di * (ch + gap)
                    card_rect = pygame.Rect(cx - cw//2, card_y, cw, ch)
                    if card_rect.collidepoint(mx, my):
                        self.selected_index = i

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: # Left click
                    for i in range(len(self.menu_items)):
                        if i < self.scroll_offset or i >= self.scroll_offset + self.visible_items:
                            continue
                        di = i - self.scroll_offset
                        card_y = top_y + di * (ch + gap)
                        card_rect = pygame.Rect(cx - cw//2, card_y, cw, ch)
                        if card_rect.collidepoint(mx, my):
                            item = self.menu_items[i]
                            if item.get("is_editor"): return "EDITOR"
                            if self._is_unlocked(i): return item["filename"]

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    self.selected_index = (self.selected_index - 1) % len(self.menu_items)
                elif event.key == pygame.K_DOWN:
                    self.selected_index = (self.selected_index + 1) % len(self.menu_items)
                elif event.key == pygame.K_RETURN:
                    item = self.menu_items[self.selected_index]
                    if item.get("is_editor"):
                        return "EDITOR"
                    if self._is_unlocked(self.selected_index):
                        return item["filename"]
                elif event.key == pygame.K_ESCAPE:
                    return None
        return "CONTINUE"


    def run(self):
        pygame.mouse.set_visible(True)
        while True:
            self.t += self.clock.tick(FPS) / 1000.0

            result = self.handle_input()
            if result != "CONTINUE":
                return result
            self.draw()