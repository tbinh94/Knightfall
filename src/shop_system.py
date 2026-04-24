import pygame
from config import SCREEN_W, SCREEN_H, SCALE_UNIFORM

class ShopSystem:
    def __init__(self, screen):
        self.screen = screen
        self.font = pygame.font.SysFont(None, int(32 * SCALE_UNIFORM))
        self.title_font = pygame.font.SysFont(None, int(48 * SCALE_UNIFORM))
        
    def run(self):
        running = True
        
        btn_w, btn_h = int(200 * SCALE_UNIFORM), int(60 * SCALE_UNIFORM)
        
        heal_btn = pygame.Rect(SCREEN_W//2 - btn_w//2, SCREEN_H//2 - 50, btn_w, btn_h)
        leave_btn = pygame.Rect(SCREEN_W//2 - btn_w//2, SCREEN_H//2 + 50, btn_w, btn_h)
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return 'QUIT'
                    
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mouse_pos = pygame.mouse.get_pos()
                    
                    if heal_btn.collidepoint(mouse_pos):
                        # Simple placeholder logic
                        print("Bought Heal!")
                        return 'HEALED'
                        
                    if leave_btn.collidepoint(mouse_pos):
                        return 'DONE'
            
            self.screen.fill((50, 40, 60))
            
            title = self.title_font.render("Mysterious Merchant", True, (255, 200, 100))
            self.screen.blit(title, (SCREEN_W//2 - title.get_width()//2, 100))
            
            pygame.draw.rect(self.screen, (100, 255, 100), heal_btn)
            pygame.draw.rect(self.screen, (200, 200, 200), leave_btn)
            
            txt_heal = self.font.render("Heal (Free)", True, (0,0,0))
            txt_leave = self.font.render("Leave", True, (0,0,0))
            
            self.screen.blit(txt_heal, (heal_btn.x + 40, heal_btn.y + 20))
            self.screen.blit(txt_leave, (leave_btn.x + 60, leave_btn.y + 20))
            
            pygame.display.flip()
