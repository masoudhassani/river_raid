from modules import Entity
import pygame as pg

class Player(Entity):

    def update(self, keys): 
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
        self.play_sound()

        # draw
        self.screen.blit(icon, self.pos)

        return self.travel_total

    def move_right(self):
        self.pos[0] += self.current_speed_h
 
    def move_left(self):
        self.pos[0] -= self.current_speed_h

    def speed_up(self):
        self.current_speed_h = self.base_speed_h * 2.0

    def slow_down(self):
        self.current_speed_h = self.base_speed_h / 2.0

    def check_walls(self):
        # left wall collision
        if self.pos[0] <= self.walls[0]:
            self.pos[0] = self.walls[0]
        
        # right wall collision 
        if self.pos[0] + self.cg[0] >= self.walls[1]:
            self.pos[0] = self.walls[1] - self.cg[0]

    def play_sound(self):
        if self.alive:
            if not self.sound_played:
                pg.mixer.Channel(0).play(self.sound, -1)
                self.sound_played = True
        else:
            pg.mixer.Channel(0).pause()
            self.sound_played = False

    def pause(self):
        pg.mixer.Channel(0).pause()
        self.sound_played = False

    def check_life(self):
        if not self.alive:
            icon = self.icons[1]
        else:
            icon = self.icons[0]

        return icon 

    def reset(self):
        self.alive = True 
        self.pos = self.init_pos.copy()
        
        
