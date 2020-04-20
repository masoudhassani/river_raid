
import pygame as pg

class Entity:
    def __init__(self, scr, name, ent_type, cg, pos, icon, v_speed, h_speed):
        self.screen = scr
        self.name = name
        self.type = ent_type
        self.cg = cg    # collision geometry dimension wxh
        self.pos = pos 
        self.current_speed_h = h_speed
        self.current_speed_v = v_speed
        self.base_speed_h = h_speed
        self.base_speed_v = v_speed
        self.screen_height = scr.get_height()
        self.alive = True
        self.icon = pg.image.load(icon)

    def update(self, events=[]):
        # logic for position manipulation comes here 

        # draw on screen
        self.screen.blit(self.icon, self.pos) 

    def speed_up(self):
        self.current_speed_v = self.base_speed_v * 2.0

    def slow_down(self):
        self.current_speed_v = self.base_speed_v / 2.0
        
    def set_walls(self, walls):
        self.walls = walls

    def set_barrier(self):
        pass

    def is_active(self):
        if self.pos[1] > self.screen_height:
            return False
            
    def sign(self, num):
        if num > 0:
            return 1
        elif num < 0:
            return -1 
        else:
            return 0