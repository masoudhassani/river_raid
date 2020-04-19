from modules import Entity
import pygame as pg

class Player(Entity):
    def __init__(self, scr, name, ent_type, cg, pos, icon, speed):
        super().__init__(scr, name, ent_type, cg, pos, icon)
        self.base_speed = speed
        self.current_speed = speed

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
            self.current_speed = self.base_speed
        
        # check collision with boundaries 
        self.check_walls()

        # draw
        self.screen.blit(self.icon, self.pos)

    def move_right(self):
        self.pos[0] += self.current_speed
 
    def move_left(self):
        self.pos[0] -= self.current_speed

    def speed_up(self):
        self.current_speed = self.base_speed * 2.0

    def slow_down(self):
        self.current_speed = self.base_speed / 2.0

    def check_walls(self):
        # left wall collision
        if self.pos[0] <= self.walls[0]:
            self.pos[0] = self.walls[0]
        
        # right wall collision 
        if self.pos[0] + self.cg[0] >= self.walls[1]:
            self.pos[0] = self.walls[1] - self.cg[0]       
