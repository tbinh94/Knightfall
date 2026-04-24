import pygame
from config import SCALE_UNIFORM

class Card:
    def __init__(self, name, type, value, cost):
        self.name = name
        self.type = type # 'attack' or 'defend'
        self.value = value
        self.cost = cost

class PlayerStats:
    def __init__(self):
        self.max_hp = 50
        self.hp = 50
        self.atk_bonus = 0
        self.deck = [
            Card("Strike", "attack", 10, 1),
            Card("Strike", "attack", 10, 1),
            Card("Strike", "attack", 10, 1),
            Card("Defend", "defend", 10, 1),
            Card("Defend", "defend", 10, 1),
        ]
        
    def add_hp(self, amount):
        self.hp = min(self.max_hp, self.hp + amount)
        
    def add_max_hp(self, amount):
        self.max_hp += amount
        self.hp += amount # Heal by same amount

    def add_card(self, card):
        self.deck.append(card)

    def draw_hud(self, screen, font):
        # Draw HP Bar
        bar_w, bar_h = int(200 * SCALE_UNIFORM), int(20 * SCALE_UNIFORM)
        x, y = 20, 20
        
        # Bg
        pygame.draw.rect(screen, (50, 0, 0), (x, y, bar_w, bar_h))
        # Fill
        fill_w = int((self.hp / self.max_hp) * bar_w)
        pygame.draw.rect(screen, (200, 0, 0), (x, y, fill_w, bar_h))
        # Border
        pygame.draw.rect(screen, (255, 255, 255), (x, y, bar_w, bar_h), 2)
        
        hp_text = font.render(f"HP: {self.hp}/{self.max_hp}", True, (255, 255, 255))
        screen.blit(hp_text, (x + bar_w + 10, y))
        
        # Draw Deck count
        deck_text = font.render(f"Deck: {len(self.deck)} cards", True, (255, 255, 255))
        screen.blit(deck_text, (x, y + bar_h + 10))
