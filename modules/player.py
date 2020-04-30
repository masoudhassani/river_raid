from modules import Entity
import pygame as pg

class Player(Entity):
    def __init__(self, scr, name, ent_type, cg, pos, icon_list, v_speed, h_speed, 
                player_cg=(), sound_list=[], life_span=999999, capacity=100, dec_factor=1,
                inc_factor=1, low_fuel=0.2):
        super().__init__(scr, name, ent_type, cg, pos, icon_list, v_speed, h_speed, 
                        player_cg, sound_list, life_span)

        self.capacity = capacity           # initial fuel capacity
        self.dec_factor = dec_factor       # fuel decrease factor per step
        self.inc_factor = inc_factor       # fuel increase factor per step
        self.low_fuel = low_fuel           # percentage of capacity for low fuel alert
        self.fuel = capacity
        self.channels = {
                        'engine-normal': 0,
                        'engine-fast': 1,
                        'engine-slow': 2,
                        'fuel-up': 3,
                        'fuel-critical': 4,
                        'tank-filled': 5
                        }
        

    def update(self, keys, fuel_col=False, close_enemies=0): 
        # handle movements
        if keys[pg.K_LEFT]:
            self.move_left()
        elif keys[pg.K_RIGHT]:
            self.move_right()

        # handle speed
        if keys[pg.K_UP]:
            self.speed_up()
        elif keys[pg.K_DOWN]:
            self.slow_down()
        else:
            self.current_speed_h = self.base_speed_h
            self.current_speed_v = self.base_speed_v
        
        # no passing from boundaries 
        # self.check_walls()

        # check player life
        icon = self.check_life()

        # update travel distance 
        self.update_odometer()

        # play engine sound 
        self.play_sound(self.sounds[0], channel=self.channels['engine-normal'], loop=-1)

        # check the remaining fuel 
        self.check_fuel(fuel_col, close_enemies)

        # draw
        self.screen.blit(icon, self.pos)

        return self.travel_total

    def move_right(self):
        self.pos[0] += self.current_speed_h
 
    def move_left(self):
        self.pos[0] -= self.current_speed_h

    def check_walls(self):
        # left wall collision
        if self.pos[0] <= self.walls[0]:
            self.pos[0] = self.walls[0]
        
        # right wall collision 
        if self.pos[0] + self.cg[0] >= self.walls[1]:
            self.pos[0] = self.walls[1] - self.cg[0]

    def play_sound(self, sound, channel=0, loop=-1):
        if self.alive:
            if not pg.mixer.Channel(channel).get_busy():
                pg.mixer.Channel(channel).play(sound, loop)
                self.sound_played = True
        else:
            pg.mixer.Channel(channel).pause()

    def pause(self):
        for key in self.channels:
            pg.mixer.Channel(self.channels[key]).stop()

    def check_life(self):
        if not self.alive:
            icon = self.icons[1]
        else:
            icon = self.icons[0]

        return icon 

    def reset(self):
        self.alive = True 
        self.pos = self.init_pos.copy()
        self.fuel = self.capacity
        for key in self.channels:
            pg.mixer.Channel(self.channels[key]).stop()
        
    def check_fuel(self, fuel_col, close_enemies):
        # fuel up if player is colliding with fuel tank
        if fuel_col:
            self.fuel += self.inc_factor 
            self.play_sound(self.sounds[3], channel=self.channels['fuel-up'], loop=-1)
            # tank filled alert 
            if self.fuel >= 0.95 * self.capacity:
                pg.mixer.Channel(self.channels['fuel-up']).stop()
                self.play_sound(self.sounds[5], channel=self.channels['tank-filled'], loop=-1) 
            else: 
                pg.mixer.Channel(self.channels['tank-filled']).stop()   

        # regular fuel consumption          
        else:
            self.fuel -= self.dec_factor * self.current_speed_v
            pg.mixer.Channel(self.channels['tank-filled']).stop()
            pg.mixer.Channel(self.channels['fuel-up']).stop()

        # fuel down if in vicinity of enemy
        self.fuel -= self.dec_factor * close_enemies * self.current_speed_v
        
        # cap the fuel between 0 and self.capacity 
        self.fuel = min(max(0, self.fuel), self.capacity)        

        # low fuel alert 
        if self.fuel < self.low_fuel * self.capacity:
            self.play_sound(self.sounds[4], channel=self.channels['fuel-critical'], loop=-1)
        else:
            pg.mixer.Channel(self.channels['fuel-critical']).stop()

               
