import pygame
import sys
from config import *
from assets_manager import LOADED_THEMES, load_assets
from enemy_manager import LOADED_ENEMIES, load_enemies
from decoy_manager import LOADED_DECOYS, load_decoys
from player_stats import PlayerStats
from game_states import PlayingState, GameOverState

if 'PLAYER_TARGET_X' not in globals():
    PLAYER_TARGET_X = SCREEN_W // 3

def initialize_pygame_and_assets():
    if not pygame.get_init():
        pygame.init()
    
    if hasattr(sys.modules.get('config'), 'print_resolution_info'):
        from config import print_resolution_info
        print_resolution_info()
    
    if not LOADED_THEMES: load_assets()
    if not LOADED_ENEMIES: load_enemies()
    if not LOADED_DECOYS: load_decoys()

class Game:
    def __init__(self, screen, level_file):
        initialize_pygame_and_assets()
        self.screen = screen
        pygame.display.set_caption(f"Parkour Game - {level_file}")
        self.clock = pygame.time.Clock()
        self.running = True
        self.game_status = 'QUIT'
        self.font = pygame.font.SysFont(None, 32)
        
        self.player_stats = PlayerStats()
        
        self.states = {
            "playing": PlayingState(self, level_file), 
            "game_over": GameOverState(self)
        }
        self.current_state_name = "playing"
        self.current_state = self.states[self.current_state_name]
        self.current_state.enter_state()

    def flip_state(self, new_state_name):
        self.current_state.exit_state()
        self.current_state_name = new_state_name
        self.current_state = self.states[self.current_state_name]
        self.current_state.enter_state()

    def run(self):
        while self.running:
            delta_time = self.clock.tick(FPS) / 1000.0
            
            events = pygame.event.get()
            self.current_state.handle_events(events)
            self.current_state.update(delta_time)
            self.current_state.draw(self.screen)
            pygame.display.flip()
            
        return self.game_status
