import pygame
import random
from config import SCREEN_W, SCREEN_H, SCALE_UNIFORM
from player_stats import Card
        
class RewardScreen:
    def __init__(self, screen, font, small_font):
        self.screen = screen
        self.font = font
        self.small_font = small_font
        self.options = [
            {"name": "Max HP +10", "type": "hp", "val": 10},
            {"name": "Attack +5", "type": "atk", "val": 5},
            {"name": "New Card: Strike+", "type": "card", "val": Card("Strike+", "attack", 15, 1)}
        ]
        
    def run(self):
        running = True
        btn_w, btn_h = int(250 * SCALE_UNIFORM), int(100 * SCALE_UNIFORM)
        rects = []
        for i in range(3):
            rects.append(pygame.Rect(SCREEN_W//2 - btn_w//2, 200 + i * (btn_h + 20), btn_w, btn_h))
            
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: return 'QUIT'
                if event.type == pygame.MOUSEBUTTONDOWN:
                    pos = pygame.mouse.get_pos()
                    for i, r in enumerate(rects):
                        if r.collidepoint(pos):
                            return self.options[i]
                            
            self.screen.fill((30, 30, 40))
            title = self.font.render("CHOOSE YOUR REWARD", True, (255, 215, 0))
            self.screen.blit(title, (SCREEN_W//2 - title.get_width()//2, 100))
            
            for i, r in enumerate(rects):
                pygame.draw.rect(self.screen, (60, 60, 80), r)
                pygame.draw.rect(self.screen, (255, 215, 0), r, 2)
                txt = self.small_font.render(self.options[i]["name"], True, (255, 255, 255))
                self.screen.blit(txt, (r.x + 20, r.y + 40))
                
            pygame.display.flip()

class BattleSystem:
    def __init__(self, screen, enemy_name, player_stats):
        self.screen = screen
        self.enemy_name = enemy_name
        self.player_stats = player_stats
        self.player_hp = player_stats.hp
        self.player_max_hp = player_stats.max_hp
        self.player_block = 0
        self.player_mana = 3
        
        self.enemy_hp = 40
        self.enemy_max_hp = 40
        self.enemy_intent = 10 
        
        # Use player's deck
        self.deck = list(player_stats.deck)
        random.shuffle(self.deck)
        self.hand = []
        self.discard = []
        
        self.font = pygame.font.SysFont(None, int(32 * SCALE_UNIFORM))
        self.small_font = pygame.font.SysFont(None, int(24 * SCALE_UNIFORM))
        
        self.card_w = int(120 * SCALE_UNIFORM)
        self.card_h = int(180 * SCALE_UNIFORM)
        
        self.state = 'PLAYER_TURN'
        
        self.draw_cards(3)

    def draw_cards(self, num):
        for _ in range(num):
            if not self.deck:
                self.deck = self.discard
                self.discard = []
                random.shuffle(self.deck)
            if self.deck:
                self.hand.append(self.deck.pop())

    def run(self):
        running = True
        clock = pygame.time.Clock()
        
        btn_w, btn_h = int(150 * SCALE_UNIFORM), int(50 * SCALE_UNIFORM)
        end_turn_btn = pygame.Rect(SCREEN_W - btn_w - 20, SCREEN_H - btn_h - 20, btn_w, btn_h)
        
        while running:
            delta_time = clock.tick(60) / 1000.0
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return 'QUIT'
                    
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mouse_pos = pygame.mouse.get_pos()
                    
                    if self.state == 'PLAYER_TURN':
                        if end_turn_btn.collidepoint(mouse_pos):
                            self.state = 'ENEMY_TURN'
                            continue
                            
                        hand_start_x = SCREEN_W // 2 - (len(self.hand) * (self.card_w + 10)) // 2
                        card_y = SCREEN_H - self.card_h - 20
                        
                        for i, card in enumerate(self.hand):
                            card_rect = pygame.Rect(hand_start_x + i * (self.card_w + 10), card_y, self.card_w, self.card_h)
                            if card_rect.collidepoint(mouse_pos):
                                if self.player_mana >= card.cost:
                                    self.player_mana -= card.cost
                                    if card.type == 'attack':
                                        self.enemy_hp -= card.value
                                    elif card.type == 'defend':
                                        self.player_block += card.value
                                        
                                    self.discard.append(self.hand.pop(i))
                                    
                                    if self.enemy_hp <= 0:
                                        reward = RewardScreen(self.screen, self.font, self.small_font).run()
                                        return ('WIN', reward)
                                break

            if self.state == 'ENEMY_TURN':
                self.screen.fill((40, 40, 50))
                msg = self.font.render("Enemy attacks for " + str(max(0, self.enemy_intent - self.player_block)) + "!", True, (255, 100, 100))
                self.screen.blit(msg, (SCREEN_W//2 - msg.get_width()//2, SCREEN_H//2))
                pygame.display.flip()
                pygame.time.delay(1000)
                
                dmg = max(0, self.enemy_intent - self.player_block)
                self.player_hp -= dmg
                
                # Sync health immediately so it's always up to date
                self.player_stats.hp = self.player_hp
                
                if self.player_hp <= 0:
                    return ('LOSE', None)
                    
                self.player_block = 0
                self.player_mana = 3
                self.enemy_intent = random.randint(5, 15)
                
                self.discard.extend(self.hand)
                self.hand = []
                self.draw_cards(3)
                
                self.state = 'PLAYER_TURN'

            self.screen.fill((40, 40, 50))
            
            pygame.draw.rect(self.screen, (100, 200, 100), (SCREEN_W//4, SCREEN_H//3, 100, 150))
            pygame.draw.rect(self.screen, (200, 100, 100), (SCREEN_W*3//4, SCREEN_H//3, 100, 150))
            
            p_text = self.font.render(f"HP: {self.player_hp}/{self.player_max_hp}  Block: {self.player_block}  Mana: {self.player_mana}/3", True, (255, 255, 255))
            e_text = self.font.render(f"{self.enemy_name}: {self.enemy_hp}/{self.enemy_max_hp}  Intent: {self.enemy_intent} dmg", True, (255, 200, 200))
            self.screen.blit(p_text, (20, 20))
            self.screen.blit(e_text, (SCREEN_W - e_text.get_width() - 20, 20))
            
            if self.state == 'PLAYER_TURN':
                pygame.draw.rect(self.screen, (200, 150, 50), end_turn_btn)
                btn_txt = self.font.render("End Turn", True, (0, 0, 0))
                self.screen.blit(btn_txt, (end_turn_btn.x + 20, end_turn_btn.y + 15))
                
                hand_start_x = SCREEN_W // 2 - (len(self.hand) * (self.card_w + 10)) // 2
                card_y = SCREEN_H - self.card_h - 20
                for i, card in enumerate(self.hand):
                    card_rect = pygame.Rect(hand_start_x + i * (self.card_w + 10), card_y, self.card_w, self.card_h)
                    color = (255, 100, 100) if card.type == 'attack' else (100, 100, 255)
                    pygame.draw.rect(self.screen, color, card_rect)
                    pygame.draw.rect(self.screen, (255, 255, 255), card_rect, 2)
                    
                    name_txt = self.small_font.render(card.name, True, (255, 255, 255))
                    val_txt = self.font.render(f"{card.value}", True, (255, 255, 255))
                    cost_txt = self.small_font.render(f"Cost: {card.cost}", True, (255, 255, 0))
                    
                    self.screen.blit(name_txt, (card_rect.x + 10, card_rect.y + 10))
                    self.screen.blit(val_txt, (card_rect.x + 40, card_rect.y + 70))
                    self.screen.blit(cost_txt, (card_rect.x + 10, card_rect.y + 140))
                
            pygame.display.flip()
