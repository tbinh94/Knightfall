import pygame
from config import SCREEN_W, SCREEN_H, SCALE_UNIFORM

class ShopSystem:
    def __init__(self, screen, player_stats):
        self.screen = screen
        self.player_stats = player_stats
        self.font = pygame.font.SysFont(None, int(32 * SCALE_UNIFORM))
        self.title_font = pygame.font.SysFont(None, int(48 * SCALE_UNIFORM))
        self.message = ""
        self.message_timer = 0
        
    def run(self):
        running = True
        btn_w, btn_h = int(240 * SCALE_UNIFORM), int(60 * SCALE_UNIFORM)
        
        # Shop items: (Name, Price)
        shop_items = [
            ("Iron Shield", 50),
            ("Sharpening Stone", 40),
            ("Leather Boots", 30)
        ]
        
        buttons = []
        for i, (name, price) in enumerate(shop_items):
            rect = pygame.Rect(SCREEN_W//2 - btn_w//2, 200 + i * (btn_h + 20), btn_w, btn_h)
            buttons.append((rect, name, price))
            
        leave_btn = pygame.Rect(SCREEN_W//2 - btn_w//2, SCREEN_H - 150, btn_w, btn_h)
        
        clock = pygame.time.Clock()
        
        while running:
            delta_time = clock.tick(60) / 1000.0
            if self.message_timer > 0:
                self.message_timer -= delta_time

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return 'QUIT'
                    
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mouse_pos = pygame.mouse.get_pos()
                    
                    for rect, name, price in buttons:
                        if rect.collidepoint(mouse_pos):
                            if self.player_stats.gold >= price:
                                self.player_stats.gold -= price
                                self.player_stats.items.append(name)
                                self.message = f"Bought {name}!"
                                self.message_timer = 2.0
                                # If item has immediate effect, apply it here
                                if name == "Sharpening Stone":
                                    self.player_stats.atk_bonus += 2
                                elif name == "Iron Shield":
                                    self.player_stats.add_max_hp(10)
                            else:
                                self.message = "Not enough gold!"
                                self.message_timer = 2.0
                        
                    if leave_btn.collidepoint(mouse_pos):
                        return 'DONE'
            
            self.screen.fill((30, 25, 40))
            
            # Draw overlay
            overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            self.screen.blit(overlay, (0, 0))
            
            title = self.title_font.render("Traveling Warrior Merchant", True, (255, 200, 100))
            self.screen.blit(title, (SCREEN_W//2 - title.get_width()//2, 80))
            
            gold_txt = self.font.render(f"Your Gold: {self.player_stats.gold}", True, (255, 215, 0))
            self.screen.blit(gold_txt, (SCREEN_W//2 - gold_txt.get_width()//2, 140))
            
            for rect, name, price in buttons:
                color = (100, 100, 120)
                if rect.collidepoint(pygame.mouse.get_pos()):
                    color = (150, 150, 180)
                pygame.draw.rect(self.screen, color, rect, border_radius=10)
                pygame.draw.rect(self.screen, (200, 200, 200), rect, 2, border_radius=10)
                
                txt = self.font.render(f"{name} ({price} G)", True, (255, 255, 255))
                self.screen.blit(txt, (rect.centerx - txt.get_width()//2, rect.centery - txt.get_height()//2))
            
            # Leave button
            color = (80, 40, 40)
            if leave_btn.collidepoint(pygame.mouse.get_pos()):
                color = (120, 60, 60)
            pygame.draw.rect(self.screen, color, leave_btn, border_radius=10)
            pygame.draw.rect(self.screen, (200, 200, 200), leave_btn, 2, border_radius=10)
            txt_leave = self.font.render("Leave", True, (255, 255, 255))
            self.screen.blit(txt_leave, (leave_btn.centerx - txt_leave.get_width()//2, leave_btn.centery - txt_leave.get_height()//2))
            
            # Message
            if self.message_timer > 0:
                msg_txt = self.font.render(self.message, True, (255, 255, 255))
                self.screen.blit(msg_txt, (SCREEN_W//2 - msg_txt.get_width()//2, SCREEN_H - 80))
                
            pygame.display.flip()
