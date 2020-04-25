from modules import Entity
import pygame as pg

class Enemy(Entity):

    def update(self, keys): 
        # handle speed
        if keys[pg.K_UP]:
            self.speed_up()
        elif keys[pg.K_DOWN]:
            self.slow_down()
        else:
            self.current_speed_h = self.base_speed_h * self.sign(self.current_speed_h)
            self.current_speed_v = self.base_speed_v

        # handle movements
        self.move()

        # check collision with boundaries 
        self.check_walls()

        # check if enemy is not in screen, it will be removed from memory 
        self.is_active()

        # draw
        self.screen.blit(self.icons[0], self.pos)

    def move(self):
        self.pos[0] += self.current_speed_h
        self.pos[1] += self.current_speed_v

    def check_walls(self):
        # left wall collision
        if self.pos[0] <= self.walls[0]:
            self.current_speed_h *= -1
        
        # right wall collision 
        if self.pos[0] + self.cg[0] >= self.walls[1]:
            self.current_speed_h *= -1       

    def is_active(self):
        if self.pos[1] > self.screen_height:
            return False
        else:
            return self.alive
