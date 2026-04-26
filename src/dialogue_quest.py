import pygame
from config import SCREEN_W, SCREEN_H

class DialogueSystem:
    def __init__(self, screen, font):
        self.screen = screen
        self.font = font
        self.active = False
        self.messages = []
        self.msg_index = 0
        self.callback = None
        
    def start_dialogue(self, messages, callback=None):
        self.messages = messages
        self.msg_index = 0
        self.active = True
        self.callback = callback
        
    def next_msg(self):
        self.msg_index += 1
        if self.msg_index >= len(self.messages):
            self.active = False
            if self.callback: self.callback()
            
    def draw(self):
        if not self.active: return
        # Draw semi-transparent box
        box_rect = pygame.Rect(50, SCREEN_H - 150, SCREEN_W - 100, 120)
        pygame.draw.rect(self.screen, (20, 20, 30, 200), box_rect)
        pygame.draw.rect(self.screen, (255, 215, 0), box_rect, 2)
        
        # Draw current message
        txt = self.font.render(self.messages[self.msg_index], True, (255, 255, 255))
        self.screen.blit(txt, (box_rect.x + 20, box_rect.y + 30))
        
        prompt = self.font.render("Press SPACE to continue...", True, (200, 200, 200))
        self.screen.blit(prompt, (box_rect.right - 250, box_rect.bottom - 40))

class QuestManager:
    def __init__(self):
        self.objectives = [
            {"id": "reach_3k", "desc": "Explore the ruins (Reach 3000m)", "target": 3000, "current": 0, "completed": False}
        ]
    
    def update(self, distance):
        for q in self.objectives:
            if not q["completed"]:
                q["current"] = distance
                if q["current"] >= q["target"]:
                    q["completed"] = True
                pass # Removed log

    def draw_hud(self, screen, font):
        y = 120
        for q in self.objectives:
            color = (100, 255, 100) if q["completed"] else (255, 255, 255)
            status = "[DONE]" if q["completed"] else f"({int(q['current'])}/{q['target']}m)"
            txt = font.render(f"Quest: {q['desc']} {status}", True, color)
            screen.blit(txt, (20, y))
            y += 30
