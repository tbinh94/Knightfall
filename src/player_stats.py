import pygame
from config import SCALE_UNIFORM

class PlayerStats:
    def __init__(self):
        self.max_hp = 50
        self.hp = 50
        self.atk_bonus = 0
        self.gold = 100 # Starting gold
        self.items = [] # Purchased items
        
    def add_hp(self, amount):
        self.hp = min(self.max_hp, self.hp + amount)
        
    def add_max_hp(self, amount):
        self.max_hp += amount
        self.hp += amount # Heal by same amount

    def draw_hud(self, screen, font):
        # Draw HP Bar
        bar_w, bar_h = int(200 * SCALE_UNIFORM), int(20 * SCALE_UNIFORM)
        x, y = 20, 20
        
        # Bg
        pygame.draw.rect(screen, (50, 0, 0), (x, y, bar_w, bar_h))
        # Fill
        fill_w = int((max(0, self.hp) / self.max_hp) * bar_w)
        pygame.draw.rect(screen, (200, 0, 0), (x, y, fill_w, bar_h))
        # Border
        pygame.draw.rect(screen, (255, 255, 255), (x, y, bar_w, bar_h), 2)
        
        hp_text = font.render(f"HP: {int(self.hp)}/{self.max_hp}", True, (255, 255, 255))
        screen.blit(hp_text, (x + bar_w + 10, y))
        
        # Draw Gold
        gold_text = font.render(f"Gold: {self.gold}", True, (255, 215, 0))
        screen.blit(gold_text, (x, y + bar_h + 10))

        # Draw Items next to HP bar
        item_x = x + bar_w + 160
        item_y = y - 5
        if self.items:
            # Draw a small box for each item or a list
            title_text = font.render("Inventory:", True, (200, 200, 200))
            screen.blit(title_text, (item_x, item_y))
            
            for i, item in enumerate(self.items):
                item_text = font.render(f"• {item}", True, (100, 255, 100))
                screen.blit(item_text, (item_x, item_y + 25 + i * 20))

