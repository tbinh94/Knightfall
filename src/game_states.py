import pygame
import math
import random
from collections import deque
from config import *
from terrain import load_level, EndlessManager, TerrainGenerator, ObstacleSprite, collide_player_hitbox
from dialogue_quest import DialogueSystem, QuestManager
from player import Player
from enemy_manager import LOADED_ENEMIES, get_random_enemy, Enemy
from decoy_manager import LOADED_DECOYS, get_random_decoy
from background import ForestBackground, GothicBackground
from shop_system import ShopSystem
from assets_manager import LOADED_THEMES

class GameState:
    def __init__(self, game): 
        self.game = game
    def handle_events(self, events): pass
    def update(self, delta_time): pass
    def draw(self, screen): pass
    def enter_state(self): pass
    def exit_state(self): pass

class PlayingState(GameState):
    def __init__(self, game, level_file):
        super().__init__(game)
        self.level_file = level_file
        try: 
            level_data = load_level(self.level_file)
        except Exception:
            level_data = load_level(DEFAULT_LEVEL)
            
        self.is_endless = level_data["is_endless"]
        theme_name = level_data["theme"]
        self.active_segments = deque()
        self.cursor_x = 0
        
        if self.is_endless:
            self.endless_manager = EndlessManager(level_data["patterns"], level_data["spawn_logic"])
            self.world_data = None
            self.level_length = -1
            self.current_run_speed = RUN_SPEED 
        else:
            self.endless_manager = None
            self.world_data = level_data["world"]
            self.level_length = level_data["length"]
            self.current_run_speed = RUN_SPEED
            
        if theme_name in ["dark_forest", "forest", "nature"]:
            self.background = ForestBackground()
        else:
            self.background = GothicBackground()

        self.active_theme_tiles = LOADED_THEMES.get(theme_name)
        if not self.active_theme_tiles:
            self.active_theme_tiles = next(iter(LOADED_THEMES.values())) if LOADED_THEMES else None
            
        self.all_sprites = pygame.sprite.LayeredUpdates()
        self.real_obstacles = pygame.sprite.Group()
        self.fake_obstacles = pygame.sprite.Group()
        
        self.player = Player(PLAYER_TARGET_X, GROUND_Y)
        self.world_x_offset = 0
        self.visible_platforms = [] 
        self.visible_walls = []
        self.visible_wall_tiles = []
        self.platform_surfaces = {}
        
        self.dialogue = DialogueSystem(self.game.screen, pygame.font.SysFont(None, 32))
        self.quests = QuestManager()
        
        self.visibility_mult = 1.0
        self.boss_active = False
        self.boss_instance = None
        self.level_phase = 1

    def enter_state(self):
        pygame.mouse.set_visible(True)
        self.all_sprites.empty()
        self.real_obstacles.empty()
        self.fake_obstacles.empty()
        
        self.player.hitbox.x = PLAYER_TARGET_X
        self.player.hitbox.bottom = GROUND_Y
        self.player.vy = 0
        self.player.vx = 0
        self.player.on_ground = True
        self.player.state = 'run'
        self.player.current_frame = 0
        self.player.anim_timer = 0.0
        self.player.wall_state.reset()
        self.player.jump_queued = False
        self.player.heal_charges = 3
        self.all_sprites.add(self.player)
        
        if self.game.player_stats.hp <= 0:
            self.game.player_stats.hp = self.game.player_stats.max_hp
        
        self.world_x_offset = 0
        self.current_run_speed = RUN_SPEED
        self.platform_surfaces.clear()

        if self.is_endless:
            self.active_segments.clear()
            self.cursor_x = 0
            
            first_plat_y = GROUND_Y
            if self.endless_manager and self.endless_manager.patterns:
                first_plat_y = self.endless_manager.patterns[0].get("platform_y", GROUND_Y)
                if first_plat_y == "ground": first_plat_y = GROUND_Y

            safe_obstacles = [{"x": i, "kind": "decor"} for i in range(100, SAFE_ZONE_DISTANCE, 200)]
            safe_zone_config = {"type": "straight", "platform_y": first_plat_y, 
                              "length": SAFE_ZONE_DISTANCE, "obstacles": safe_obstacles}
            safe_segment = TerrainGenerator.straight(self.cursor_x, safe_zone_config)
            self.active_segments.append(safe_segment)
            self.cursor_x += SAFE_ZONE_DISTANCE
            
            while self.cursor_x < self.world_x_offset + SCREEN_W * 4.0:
                self._spawn_next_segment()

        else:
            self.player.hitbox.bottom = GROUND_Y
            self.player.pos_y = float(self.player.hitbox.y)
            self._create_fixed_level()
            
        initial_segments = self.active_segments if self.is_endless else self.world_data
        all_platforms = []
        for seg in initial_segments:
            platforms_in_seg = seg.get("platforms", [seg.get("platform")])
            for p in platforms_in_seg:
                if p:
                    all_platforms.append(p)
        
        self.visible_platforms.clear()
        self.visible_platforms.extend(all_platforms)

        player_on_platform = False
        if all_platforms:
            for p in all_platforms:
                if p.x <= self.player.hitbox.centerx < p.x + p.length:
                    self.player.hitbox.bottom = p.y
                    self.player.pos_y = float(self.player.hitbox.y)
                    self.player.on_ground = True
                    self.player.vy = 0
                    player_on_platform = True
                    break
            
            if not player_on_platform:
                first_platform_y = all_platforms[0].y
                self.player.hitbox.bottom = first_platform_y
                self.player.pos_y = float(self.player.hitbox.y)
                self.player.on_ground = True
                self.player.vy = 0
        
        self.player.rect.midbottom = self.player.hitbox.midbottom

    def _create_fixed_level(self):
        for seg in self.world_data:
            for ob_data in seg.get("obstacles", []): 
                self._create_obstacle_sprite(ob_data)

    def _spawn_next_segment(self):
        pattern = self.endless_manager.get_next_pattern()
        if not pattern: return
        
        terrain_type = pattern.get("type", "straight")
        terrain_func = getattr(TerrainGenerator, terrain_type, TerrainGenerator.straight)
        segment = terrain_func(self.cursor_x, pattern)
        for ob_data in segment.get("obstacles", []): 
            self._create_obstacle_sprite(ob_data)
        self.active_segments.append(segment)
        self.cursor_x += segment["length"]
        
    def _create_obstacle_sprite(self, ob_data):
        sprite_type = ob_data.sprite_type
        if not sprite_type:
            if ob_data.kind == 'real' and LOADED_ENEMIES: 
                sprite_type = get_random_enemy()
            elif ob_data.kind in ['fake', 'decor'] and LOADED_DECOYS: 
                if ob_data.kind == 'fake':
                    lore_text = ob_data.get("text")
                    if ob_data.x > 400:
                        rand_val = random.random()
                        if rand_val < 0.20:
                            sprite_type = 'pillar'
                        elif rand_val < 0.40: 
                            sprite_type = 'warrior'
                        else:
                            sprite_type = 'wall'
                    else:
                        sprite_type = 'wall'
                else:
                    available = [k for k in LOADED_DECOYS.keys() if k not in ['pillar', 'warrior']]
                    if available:
                        sprite_type = random.choice(available)
                    else:
                        sprite_type = get_random_decoy()
                
        obstacle_sprite = ObstacleSprite(ob_data.x, ob_data.y, ob_data.kind, sprite_type=sprite_type, lore_text=ob_data.text)
        if ob_data.kind == 'real': 
            self.real_obstacles.add(obstacle_sprite)
        elif ob_data.kind == 'fake' or sprite_type in ['pillar', 'warrior']: 
            self.fake_obstacles.add(obstacle_sprite)
        self.all_sprites.add(obstacle_sprite)
        
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.QUIT: 
                self.game.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE: 
                    if self.dialogue.active:
                        self.dialogue.next_msg()
                    else:
                        self.player.jump()
                if event.key == pygame.K_f or event.key == pygame.K_j:
                    if not self.player.stomp():
                        self.player.attack()
                if event.key == pygame.K_h:
                    self.player.heal(self.game.player_stats)
                if event.key == pygame.K_s or event.key == pygame.K_DOWN:
                    if not self.player.on_ground:
                        self.player.stomp()
                if event.key == pygame.K_v:
                    self.player.roll()
                if event.key == pygame.K_ESCAPE: 
                    self.game.running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    self.player.attack()
                elif event.button == 3:
                    self.player.stomp()

    def update(self, delta_time):
        if self.player.state == 'death':
            self.player.update([], self.world_x_offset, delta_time)
            death_anim = self.player.animations['death']
            if self.player.current_frame >= len(death_anim['frames']) - 1:
                pygame.time.delay(500)
                self.game.flip_state("game_over")
            return
            
        self.current_run_speed = 0
        
        self.visible_platforms.clear()
        self.visible_walls.clear()
        self.visible_wall_tiles.clear()
        
        stomp_hitbox = self.player._get_stomp_hitbox(self.world_x_offset)
        if stomp_hitbox:
            for obs in self.real_obstacles:
                if stomp_hitbox.colliderect(obs.rect):
                    if hasattr(obs, 'hp'):
                        if not hasattr(self.player, 'hit_enemies'):
                            self.player.hit_enemies = set()
                        if obs not in self.player.hit_enemies:
                            self.player.hit_enemies.add(obs)
                            damage = 10 + getattr(self.game.player_stats, 'atk_bonus', 0)
                            obs.hp -= damage
                            if obs.hp <= 0:
                                obs.kill()
                                self.game.player_stats.gold += 50
                            else:
                                if hasattr(obs, 'change_state'):
                                    obs.change_state("hit")
                                    obs.stun_timer = 1.0
                    else:
                        self.game.player_stats.gold += 15
                        obs.kill()
                    self.player.vy = STOMP_BOUNCE_V
                    self.player.is_stomping = False
                    self.player.stomp_phase = None
                    self.player.stomp_cooldown_timer = STOMP_COOLDOWN
                    break

        segments_to_draw = self.active_segments if self.is_endless else self.world_data

        for seg in segments_to_draw:
            for tile in seg.get("wall_tiles", []):
                self.visible_wall_tiles.append(tile)
            
            platforms = seg.get("platforms", [seg.get("platform")])
            for p in platforms:
                if p is None: 
                    continue
                
                if self.active_theme_tiles and self.active_theme_tiles.get('wall_top_middle'):
                    tile_size = self.active_theme_tiles.get('wall_top_middle').get_width()
                    if tile_size > 0:
                        num_tiles_x = max(1, round(p.length / tile_size))
                        p.length = num_tiles_x * tile_size

                x_on_screen = p.x - self.world_x_offset
                if x_on_screen + p.length < -200 or x_on_screen > SCREEN_W + 200:
                    continue
                
                self.visible_platforms.append(p)
        
        wall_check = self.player.update(
            self.visible_platforms, 
            self.world_x_offset, 
            delta_time, 
            wall_tiles=self.visible_wall_tiles,
            current_run_speed=self.current_run_speed
        )
        
        current_screen_x = self.player.hitbox.x
        diff = current_screen_x - PLAYER_TARGET_X
        self.world_x_offset += diff
        self.player.hitbox.x = PLAYER_TARGET_X
        self.player.rect.midbottom = self.player.hitbox.midbottom
        current_anim = self.player.animations[self.player.state]
        self.player.rect.y += int(current_anim.get('y_offset', 0))

        if wall_check == "WALL_TIME_EXCEEDED":
            self.game.flip_state("game_over")
            return
        
        for sprite in self.all_sprites:
            if sprite != self.player:
                if isinstance(sprite, ObstacleSprite):
                    # Optimize: only update if close to screen to fix lag and unwanted patrol drifting
                    screen_x = sprite.world_pos.x - self.world_x_offset
                    if -SCREEN_W <= screen_x <= SCREEN_W * 2:
                        sprite.update(self.world_x_offset, delta_time, player_pos=self.player.hitbox)
                else:
                    sprite.update(self.world_x_offset, delta_time)

        
        real_collisions = pygame.sprite.spritecollide(self.player, self.real_obstacles, False, collided=collide_player_hitbox)
        if real_collisions and self.player.state != 'death':
            player_took_damage = False
            for obs in real_collisions:
                # Check for player invincibility
                is_invincible = False
                if self.player.is_rolling:
                    is_invincible = True
                if hasattr(self.player, 'invincible_timer') and self.player.invincible_timer > 0:
                    is_invincible = True

                if self.player.is_attacking or (self.player.is_stomping and self.player.stomp_phase == 'dive'):
                    if hasattr(obs, 'hp'):
                        if not hasattr(self.player, 'hit_enemies'):
                            self.player.hit_enemies = set()
                        
                        if obs not in self.player.hit_enemies:
                            self.player.hit_enemies.add(obs)
                            if self.player.is_stomping:
                                damage = 10 + getattr(self.game.player_stats, 'atk_bonus', 0)
                            else:
                                damage = 20 + getattr(self.game.player_stats, 'atk_bonus', 0)
                            obs.hp -= damage  # Player attack damage
                            if obs.hp <= 0:
                                obs.kill()
                                self.game.player_stats.gold += 50
                            else:
                                if hasattr(obs, 'change_state'):
                                    obs.change_state("hit")
                                    obs.stun_timer = 1.0
                    else:
                        self.game.player_stats.gold += 10
                        obs.kill()
                else:
                    if not is_invincible and not player_took_damage:
                        player_took_damage = True
                        # Player takes damage from enemy collision
                        if hasattr(obs, 'hp') and obs.hp > 0:
                            self.game.player_stats.hp -= 10  # Enemy damage (reduced from 15)
                            self.player.invincible_timer = 800  # 0.8s invincible
                        else:
                            self.game.player_stats.hp -= 10  # Trap damage
                            self.player.invincible_timer = 800

                        if self.game.player_stats.hp <= 0:
                            self.player.state = 'death'
                            self.player.current_frame = 0
                            self.player.vx = 0
                            self.game.player_stats.hp = 0
                            break
                        else:
                            # Optional knockback on taking damage
                            self.player.vx = -5 if self.player.facing_right else 5
                            self.player.vy = -3
                            self.player.on_ground = False
            return


        # --- HEALTH & FALL BOUNDS VALIDATION ---
        if self.player.hitbox.top > SCREEN_H + 100 or self.game.player_stats.hp <= 0:
            if self.player.state != 'death':
                self.player.state = 'death'
                self.player.current_frame = 0
                self.player.vx = 0
                self.game.player_stats.hp = 0

        self.interaction_prompt = None
        keys = pygame.key.get_pressed()
        
        interaction_zone = self.player.hitbox.inflate(100, 50)
        
        for obs in self.fake_obstacles:
            if interaction_zone.colliderect(obs.rect):
                if obs.sprite_type == 'pillar' and not obs.is_used:
                    self.interaction_prompt = "Press E to Heal at Shrine"
                    if keys[pygame.K_e]:
                        heal_amount = self.game.player_stats.hp * 0.2
                        self.game.player_stats.add_hp(heal_amount)
                        obs.is_used = True
                        break
                elif obs.sprite_type == 'warrior':
                    self.interaction_prompt = "Press E to Trade with Warrior"
                    if keys[pygame.K_e]:
                        msgs = [
                            "Warrior: Halt, traveler!",
                            "Warrior: I've found some rare artifacts in these ruins.",
                            "Warrior: Do you have gold to trade?"
                        ]
                        def open_shop():
                            shop = ShopSystem(self.game.screen, self.game.player_stats)
                            res = shop.run()
                            obs.kill()
                            if res == 'QUIT': self.game.running = False
                            
                        self.dialogue.start_dialogue(msgs, open_shop)
                        break
                
                if obs.sprite_type == 'lore_popup' and not obs.is_used:
                    lore_text = getattr(obs, 'lore_text', "Use A/D to move, Space to Jump, J to Attack")
                    self.interaction_prompt = f"Lore: {lore_text}"
                
                if obs.sprite_type == 'dead_knight' and not obs.is_used:
                    self.interaction_prompt = "Examine Fallen Knight (E)"
                    if keys[pygame.K_e]:
                        self.dialogue.start_dialogue(["A fallen warrior... his armor is rusted through.", "\"They came from beneath...\" is carved into the hilt of his sword."], None)
                        obs.is_used = True

                if obs.sprite_type == 'boss_trigger' and not self.boss_active:
                    self.boss_active = True
                    self.dialogue.start_dialogue(["The ground tremors...", "The Rooted Knight rises from the decay!"], None)
                    for boss_obs in self.real_obstacles:
                        if boss_obs.sprite_type == 'rooted_knight_boss':
                            self.boss_instance = boss_obs
                            self.boss_instance.hp = 80
                            self.boss_instance.max_hp = 80
                            break

        self.quests.update(self.world_x_offset)

        if self.player.state == 'death':
            death_anim = self.player.animations['death']
            if self.player.current_frame >= len(death_anim['frames']) - 1:
                self.game.flip_state("game_over")
                return

        if self.world_x_offset > 2500:
            self.level_phase = 4
        elif self.world_x_offset > 1500:
            self.level_phase = 3
            target_vis = 0.4
            if self.visibility_mult > target_vis:
                self.visibility_mult -= delta_time * 0.1
        elif self.world_x_offset > 500:
            self.level_phase = 2

        if keys[pygame.K_LSHIFT] or keys[pygame.K_k]:
            self.player.dash()

        if self.boss_active and self.boss_instance:
            if not self.boss_instance.alive():
                self.boss_active = False
                self.player.can_dash = True
                self.dialogue.start_dialogue(["The Rooted Knight has been cleansed.", "You feel a surge of energy! Skill Unlocked: DASH (LSHIFT)"], None)
            else:
                dist = self.boss_instance.world_pos.x - (self.world_x_offset + self.player.hitbox.x)
                if abs(dist) > 100:
                    self.boss_instance.world_pos.x -= (20 * delta_time) if dist > 0 else -(20 * delta_time)
                
                if abs(dist) < 400 and random.random() < 0.01:
                    spike_x = self.world_x_offset + self.player.hitbox.x + random.randint(-100, 100)
                    spike = ObstacleSprite(spike_x, GROUND_Y, kind='real', sprite_type='spiked_barricade')
                    self.real_obstacles.add(spike)
                    self.all_sprites.add(spike)

        if self.is_endless:
            if self.cursor_x < self.world_x_offset + SCREEN_W * 4.0:
                self._spawn_next_segment()

            if self.active_segments:
                first_seg = self.active_segments[0]
                platforms = first_seg.get("platforms", [first_seg.get("platform")])
                if platforms and platforms[-1] and platforms[-1].x + platforms[-1].length < self.world_x_offset - 200:
                    self.active_segments.popleft()
            for sprite in list(self.all_sprites):
                if not isinstance(sprite, Player) and sprite.world_pos.x < self.world_x_offset - 200:
                    sprite.kill()
        else:
            if self.world_x_offset >= self.level_length - PLAYER_W:
                self.game.game_status = 'COMPLETED'
                self.game.running = False
                return
                    
    def draw(self, screen):
        bg_surface = pygame.Surface((SCREEN_W, SCREEN_H))
        bg_surface.fill((30, 30, 40))
        
        if self.background:
            self.background.draw(bg_surface, self.world_x_offset, self.level_length)

        if self.visibility_mult < 1.0:
            dark_overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            alpha = int(255 * (1.0 - self.visibility_mult))
            dark_overlay.fill((0, 0, 0, alpha))
            bg_surface.blit(dark_overlay, (0, 0))

        screen.blit(bg_surface, (0, 0))

        if not self.active_theme_tiles:
            self.draw_platforms_fallback(screen)
            self.all_sprites.draw(screen)
            return

        if hasattr(self.background, 'tiles') and self.background.tiles:
            g_tiles = self.background.tiles
            tile_top_left = pygame.transform.scale(g_tiles[3][0], (32, 32))
            tile_top_middle = pygame.transform.scale(g_tiles[3][1], (32, 32))
            tile_top_right = pygame.transform.scale(g_tiles[3][2], (32, 32))
            tile_middle_left = pygame.transform.scale(g_tiles[2][0], (32, 32))
            tile_middle_right = pygame.transform.scale(g_tiles[2][2], (32, 32))
            tile_fill = pygame.transform.scale(g_tiles[2][1], (32, 32))
        else:
            tile_top_left = self.active_theme_tiles.get('wall_top_left')
            tile_top_middle = self.active_theme_tiles.get('wall_top_middle')
            tile_top_right = self.active_theme_tiles.get('wall_top_right')
            tile_middle_left = self.active_theme_tiles.get('wall_middle_left')
            tile_middle_right = self.active_theme_tiles.get('wall_middle_right')
            tile_fill = self.active_theme_tiles.get('wall_fill') 
        
        essential_tiles = [tile_top_left, tile_top_middle, tile_top_right, 
                          tile_middle_left, tile_middle_right]
        if not all(essential_tiles):
            self.draw_platforms_fallback(screen)
            self.all_sprites.draw(screen)
            self.game.player_stats.draw_hud(screen, self.game.font)
            return

        tile_size = tile_top_middle.get_width()
        if tile_size == 0: 
            return

        for p in self.visible_platforms:
            x_on_screen = p.x - self.world_x_offset
            plat_key = (p.length, p.y)
            if plat_key not in self.platform_surfaces:
                tile_size = tile_top_middle.get_width()
                num_tiles_x = max(1, round(p.length / tile_size))
                height_needed = SCREEN_H - p.y
                num_tiles_y = math.ceil(height_needed / tile_size) + 1
                
                actual_w = num_tiles_x * tile_size
                plat_surf = pygame.Surface((actual_w, num_tiles_y * tile_size), pygame.SRCALPHA)
                
                for i in range(num_tiles_x):
                    tile = tile_top_middle
                    if num_tiles_x > 1:
                        if i == 0: tile = tile_top_left
                        elif i == num_tiles_x - 1: tile = tile_top_right
                    if tile: plat_surf.blit(tile, (i * tile_size, 0))
                
                for j in range(1, num_tiles_y):
                    if num_tiles_x > 1:
                        plat_surf.blit(tile_middle_left, (0, j * tile_size))
                        if tile_fill:
                            for i in range(1, num_tiles_x - 1):
                                plat_surf.blit(tile_fill, (i * tile_size, j * tile_size))
                        plat_surf.blit(tile_middle_right, ((num_tiles_x - 1) * tile_size, j * tile_size))
                    else:
                        plat_surf.blit(tile_middle_left, (0, j * tile_size))
                
                final_w = p.length
                final_surf = pygame.Surface((final_w, num_tiles_y * tile_size), pygame.SRCALPHA)
                final_surf.blit(plat_surf, (0, 0))
                self.platform_surfaces[plat_key] = final_surf
            
            screen.blit(self.platform_surfaces[plat_key], (x_on_screen, p.y))

        for wall_tile in self.visible_wall_tiles:
            if wall_tile.width != 10: 
                continue

            wall_screen_x = wall_tile.x - self.world_x_offset
            wall_screen_y = wall_tile.y
            
            wall_rect = pygame.Rect(
                wall_screen_x,
                wall_screen_y,
                wall_tile.width,
                wall_tile.tile_height
            )
            
            if wall_rect.right < 0 or wall_rect.left > SCREEN_W:
                continue
            if wall_rect.bottom < 0 or wall_rect.top > SCREEN_H:
                continue
            
            tile_to_use = self.active_theme_tiles.get('wall_middle_left')
            if tile_to_use:
                scaled_tile = pygame.transform.scale(tile_to_use, 
                                                     (wall_tile.width, wall_tile.tile_height))
                screen.blit(scaled_tile, (int(wall_rect.x), int(wall_rect.y)))
            else:
                pygame.draw.rect(screen, (100, 100, 80), wall_rect)

        self.all_sprites.draw(screen)
        
        # Draw health bars for enemies
        for sprite in self.all_sprites:
            if isinstance(sprite, Enemy) and not hasattr(sprite, 'is_player'):  # Exclude player
                self.draw_enemy_health_bar(screen, sprite)
        
        self.game.player_stats.draw_hud(screen, self.game.font)

        if self.player.wall_state.is_sliding:
            wall_time_ratio = self.player.wall_state.time_elapsed / WALL_CLIMB_TIME_LIMIT
            bar_width, bar_height = int(200 * SCALE_X), int(20 * SCALE_Y)
            bar_x, bar_y = SCREEN_W // 2 - bar_width // 2, int(30 * SCALE_Y)
            
            pygame.draw.rect(screen, (50, 50, 50), (bar_x, bar_y, bar_width, bar_height))
            
            color = (0, 200, 0)
            if wall_time_ratio >= WALL_CLIMB_WARNING_TIME / WALL_CLIMB_TIME_LIMIT:
                color = (255, 100, 0) if wall_time_ratio < 0.8 else (255, 0, 0)
            
            current_bar_width = min(bar_width, bar_width * wall_time_ratio)
            pygame.draw.rect(screen, color, (bar_x, bar_y, current_bar_width, bar_height))
            pygame.draw.rect(screen, (200, 200, 200), (bar_x, bar_y, bar_width, bar_height), 2)
            
            font_size = int(16 * SCALE_UNIFORM)
            font = pygame.font.SysFont(None, font_size)
            text = font.render(f"Wall Time: {self.player.wall_state.time_elapsed:.1f}s", 
                             True, (200, 200, 200))
            screen.blit(text, (bar_x, bar_y - int(25 * SCALE_Y)))

        self.quests.draw_hud(self.game.screen, self.game.font)
        self.dialogue.draw()
        
        if self.interaction_prompt and not self.dialogue.active:
            prompt_text = self.game.font.render(self.interaction_prompt, True, (255, 255, 255))
            prompt_x = self.player.rect.centerx - prompt_text.get_width() // 2
            prompt_y = self.player.rect.top - 60
            
            bg_rect = pygame.Rect(prompt_x - 10, prompt_y - 5, prompt_text.get_width() + 20, prompt_text.get_height() + 10)
            pygame.draw.rect(screen, (0, 0, 0, 180), bg_rect, border_radius=5)
            pygame.draw.rect(screen, (255, 255, 100), bg_rect, 2, border_radius=5)
            
            screen.blit(prompt_text, (prompt_x, prompt_y))

    def draw_platforms_fallback(self, screen):
        segments_to_draw = self.active_segments if self.is_endless else self.world_data
        for seg in segments_to_draw:
            platforms = seg.get("platforms", [seg.get("platform")])
            for p in platforms:
                if p is None: continue
                pygame.draw.rect(screen, (80,80,80), 
                               (p.x - self.world_x_offset, p.y, p.length, 6))

    def draw_enemy_health_bar(self, screen, enemy):
        """Draw health bar above enemy"""
        if enemy.hp <= 0:
            return
        
        bar_width = 40
        bar_height = 5
        bar_x = enemy.rect.centerx - bar_width // 2
        bar_y = enemy.rect.top - 15
        
        # Background
        pygame.draw.rect(screen, (50, 50, 50), (bar_x, bar_y, bar_width, bar_height))
        
        # Health
        health_ratio = enemy.hp / enemy.max_hp
        health_width = int(bar_width * health_ratio)
        color = (0, 255, 0) if health_ratio > 0.5 else (255, 255, 0) if health_ratio > 0.25 else (255, 0, 0)
        pygame.draw.rect(screen, color, (bar_x, bar_y, health_width, bar_height))
        
        # Border
        pygame.draw.rect(screen, (200, 200, 200), (bar_x, bar_y, bar_width, bar_height), 1)

class GameOverState(GameState):
    def __init__(self, game):
        super().__init__(game)
        font_size_large = int(60 * SCALE_UNIFORM)
        font_size_small = int(30 * SCALE_UNIFORM)
        self.font_large = pygame.font.SysFont(None, font_size_large)
        self.text_game_over = self.font_large.render("GAME OVER", True, (255, 60, 60))
        self.text_rect = self.text_game_over.get_rect(center=(SCREEN_W/2, SCREEN_H/2 - 40))
        self.font_small = pygame.font.SysFont(None, font_size_small)
        self.instr_text = self.font_small.render("Press ENTER to Restart | ESC for Menu", 
                                                 True, (200, 200, 200))
        self.instr_rect = self.instr_text.get_rect(center=(SCREEN_W/2, SCREEN_H/2 + 20))

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.QUIT: 
                self.game.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN: 
                    self.game.flip_state("playing")
                if event.key == pygame.K_ESCAPE: 
                    self.game.running = False

    def draw(self, screen):
        screen.fill((10, 10, 10))
        screen.blit(self.text_game_over, self.text_rect)
        screen.blit(self.instr_text, self.instr_rect)
