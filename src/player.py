import pygame
from config import *
from terrain import WallState

class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self._layer = 2
        self.vx = 0
        self.vy = 0
        self.on_ground = True
        self.state = 'run'
        self.current_frame = 0
        self.anim_timer = 0.0
        self.animations = {}
        self.wall_state = WallState()
        self.facing_right = True
        self.double_jump_available = True
        self.jump_queued = False
        self.is_hanging = False
        self.hanging_side = None
        self.hanging_y = 0
        self.is_crouching = False
        self.is_attacking = False
        self.attack_timer = 0
        self.attack_duration = 400
        self.attack_combo = 0
        self.invincible_timer = 0.0
        
        self.dash_cooldown = 0
        self.dash_timer = 0
        self.is_dashing = False
        self.can_dash = False
        
        self.is_rolling = False
        self.roll_timer = 0
        self.roll_cooldown = 0
        
        self.is_stomping = False
        self.stomp_phase = None
        self.stomp_timer = 0.0
        self.stomp_cooldown_timer = 0.0
        
        self.is_healing = False
        
        for anim_name, anim_cfg in ANIMATION_CONFIG.items():
            self.animations[anim_name] = self.load_spritesheet(
                anim_cfg['file'], anim_cfg['frames'], anim_cfg['frame_width'],
                anim_cfg['frame_height'], anim_cfg['scale'], anim_cfg['speed'],
                anim_cfg.get('y_offset', 0), anim_cfg.get('start_frame', 0)
            )
        self.image = self.animations[self.state]['frames'][self.current_frame]
        
        self.hitbox = pygame.Rect(x, 0, PLAYER_W, PLAYER_H)
        self.hitbox.bottom = y
        self.pos_y = float(self.hitbox.y)
        self.rect = self.image.get_rect(midbottom=self.hitbox.midbottom)

    def load_spritesheet(self, path, num_frames, frame_w, frame_h, scale, anim_speed, y_offset=0, start_frame=0):
        frames = []
        try:
            spritesheet = pygame.image.load(path).convert_alpha()
            cols = spritesheet.get_width() // frame_w
            for i in range(start_frame, start_frame + num_frames):
                row = i // cols
                col = i % cols
                rect = pygame.Rect(col * frame_w, row * frame_h, frame_w, frame_h)
                frame = spritesheet.subsurface(rect)
                new_w = int(frame_w * scale)
                new_h = int(frame_h * scale)
                frame = pygame.transform.scale(frame, (new_w, new_h))
                frames.append(frame)
        except pygame.error:
            placeholder = pygame.Surface((int(frame_w*scale), int(frame_h*scale)), pygame.SRCALPHA)
            placeholder.fill((255, 0, 255, 128))
            frames.append(placeholder)
        return {'frames': frames, 'speed': anim_speed, 'y_offset': y_offset * scale}

    def jump(self):
        if self.is_hanging:
            self.vy = JUMP_V
            if self.hanging_side == 'right':
                self.vx = -WALL_PUSH_BACK_SPEED
            else:
                self.vx = WALL_PUSH_BACK_SPEED
            self.is_hanging = False
            self.on_ground = False
            self.double_jump_available = True
            return

        if self.on_ground:
            self.vy = JUMP_V
            self.on_ground = False
            self.double_jump_available = True
        elif self.wall_state.is_sliding and self.wall_state.execute_jump():
            wall_side = self.wall_state.side
            self.vy = JUMP_V
            if wall_side == 'right':
                self.vx = -WALL_PUSH_BACK_SPEED
            else:
                self.vx = WALL_PUSH_BACK_SPEED
            self.wall_state.stop_slide()
            self.double_jump_available = True
        elif self.double_jump_available:
            self.vy = DOUBLE_JUMP_V
            self.double_jump_available = False

    def dash(self):
        if self.can_dash and self.dash_cooldown <= 0 and not self.is_dashing:
            self.is_dashing = True
            self.dash_timer = 200
            self.dash_cooldown = 800
            dash_speed = WALK_SPEED * 3
            self.vx = dash_speed if self.facing_right else -dash_speed
            self.vy = 0
            self.state = 'run'
            return True
        return False

    def roll(self):
        if self.on_ground and self.roll_cooldown <= 0 and not self.is_rolling:
            self.is_rolling = True
            self.roll_timer = ROLL_DURATION
            self.roll_cooldown = ROLL_COOLDOWN
            self.state = 'roll'
            self.current_frame = 0
            self.anim_timer = 0
            self.vx = ROLL_SPEED if self.facing_right else -ROLL_SPEED
            return True
        return False

    def attack(self):
        if not self.is_attacking and not self.wall_state.is_sliding:
            self.is_attacking = True
            self.current_frame = 0
            self.anim_timer = 0
            if not hasattr(self, 'hit_enemies'):
                self.hit_enemies = set()
            else:
                self.hit_enemies.clear()
            
            if not self.on_ground:
                self.state = 'attack_from_air'
                self.attack_timer = 500
            elif self.is_crouching:
                self.state = 'crouch_attack'
                self.attack_timer = 400
            else:
                self.attack_combo = (self.attack_combo % 3) + 1
                self.state = f'attack{self.attack_combo}'
                self.attack_timer = 400
            return True
        return False

    def stomp(self):
        if not self.on_ground and not self.is_stomping and self.stomp_cooldown_timer <= 0:
            self.is_stomping = True
            self.stomp_phase = 'dive'
            self.state = 'stomp_down'
            self.current_frame = 0
            self.anim_timer = 0
            self.vx = 0
            self.vy = STOMP_DIVE_SPEED
            if not hasattr(self, 'hit_enemies'):
                self.hit_enemies = set()
            else:
                self.hit_enemies.clear()
            return True
        return False

    def heal(self, player_stats):
        if player_stats.hp < player_stats.max_hp and not self.is_healing:
            if getattr(self, 'heal_charges', 0) > 0:
                self.heal_charges -= 1
                player_stats.hp = min(player_stats.max_hp, player_stats.hp + 30)
                self.is_healing = True
                self.state = 'heal'
                self.current_frame = 0
                self.anim_timer = 0
                self.vx = 0
                return True
        return False

    def _get_stomp_hitbox(self, world_x_offset):
        if self.is_stomping and self.stomp_phase == 'dive':
            foot_x = self.hitbox.centerx
            foot_y = self.hitbox.bottom
            w = self.hitbox.width
            h = int(40 * SCALE_UNIFORM)
            return pygame.Rect(foot_x - w//2, foot_y - 10, w, h)
        return None

    def _check_wall_collision(self, test_rect, wall_tiles, world_x_offset):
        for wall_tile in wall_tiles:
            wall_screen_rect = pygame.Rect(
                wall_tile.x - world_x_offset,
                wall_tile.y,
                wall_tile.width,
                wall_tile.tile_height
            )
            
            if not test_rect.colliderect(wall_screen_rect):
                continue
            
            overlap_left = test_rect.right - wall_screen_rect.left
            overlap_right = wall_screen_rect.right - test_rect.left
            
            if overlap_left < overlap_right:
                return ('right', wall_screen_rect, overlap_left)
            else:
                return ('left', wall_screen_rect, overlap_right)
        return (None, None, 0)

    def update(self, platforms, world_x_offset, delta_time, wall_tiles=None, current_run_speed=0):
        old_hitbox = self.hitbox.copy()
        self.wall_state.update(delta_time)
        player_on_platform = False
        
        if self.stomp_cooldown_timer > 0:
            self.stomp_cooldown_timer -= delta_time * 1000
            
        if hasattr(self, 'invincible_timer') and self.invincible_timer > 0:
            self.invincible_timer -= delta_time * 1000
            
        keys = pygame.key.get_pressed()
        if self.is_dashing:
            self.dash_timer -= delta_time * 1000
            self.vx = (WALK_SPEED * 3) if self.facing_right else -(WALK_SPEED * 3)
            self.vy = 0
            if self.dash_timer <= 0:
                self.is_dashing = False
                self.vx = 0
        
        if self.dash_cooldown > 0:
            self.dash_cooldown -= delta_time * 1000

        if not self.is_attacking and not self.is_stomping and not self.is_dashing and not self.is_rolling and not self.is_healing:
            current_speed = WALK_SPEED
            if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]:
                current_speed = WALK_SPEED * 1.5  # Sprint boost
                
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                self.vx = -current_speed
                self.facing_right = False
            elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.vx = current_speed
                self.facing_right = True
            else:
                self.vx *= PLAYER_DRAG_COEFFICIENT

        elif self.is_rolling:
            self.vx = ROLL_SPEED if self.facing_right else -ROLL_SPEED
            self.roll_timer -= delta_time * 1000
            if self.roll_timer <= 0:
                self.is_rolling = False
                self.state = 'run'
        elif not self.is_dashing:
            self.vx *= PLAYER_DRAG_COEFFICIENT
        
        if self.roll_cooldown > 0:
            self.roll_cooldown -= delta_time * 1000

        if abs(self.vx) < 0.1:
            self.vx = 0
                
        self.is_crouching = False
        if self.on_ground and (keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL]):
            self.is_crouching = True
            self.vx = 0
            
        if self.is_hanging:
            if self.hanging_side == 'right' and (keys[pygame.K_LEFT] or keys[pygame.K_a]):
                self.is_hanging = False
            elif self.hanging_side == 'left' and (keys[pygame.K_RIGHT] or keys[pygame.K_d]):
                self.is_hanging = False
                
        if not self.is_hanging:
            self.hitbox.x += self.vx
        
        for p in platforms:
            platform_screen_rect = pygame.Rect(p.x - world_x_offset + 5, p.y, p.length - 10, 600) 
            if self.hitbox.colliderect(platform_screen_rect):
                if self.hitbox.bottom > platform_screen_rect.top + 40:
                    if self.vx > 0:
                        self.hitbox.right = platform_screen_rect.left
                        self.vx = 0
                    elif self.vx < 0:
                        self.hitbox.left = platform_screen_rect.right
                        self.vx = 0

        if wall_tiles and self.wall_state.re_attach_cooldown <= 0:
            side, wall_rect, overlap = self._check_wall_collision(self.hitbox, wall_tiles, world_x_offset)
            
            if side:
                if side == 'right' and self.vx >= 0:
                    self.hitbox.right = wall_rect.left
                    self.vx = 0
                    self.wall_state.start_slide('right')
                elif side == 'left' and self.vx <= 0:
                    self.hitbox.left = wall_rect.right
                    self.vx = 0
                    self.wall_state.start_slide('left')
                else:
                    self.wall_state.stop_slide()
            else:
                self.wall_state.stop_slide()
        
        if not self.on_ground and not self.is_hanging and self.vy >= -2:
            for p in platforms:
                platform_rect = pygame.Rect(p.x - world_x_offset, p.y, p.length, 20)
                if self.facing_right and abs(self.hitbox.right - platform_rect.left) < 15:
                    if abs(self.hitbox.top - platform_rect.top) < 25:
                        self.is_hanging = True
                        self.hanging_side = 'right'
                        self.hitbox.right = platform_rect.left + 5
                        self.hitbox.top = platform_rect.top + 12
                        self.vy = 0
                        self.vx = 0
                        self.pos_y = float(self.hitbox.y)
                        break
                elif not self.facing_right and abs(self.hitbox.left - platform_rect.right) < 15:
                    if abs(self.hitbox.top - platform_rect.top) < 25:
                        self.is_hanging = True
                        self.hanging_side = 'left'
                        self.hitbox.left = platform_rect.right - 5
                        self.hitbox.top = platform_rect.top + 12
                        self.vy = 0
                        self.vx = 0
                        self.pos_y = float(self.hitbox.y)
                        break

        if not self.on_ground and not self.is_hanging:
            grav = GRAVITY
            if self.is_stomping:
                if self.stomp_phase == 'windup':
                    grav *= STOMP_WINDUP_GRAVITY_MULT
                elif self.stomp_phase == 'dive':
                    grav *= STOMP_GRAVITY_MULT
                    self.vy = STOMP_DIVE_SPEED
            self.vy += grav
            
        if self.wall_state.is_sliding and not self.on_ground:
            self.vy = min(self.vy, MAX_WALL_SLIDE_SPEED)
        
        if self.is_stomping:
            self.stomp_timer -= delta_time * 1000
            if self.stomp_phase == 'windup' and self.stomp_timer <= 0:
                self.stomp_phase = 'dive'
                self.state = 'stomp_down'
                self.current_frame = 0
            elif self.stomp_phase == 'recovery' and self.stomp_timer <= 0:
                self.is_stomping = False
                self.stomp_phase = None
                self.stomp_cooldown_timer = STOMP_COOLDOWN
        
        self.pos_y += self.vy
        self.hitbox.y = int(self.pos_y)
        
        if not self.is_hanging:
            self.on_ground = False
            for p in platforms:
                top_rect = pygame.Rect(p.x - world_x_offset - 1, p.y, p.length + 2, 20)
                ground_check_rect = pygame.Rect(self.hitbox.x, self.hitbox.y, self.hitbox.width, self.hitbox.height + 2)
                
                if ground_check_rect.colliderect(top_rect) and self.vy >= 0:
                    if old_hitbox.bottom <= top_rect.top + 45:
                        self.on_ground = True
                        self.double_jump_available = True
                        self.vy = 0
                        self.hitbox.bottom = top_rect.top
                        self.pos_y = float(self.hitbox.y)
                        self.wall_state.reset()
                        
                        if self.is_attacking and self.state == 'attack_from_air':
                            self.is_attacking = False
                            self.attack_timer = 0
                            self.state = 'idle'
                            
                        if self.is_stomping and self.stomp_phase == 'dive':
                            self.stomp_phase = 'recovery'
                            self.stomp_timer = STOMP_RECOVERY_TIME
                            self.state = 'land_heavy'
                            self.current_frame = 0
                            self.vx = 0
                            player_on_platform = "STOMP_IMPACT"
                        break
        else:
            self.on_ground = False
        
        if self.wall_state.is_sliding and not self.on_ground:
            if self.wall_state.time_elapsed > WALL_CLIMB_TIME_LIMIT:
                return "WALL_TIME_EXCEEDED"
        
        if player_on_platform == "STOMP_IMPACT":
            return "STOMP_IMPACT"
        
        previous_state = self.state
        if self.state == 'death':
            pass
        elif self.is_attacking or self.is_stomping or self.is_rolling or self.is_healing:
            pass
        elif self.is_hanging:
            self.state = 'hanging'
        elif self.wall_state.is_sliding and not self.on_ground:
            self.state = 'climb'
        elif not self.on_ground:
            self.state = 'jump' if self.vy < 0 else 'fall'
        elif self.is_crouching:
            self.state = 'crouch'
        elif abs(self.vx) > 0.1:
            if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]:
                self.state = 'run'
            else:
                self.state = 'walk'

        else:
            self.state = 'idle'
        
        if self.is_attacking:
            self.attack_timer -= delta_time * 1000
            if self.attack_timer <= 0:
                self.is_attacking = False
                self.state = 'run' if abs(self.vx) > 0.1 else 'idle'
        
        if self.state != previous_state:
            self.current_frame = 0
        
        anim_to_play = self.state
        current_anim = self.animations[anim_to_play]
        self.anim_timer += delta_time * 1000
        
        if self.anim_timer > current_anim['speed']:
            self.anim_timer %= current_anim['speed']
            if anim_to_play in ['jump', 'death', 'stomp_down'] and self.current_frame < len(current_anim['frames']) - 1:
                self.current_frame += 1
            elif anim_to_play not in ['jump', 'death', 'stomp_down']:
                self.current_frame = (self.current_frame + 1) % len(current_anim['frames'])
                if self.current_frame == 0:
                    if self.is_attacking:
                        self.is_attacking = False
                    if self.is_healing:
                        self.is_healing = False
        
        self.image = current_anim['frames'][self.current_frame]
        
        if self.state in ['climb', 'hanging']:
            side = self.wall_state.side if self.state == 'climb' else self.hanging_side
            if side == 'left':
                self.image = pygame.transform.flip(self.image, True, False)
        else:
            faces_left = current_anim.get('faces_left', False)
            if not faces_left:
                if not self.facing_right:
                    self.image = pygame.transform.flip(self.image, True, False)
            else:
                if self.facing_right:
                    self.image = pygame.transform.flip(self.image, True, False)
        
        self.rect = self.image.get_rect()
        self.rect.midbottom = self.hitbox.midbottom
        self.rect.y += int(current_anim.get('y_offset', 0))
        
        
        if hasattr(self, 'invincible_timer') and self.invincible_timer > 0:
            if (pygame.time.get_ticks() // 100) % 2 == 0:
                self.image = self.image.copy()
                self.image.set_alpha(120)
                
        return None
